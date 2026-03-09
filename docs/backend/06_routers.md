# Router e Endpoint HTTP

I router si trovano in `backend/app/routers/`. Ogni file definisce un `APIRouter` con un gruppo di endpoint correlati.
Tutti i router sono aggregati in `api.py` e montati con prefisso `/api/v1`.

---

## api.py — Router radice

```python
api_router = APIRouter()
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(experiments.router, tags=["experiments"])


@api_router.get("/")
async def root():
    return {"message": "Backend API for Polibench operational !"}
```

L'endpoint `GET /api/v1/` è un health check che non richiede autenticazione.

---

## Principio: router sottili

I router non contengono logica di business. Il loro unico compito è:

1. ricevere la richiesta HTTP e validare il body con Pydantic
2. estrarre l'utente corrente dal JWT (quando richiesto)
3. delegare al **service layer** (`app/services/`)
4. restituire la risposta

Tutta la logica (risoluzione UUID→ObjectId, denormalizzazione, query, aggregazioni) vive nei service.
Vedi [09_services.md](./09_services.md) per i dettagli.

---

## login.py — Autenticazione

Prefisso: `/api/v1/login`

Vedi il documento [05_authentication.md](./05_authentication.md) per i dettagli implementativi.

| Endpoint           | Metodo | Auth   | Risposta | Descrizione                          |
|--------------------|--------|--------|----------|--------------------------------------|
| `/access-token`    | POST   | No     | `Token`  | Login con email/password (form data) |
| `/test-token`      | GET    | JWT    | `User`   | Verifica validità del token corrente |
| `/refresh-token`   | GET    | Cookie | `Token`  | Rinnova token (usato dopo SSO)       |
| `/google`          | GET    | No     | Redirect | Avvia flusso Google OAuth2           |
| `/google/callback` | GET    | No     | Redirect | Callback Google, imposta cookie      |

---

## users.py — Gestione utenti

Prefisso: `/api/v1/users`

Questo router implementa il CRUD completo degli utenti con due livelli di accesso: operazioni sull'utente corrente (
autenticato) e operazioni amministrative (solo superuser).

### Registrazione utente

```
POST /api/v1/users
```

- **Auth**: nessuna (endpoint pubblico)
- **Input**: `password`, `email`, `first_name`, `last_name` (body JSON)
- **Output**: `schemas.User`
- **Errori**: HTTP 400 se email già in uso (`DuplicateKeyError` da MongoDB)

Crea un nuovo utente con password hashata. L'utente viene creato con `is_active=True`, `is_verified=False` e
`is_superuser=False`. Dopo la creazione, viene generato un **token JWT di verifica** e inviata un'email con un link
di conferma. L'utente deve confermare l'email cliccando il link prima di poter operare come utente verificato.

Se SMTP non è configurato (sviluppo locale), il link di verifica viene loggato nella console del backend.

### Verifica email

```
GET /api/v1/users/verify/{token}
```

- **Auth**: nessuna (endpoint pubblico — il token è nel path)
- **Output**: `{"message": "Email verificata con successo."}`
- **Errori**: HTTP 400 se il token è scaduto o non valido; HTTP 404 se l'utente non esiste

Il token è un JWT con `purpose: email-verification`, `sub: user.uuid` e scadenza di 48 ore. Il frontend
costruisce la richiesta dalla pagina `/verify-email?token=...`.

### Reinvio email di verifica

```
POST /api/v1/users/resend-verification
```

- **Auth**: nessuna (endpoint pubblico)
- **Input**: `{"email": "user@example.com"}`
- **Output**: `{"message": "Email di verifica reinviata."}`
- **Errori**: HTTP 404 se l'utente non esiste

Se l'utente è già verificato, ritorna un messaggio di conferma senza inviare l'email.

### Lista utenti

```
GET /api/v1/users?limit=10&offset=0
```

- **Auth**: superuser
- **Query params**: `limit` (default 10), `offset` (default 0)
- **Output**: `list[schemas.User]`

Restituisce la lista paginata di tutti gli utenti. Accessibile solo ai superuser.

### Profilo utente corrente

```
GET /api/v1/users/me
PATCH /api/v1/users/me
DELETE /api/v1/users/me
```

- **Auth**: utente attivo (JWT)
- **Input PATCH**: `schemas.UserUpdate`
- **Output**: `schemas.User`

`GET` restituisce il profilo dell'utente corrente estratto dal token JWT.

`PATCH` aggiorna i campi forniti. I campi `is_active` e `is_superuser` sono esclusi dall'aggiornamento (un utente non
può auto-promuoversi). Se viene fornita una nuova `password`, viene hashata prima del salvataggio. In caso di email
duplicata, risponde HTTP 400.

