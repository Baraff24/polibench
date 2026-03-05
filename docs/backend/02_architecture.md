# Architettura del Backend

## Struttura delle cartelle

```
backend/
├── pyproject.toml          ← dipendenze e configurazione tool
├── uv.lock                 ← lock file riproducibile
├── Dockerfile              ← immagine di produzione
└── app/
    ├── __init__.py
    ├── main.py             ← punto di ingresso, lifespan, middleware
    ├── auth/
    │   └── auth.py         ← JWT, hashing, dipendenze autenticazione
    ├── config/
    │   ├── config.py       ← Settings (pydantic-settings)
    │   └── logging.py      ← configurazione logging standard
    ├── models/
    │   ├── __init__.py     ← DOCUMENT_MODELS (lista per init_beanie)
    │   ├── datasets.py
    │   ├── experiments.py
    │   ├── metrics.py
    │   ├── ml_models.py
    │   ├── teams.py
    │   └── users.py
    ├── routers/
    │   ├── api.py          ← router radice, aggrega tutti i sotto-router
    │   ├── login.py        ← endpoint autenticazione e SSO
    │   ├── users.py        ← CRUD utenti
    │   ├── datasets.py     ← Dataset + MLModel (catalogo)
    │   └── experiments.py  ← Experiment, Metric batch, Leaderboard
    ├── schemas/
    │   ├── __init__.py     ← esporta tutti gli schemi pubblici
    │   ├── datasets.py
    │   ├── experiments.py
    │   ├── metrics.py
    │   ├── ml_models.py
    │   ├── tokens.py
    │   └── users.py
    └── services/
        ├── __init__.py
        ├── datasets.py     ← logica Dataset + MLModel (risoluzione, creazione)
        ├── experiments.py  ← logica Experiment (risoluzione UUID, creazione)
        ├── metrics.py      ← inserimento batch, raggruppamento per split
        └── leaderboard.py  ← query top-N con batch fetch ottimizzato
```

---

## Separazione models / schemas

La distinzione tra `models/` e `schemas/` è il principio architetturale più importante del backend. I due strati hanno
responsabilità completamente diverse e non devono essere confusi.

### models/ — rappresentazione del database

I file in `models/` definiscono classi che estendono `beanie.Document`. Ogni classe corrisponde a una **collezione
MongoDB**. Queste classi:

- contengono tutti i campi del documento, inclusi quelli interni (es. `hashed_password`)
- dichiarano gli indici MongoDB tramite `Indexed(unique=True)` e simili
- definiscono il nome della collezione tramite la classe interna `Settings`
- sono usate esclusivamente per le operazioni su database (CRUD, query)

Esempio: `User` in `models/users.py` contiene `hashed_password`, che non deve mai uscire dall'API.

### schemas/ — contratto HTTP

I file in `schemas/` definiscono classi che estendono `pydantic.BaseModel`. Ogni schema rappresenta la forma di un *
*messaggio HTTP** (richiesta o risposta). Questi schemi:

- definiscono esattamente cosa il client può mandare (`XCreate`)
- definiscono esattamente cosa l'API restituisce (`XPublic`, `XSummary`)
- non contengono logica di database né annotazioni Beanie
- appaiono nella documentazione OpenAPI auto-generata

Questa separazione garantisce che una modifica interna al database (aggiunta di un indice, rinomina di un campo interno)
non cambi il contratto pubblico dell'API.

---

## Pattern degli schemi: Base, Create, Public, Summary

Per ogni entità del dominio si seguono queste convenzioni:

```
XBase       → campi condivisi tra Create e Public (ereditarietà)
  ├── XCreate   → cosa il CLIENT manda (solo Base, nessun campo server)
  └── XPublic   → cosa l'API RITORNA (Base + id, uuid, timestamps)
XSummary    → versione ridotta per liste (classe piatta, non eredita Base)
```

`XSummary` è sempre una classe piatta perché omette campi presenti in `Base`. In Pydantic non è possibile rimuovere
campi ereditati, quindi l'ereditarietà si usa solo quando le sottoclassi **aggiungono** campi.

### Principio UUID-first

L'intera API segue il principio UUID-first in modo consistente:

| Contesto        | Identificatore   | Note                                |
|-----------------|------------------|-------------------------------------|
| Path params     | UUID             | `GET /datasets/{dataset_uuid}`      |
| Body input      | UUID             | `dataset_uuid: UUID`, mai ObjectId  |
| Response output | UUID             | `uuid` unico identificatore esposto |
| Interno al DB   | ObjectId (`_id`) | Mai esposto all'esterno             |

Gli schemi `XCreate` usano UUID per tutti i riferimenti (`dataset_uuid`, `model_uuid`, `team_uuid`). Gli schemi
`XPublic` espongono solo `uuid` come identificatore: niente `_id`, niente `PydanticObjectId`.

Il router è il solo punto dove avviene la risoluzione `UUID → ObjectId`, internamente e in modo trasparente al client.
Questo rende l'API stabile e DB-agnostic: se il database cambia, i client non cambiano nulla.

---

## Inizializzazione dell'applicazione (lifespan)

FastAPI gestisce le operazioni di startup e shutdown tramite il context manager `@asynccontextmanager` definito in
`main.py`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    app.state.client = AsyncIOMotorClient(...)
    await init_beanie(
        database=app.state.client[settings.MONGO_DB],
        document_models=DOCUMENT_MODELS
    )
    # Creazione superutente iniziale se non esiste
    user = await User.find_one({"email": settings.FIRST_SUPERUSER})
    if not user:
        await user.create()
    yield
    # SHUTDOWN (implicito: Motor chiude le connessioni)