`DELETE` elimina definitivamente l'account dell'utente corrente.

### Operazioni admin su utenti specifici

```
GET    /api/v1/users/{userid}
PATCH  /api/v1/users/{userid}
DELETE /api/v1/users/{userid}
```

- **Auth**: superuser
- **Path param**: `userid` (UUID dell'utente)
- **Errori**: HTTP 404 se utente non trovato

`{userid}` è sempre un **UUID**, non un ObjectId. La ricerca avviene con `User.find_one({"uuid": userid})`.

`PATCH` permette al superuser di aggiornare tutti i campi inclusi `is_active` e `is_superuser`.

---

## datasets.py — Dataset e MLModel

**File**: `routers/datasets.py` — delegato a `services/datasets.py`

Contiene gli endpoint sia per `Dataset` che per `MLModel` (entità di "catalogo" con pattern identico).

### Dataset

| Endpoint                          | Metodo | Auth              | Input / Output                    | Note                                    |
|-----------------------------------|--------|-------------------|-----------------------------------|-----------------------------------------|
| `/api/v1/datasets`                | POST   | utente verificato | `DatasetCreate` → `DatasetPublic` | Il server risolve `team_uuid → team_id` |
| `/api/v1/datasets`                | GET    | pubblico          | — → `list[DatasetSummary]`        | Lista completa (senza filtri per ora)   |
| `/api/v1/datasets/{dataset_uuid}` | GET    | pubblico          | — → `DatasetPublic`               | Dettaglio con risoluzione UUID          |

**Flusso POST `/datasets`**:

1. `DatasetCreate` viene validato da Pydantic (task e visibility sono enum)
2. Se `team_uuid` è presente, il service risolve `team_uuid → Team` (404 se non esiste)
3. Viene creato il Document `Dataset` con `team_id` (ObjectId interno) e `created_by_user_id` dall'utente JWT
4. La risposta `DatasetPublic` contiene solo UUID: `team_uuid` e `created_by_user_uuid`

**Flusso GET `/datasets/{dataset_uuid}`**:

1. Il service risolve `dataset_uuid → Dataset` (404 se non esiste)
2. Risolve `team_id → Team → team.uuid` e `created_by_user_id → User → user.uuid`
3. Ritorna `DatasetPublic` con tutti i campi UUID

### MLModel

| Endpoint                         | Metodo | Auth              | Input / Output                    | Note |
|----------------------------------|--------|-------------------|-----------------------------------|------|
| `/api/v1/ml-models`              | POST   | utente verificato | `MLModelCreate` → `MLModelPublic` |      |
| `/api/v1/ml-models`              | GET    | pubblico          | — → `list[MLModelSummary]`        |      |
| `/api/v1/ml-models/{model_uuid}` | GET    | pubblico          | — → `MLModelPublic`               |      |

`MLModelSummary` espone solo `uuid`, `name`, `family`, `paper_url` (versione ridotta per le liste).
`MLModelPublic` include anche `hyperparams` (configurazione canonica dell'algoritmo), `implementation`,
`created_by_user_uuid`, `created_at`.

---

## experiments.py — Experiment, Metric e Leaderboard

**File**: `routers/experiments.py` — delegato a `services/experiments.py`, `services/metrics.py`,
`services/leaderboard.py`

### Experiments

| Endpoint                     | Metodo | Auth              | Input / Output                          | Note                                         |
|------------------------------|--------|-------------------|-----------------------------------------|----------------------------------------------|
| `/api/v1/experiments`        | POST   | utente verificato | `ExperimentCreate` → `ExperimentPublic` | Risolve UUID → ObjectId; status parte QUEUED |
| `/api/v1/experiments/{uuid}` | GET    | utente attivo     | — → `ExperimentPublic`                  | Risolve tutti gli ObjectId interni in UUID   |

**Flusso POST `/experiments`**:

1. `ExperimentCreate` contiene `dataset_uuid` e `model_uuid` (UUID pubblici)
2. Il service risolve `dataset_uuid → Dataset` e `model_uuid → MLModel` (404 se non esistono)
3. Crea il Document `Experiment` con ObjectId interni: `dataset_id`, `model_id`, `submitted_by_user_id`
4. `submitted_by_user_id` viene estratto dal token JWT — il client non lo invia mai
5. `status` viene impostato a `QUEUED` lato server — il client non lo invia mai
6. La risposta `ExperimentPublic` risolve tutti gli ObjectId in UUID

**Campi gestiti esclusivamente dal server** (mai nel body del client):

- `submitted_by_user_uuid`: estratto dal JWT
- `status`: inizialmente `QUEUED`
- `created_at`: timestamp server

### Metrics (submission batch)

| Endpoint                             | Metodo | Auth              | Input / Output                             | Note                                             |
|--------------------------------------|--------|-------------------|--------------------------------------------|--------------------------------------------------|
| `/api/v1/experiments/{uuid}/metrics` | POST   | utente verificato | `MetricsBatchCreate` → `ExperimentMetrics` | Denormalizza dataset_id/model_id dall'Experiment |
| `/api/v1/experiments/{uuid}/metrics` | GET    | pubblico          | — → `ExperimentMetrics`                    | Raggruppato per split                            |

**Flusso POST `/experiments/{uuid}/metrics`**:

1. Il router impone `data.experiment_uuid = experiment_uuid` (path param ha precedenza sul body)
2. Il service risolve `experiment_uuid → Experiment`
3. Per ogni `MetricCreate` crea un Document `Metric` copiando `dataset_id`, `model_id`, `submitted_by_user_id`,
   `team_id` dall'Experiment (denormalizzazione server-side)
4. Inserisce tutti i Document in bulk con `insert_many`
5. Ritorna le metriche raggruppate per split (`ExperimentMetrics`)

### Leaderboard

| Endpoint              | Metodo | Auth     | Query params                                  | Output                   |
|-----------------------|--------|----------|-----------------------------------------------|--------------------------|
| `/api/v1/leaderboard` | GET    | pubblico | `dataset_uuid`, `metric`, `split`, `top_n=10` | `list[LeaderboardEntry]` |

**Flusso GET `/leaderboard`**:

1. Risolve `dataset_uuid → Dataset` (404 se non esiste)
2. Query su `Metric` per `(dataset_id, metric, split)`, ordinata per `value DESC`, limitata a `top_n`
3. Batch fetch degli `MLModel` e degli `Experiment` distinti per risolvere `model_id → model.uuid / model.name`
   e `experiment_id → experiment.uuid`
4. Assembla `LeaderboardEntry` con `rank` progressivo (1-based)

**Ottimizzazione**: le query sul leaderboard non fanno `$lookup` — `dataset_id` è denormalizzato in `Metric`,
quindi la query è un semplice `find()` su indice composto `{dataset_id, metric, split, value: -1}`.

---

## Riepilogo completo endpoint

| Endpoint                                  | Metodo | Auth       | Descrizione                             |
|-------------------------------------------|--------|------------|-----------------------------------------|
| `GET  /api/v1/`                           | GET    | no         | Health check                            |
| `POST /api/v1/login/access-token`         | POST   | no         | Login email/password                    |
| `GET  /api/v1/login/test-token`           | GET    | JWT        | Verifica token                          |
| `POST /api/v1/users`                      | POST   | no         | Registrazione utente (+ email verifica) |
| `GET  /api/v1/users/verify/{token}`       | GET    | no         | Verifica email (token JWT)              |
| `POST /api/v1/users/resend-verification`  | POST   | no         | Reinvia email di verifica               |
| `GET  /api/v1/users`                      | GET    | superuser  | Lista utenti                            |
| `GET  /api/v1/users/me`                   | GET    | attivo     | Profilo corrente                        |
| `PATCH /api/v1/users/me`                  | PATCH  | attivo     | Aggiorna profilo corrente               |
| `DELETE /api/v1/users/me`                 | DELETE | attivo     | Cancella account                        |
| `GET  /api/v1/users/{uuid}`               | GET    | superuser  | Profilo utente per UUID                 |
| `PATCH /api/v1/users/{uuid}`              | PATCH  | superuser  | Aggiorna utente                         |
| `DELETE /api/v1/users/{uuid}`             | DELETE | superuser  | Cancella utente                         |
| `POST /api/v1/datasets`                   | POST   | verificato | Crea Dataset                            |
| `GET  /api/v1/datasets`                   | GET    | no         | Lista Dataset                           |
| `GET  /api/v1/datasets/{uuid}`            | GET    | no         | Dettaglio Dataset                       |
| `POST /api/v1/ml-models`                  | POST   | verificato | Registra MLModel                        |
| `GET  /api/v1/ml-models`                  | GET    | no         | Lista MLModel                           |
| `GET  /api/v1/ml-models/{uuid}`           | GET    | no         | Dettaglio MLModel                       |
| `POST /api/v1/experiments`                | POST   | verificato | Sottomette Experiment (UUID input)      |
| `GET  /api/v1/experiments/{uuid}`         | GET    | attivo     | Dettaglio Experiment                    |
| `POST /api/v1/experiments/{uuid}/metrics` | POST   | verificato | Sottomette metriche batch               |
| `GET  /api/v1/experiments/{uuid}/metrics` | GET    | no         | Metriche raggruppate per split          |
| `GET  /api/v1/leaderboard`                | GET    | no         | Top-N per (dataset, metric, split)      |