```

`DOCUMENT_MODELS` è una lista definita in `models/__init__.py` che contiene tutti i Document Beanie registrati nel
sistema. Aggiungere un nuovo modello richiede solo di aggiungerlo a questa lista.

---

## Routing

Tutti gli endpoint sono raggruppati sotto il prefisso `/api/v1`, dichiarato in `settings.API_V1_STR`. Il router
principale (`api.py`) include i sotto-router:

```
/api/v1/
├── /                          ← health check (GET)
├── /login/
│   ├── /access-token          ← POST: login con email/password
│   ├── /test-token            ← GET: verifica token
│   ├── /refresh-token         ← GET: rinnovo token (da cookie)
│   ├── /google                ← GET: redirect a Google OAuth2
│   └── /google/callback       ← GET: callback SSO
├── /users/
│   ├── /                      ← POST: registrazione, GET: lista (admin)
│   ├── /me                    ← GET/PATCH/DELETE: profilo corrente
│   └── /{uuid}                ← GET/PATCH/DELETE: utente specifico (admin)
├── /datasets/
│   ├── /                      ← POST: crea Dataset, GET: lista
│   └── /{dataset_uuid}        ← GET: dettaglio Dataset
├── /ml-models/
│   ├── /                      ← POST: registra MLModel, GET: lista
│   └── /{model_uuid}          ← GET: dettaglio MLModel
├── /experiments/
│   ├── /                      ← POST: sottometti Experiment (UUID input)
│   ├── /{uuid}                ← GET: dettaglio Experiment
│   ├── /{uuid}/metrics        ← POST: batch metriche, GET: metriche per split
└── /leaderboard/
    └── /                      ← GET: top-N per (dataset, metric, split)
```

Ogni gruppo di endpoint delega al service layer corrispondente:

- `/datasets` e `/ml-models` → `services/datasets.py`
- `/experiments` e `/{uuid}/metrics` → `services/experiments.py` + `services/metrics.py`
- `/leaderboard` → `services/leaderboard.py`

Vedi [06_routers.md](./06_routers.md) per la documentazione dettagliata di ogni endpoint
e [09_services.md](./09_services.md) per la logica di business.

---

## Middleware CORS

Il middleware CORS è configurato in `main.py` e permette richieste da origini definite in
`settings.BACKEND_CORS_ORIGINS`. In sviluppo questa lista include tipicamente `http://localhost:5173` (il dev server
Vite del frontend).

Il middleware usa `str(origin).rstrip("/")` per normalizzare le origini, rimuovendo eventuali slash finali che
causerebbero mismatch (comportamento documentato in un issue Pydantic).

---

## Configurazione tramite variabili d'ambiente

L'applicazione legge la configurazione da un file `.env` posizionato nella root del progetto (un livello sopra
`backend/`). La classe `Settings` in `config/config.py` dichiara tutti i parametri con i relativi tipi. I parametri
obbligatori (senza default) causano un errore di validazione all'avvio se assenti:

| Variabile                  | Tipo               | Obbligatoria | Descrizione                       |
|----------------------------|--------------------|--------------|-----------------------------------|
| `PROJECT_NAME`             | `str`              | ✅            | Nome del progetto                 |
| `FIRST_SUPERUSER`          | `EmailStr`         | ✅            | Email del superutente iniziale    |
| `FIRST_SUPERUSER_PASSWORD` | `str`              | ✅            | Password del superutente iniziale |
| `MONGO_HOST`               | `str`              | ✅            | Host MongoDB                      |
| `MONGO_PORT`               | `int`              | ✅            | Porta MongoDB                     |
| `MONGO_DB`                 | `str`              | ✅            | Nome del database                 |
| `MONGO_USER`               | `str`              | ❌            | Username MongoDB (opzionale)      |
| `MONGO_PASSWORD`           | `str`              | ❌            | Password MongoDB (opzionale)      |
| `SECRET_KEY`               | `str`              | ❌            | Chiave JWT (default: random)      |
| `BACKEND_CORS_ORIGINS`     | `list[AnyHttpUrl]` | ❌            | Origini CORS ammesse              |
| `GOOGLE_CLIENT_ID`         | `str`              | ❌            | ID client Google OAuth2           |
| `GOOGLE_CLIENT_SECRET`     | `str`              | ❌            | Secret Google OAuth2              |

---

## Containerizzazione

In sviluppo, l'intero stack è avviato con `docker compose up`. I servizi definiti in `docker-compose.yml` sono:

| Servizio   | Immagine       | Porta     | Descrizione                             |
|------------|----------------|-----------|-----------------------------------------|
| `proxy`    | `traefik:v3.2` | 80, 8090  | Reverse proxy e dashboard               |
| `db`       | `mongo:latest` | variabile | Database MongoDB con volume persistente |
| `backend`  | build locale   | 8000      | API FastAPI                             |
| `frontend` | build locale   | 5173      | Dev server Vite                         |

Traefik instrada le richieste in base al path:

- `PathPrefix(/api)`, `/docs`, `/redoc` → backend
- `PathPrefix(/)` → frontend

Il servizio `backend` dipende da `db` con `condition: service_healthy`: FastAPI non parte finché MongoDB non supera il
healthcheck (`mongosh --eval "db.adminCommand('ping')"`).

