# Deployment e Ambienti

Questo documento descrive come avviare, configurare e distribuire Polibench nei tre ambienti principali: sviluppo
locale, test (CI) e produzione. Raccoglie in una vista unica operativa le informazioni sparse tra configurazione,
tecnologie e architettura.

---

## Ambienti previsti

| Ambiente        | File Compose                      | Database            | HTTPS              | Reload automatico |
|-----------------|-----------------------------------|---------------------|--------------------|-------------------|
| Sviluppo locale | `docker-compose.yml`              | MongoDB locale      | No (HTTP)          | Sì (`--reload`)   |
| Test (CI)       | nessun compose, `mongomock-motor` | in-memory           | No                 | N/A               |
| Produzione      | `docker-compose.prod.yml`         | MongoDB persistente | Sì (Let's Encrypt) | No                |

---

## Sviluppo locale

### Prerequisiti

- Docker Desktop (o Docker Engine + Docker Compose v2)
- `uv` per gestire le dipendenze Python (opzionale se si usa solo Docker)

### Avvio rapido con Docker Compose

```bash
# 1. Copia il file delle variabili d'ambiente
cp .env.example .env
# Edita .env con i tuoi valori (vedi sezione Variabili d'ambiente)

# 2. Avvia tutti i servizi
docker compose up --watch
```

Il flag `--watch` attiva la modalità **Docker Compose Watch**: quando un file in `backend/` o `frontend/` cambia,
Docker sincronizza automaticamente il file nel container senza ricostruire l'immagine (tranne per modifiche a
`pyproject.toml` o `package.json`, che triggerano un rebuild).

### Servizi avviati in sviluppo locale

| Servizio        | Porta locale  | Nota                                                   |
|-----------------|---------------|--------------------------------------------------------|
| `proxy`         | `80`          | Traefik in modalità insecure (dashboard su `8090`)     |
| `db`            | `27017`       | MongoDB con volume persistente `app-db-data`           |
| `mongo-express` | (via Traefik) | Pannello web MongoDB (stile Django admin)              |
| `backend`       | `8000`        | FastAPI con `--reload` (auto-riavvio su modifica file) |
| `frontend`      | `5173`        | Vite dev server con HMR (Hot Module Replacement)       |

### URL locali

| Risorsa           | URL                              |
|-------------------|----------------------------------|
| Frontend          | `http://localhost/`              |
| Backend API       | `http://localhost/api/v1/`       |
| Swagger UI        | `http://localhost/docs`          |
| ReDoc             | `http://localhost/redoc`         |
| Mongo Express     | `http://localhost/mongo-express` |
| Traefik Dashboard | `http://localhost:8090`          |

Il routing da porta 80 verso i singoli servizi è gestito da **Traefik** tramite le label Docker:

- path `/api`, `/docs`, `/redoc` → backend (porta 8000)
- tutto il resto `/` → frontend (porta 5173)

### Avvio backend senza Docker (per debug diretto)

Se si preferisce eseguire il backend direttamente senza container:

```bash
cd backend
uv sync                          # installa le dipendenze nel venv
uv run fastapi run --reload app/main.py
```

Il file `.env` deve trovarsi nella root del progetto (un livello sopra `backend/`), perché `Settings` lo cerca con
path relativo `"../.env"`.

---

## Configurazione: variabili d'ambiente minime

Le variabili obbligatorie (senza le quali l'app non parte) sono:

```dotenv
# Infrastruttura (Docker Compose / Traefik)
DOMAIN=localhost
STACK_NAME=polibench

# Applicazione
PROJECT_NAME=polibench

# Superutente iniziale (creato automaticamente al primo avvio)
FIRST_SUPERUSER=admin@polibench.com
FIRST_SUPERUSER_PASSWORD=changeme

# JWT — generare con: openssl rand -hex 32
SECRET_KEY=changeme-generate-with-openssl-rand-hex-32

# Database MongoDB
MONGO_HOST=db           # "db" in Docker, "localhost" in locale senza Docker
MONGO_PORT=27017
MONGO_DB=polibench
MONGO_USER=mongodbadmin
MONGO_PASSWORD=changeme-strong-password

# Mongo Express Basic Auth
MONGO_EXPRESS_USER=admin
MONGO_EXPRESS_PASSWORD=changeme-in-production
# Nota: la connection string MongoDB per mongo-express viene costruita
# automaticamente dal compose come:
#   mongodb://${MONGO_USER}:${MONGO_PASSWORD}@db:${MONGO_PORT}/
# Non è necessario impostarla manualmente.
```

Le variabili opzionali (SMTP, SSO, CORS, FRONTEND_URL) hanno valori di default sicuri per lo sviluppo ma devono essere
configurate esplicitamente in produzione. Vedi [07_configuration.md](./07_configuration.md) per la lista completa.

---

## Cosa succede all'avvio dell'applicazione

Il `lifespan` definito in `app/main.py` esegue questa sequenza ad ogni avvio:

```
1. Connessione a MongoDB (AsyncIOMotorClient)
    └── usa MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_USER, MONGO_PASSWORD

2. init_beanie(document_models=DOCUMENT_MODELS)
    └── crea indici su tutte le collezioni (se non esistono)
    └── idempotente: si può eseguire più volte senza problemi

3. Creazione superutente iniziale (se non esiste)
    └── cerca utente con email == FIRST_SUPERUSER
    └── se non trovato → crea con FIRST_SUPERUSER_PASSWORD hashata
    └── utile al primo deploy o dopo un reset del database

4. Applicazione pronta → Traefik inizia a smistare il traffico
```

**Nota**: `init_beanie` gestisce automaticamente la creazione degli indici MongoDB. Se un indice non esiste, viene
creato al primo avvio. Questa operazione è sicura da eseguire su database già popolati.

---

## Produzione

### Prerequisiti

- Server Linux con Docker Engine e Docker Compose v2
- DNS configurato per puntare al server (es. `polibench.example.com`)
- Porta 80 e 443 aperte nel firewall

### Avvio in produzione

```bash
# 1. Copia e configura il file .env
cp .env.example .env
# Imposta SECRET_KEY con un valore casuale sicuro
# Imposta DOMAIN, TRAEFIK_TLS_EMAIL, credenziali MongoDB

# 2. Crea la rete esterna Traefik (una tantum)
docker network create traefik-public

# 3. Build e avvio
docker compose -f docker-compose.prod.yml up -d --build
```

### Differenze rispetto allo sviluppo

| Aspetto             | Sviluppo                | Produzione                                       |
|---------------------|-------------------------|--------------------------------------------------|
| HTTPS               | No (HTTP puro)          | Sì (Let's Encrypt TLS automatico)                |
| Backend command     | `fastapi run --reload`  | `fastapi run` (senza reload)                     |
| Frontend build      | Vite dev server (HMR)   | Nginx serve build statica (`npm run build`)      |
| Immagini Docker     | Build locale            | Build e push su GHCR (GitHub Container Registry) |
| Rete Traefik        | Rete interna al compose | Rete Docker esterna (`traefik-public`)           |
| Redirect HTTP→HTTPS | No                      | Sì (redirect automatico via Traefik)             |

### Routing Traefik in produzione

Traefik gestisce il routing tramite label Docker sui servizi:

```
https://polibench.example.com/api/*           → backend (FastAPI)
https://polibench.example.com/docs            → backend (Swagger UI)
https://polibench.example.com/redoc           → backend (ReDoc)
https://polibench.example.com/mongo-express   → mongo-express (pannello DB)
https://polibench.example.com/*               → frontend (Nginx)
```

I certificati TLS sono gestiti automaticamente da Traefik tramite Let's Encrypt (challenge TLS-ALPN-01).
I certificati sono persistiti nel volume `./letsencrypt/acme.json`.

---

## Mongo Express — Pannello web MongoDB

Mongo Express è un'interfaccia web per ispezionare e modificare i dati MongoDB, simile al Django admin panel.
È presente sia nel compose di sviluppo che in quello di produzione.

### Cosa permette di fare

- Visualizzare tutte le **collezioni** del database (`users`, `datasets`, `experiments`, `metrics`, ecc.)
- **Leggere, modificare e cancellare** singoli documenti
- **Creare** nuovi documenti manualmente
- Eseguire **query** di ricerca e filtro
- Vedere la struttura dei dati grezzi (inclusi ObjectId, campi denormalizzati)

### URL di accesso

| Ambiente   | URL                               |
|------------|-----------------------------------|
| Sviluppo   | `http://localhost/mongo-express`  |
| Produzione | `https://<dominio>/mongo-express` |

### Autenticazione

Mongo Express è protetto da **HTTP Basic Auth**. Le credenziali sono configurate nel `.env`:

```dotenv
MONGO_EXPRESS_USER=admin
MONGO_EXPRESS_PASSWORD=admin   # CAMBIARE in produzione!
```

### Connessione a MongoDB

La connection string per mongo-express viene costruita **automaticamente da Docker Compose**:

```
mongodb://${MONGO_USER}:${MONGO_PASSWORD}@db:${MONGO_PORT}/
```

Non è necessario impostare variabili aggiuntive — basta che `MONGO_USER`, `MONGO_PASSWORD` e `MONGO_PORT` siano
presenti nel `.env`. L'immagine usata è `mongo-express:1.0.2` (versione stabile, non `latest`).

### Differenze con il Django admin

| Django admin                         | Mongo Express                          |
|--------------------------------------|----------------------------------------|
| CRUD su modelli ORM con form         | CRUD su documenti JSON grezzi          |
| Validazione automatica               | Nessuna validazione — documento grezzo |
| Form generati da modelli             | Editor JSON diretto                    |
| Azioni bulk personalizzate           | Query filter di base                   |
| Gestione utenti e permessi integrata | Solo visualizzazione/modifica dati     |

> **Nota**: Mongo Express mostra i dati **interni** (ObjectId, campi denormalizzati, campi non esposti dall'API).
> È uno strumento di **debug e amministrazione**, non un pannello utente.

### Sicurezza in produzione

In produzione, mongo-express è accessibile solo via HTTPS (TLS tramite Traefik/Let's Encrypt) e protetto da
Basic Auth. Si consiglia di:

- usare credenziali forti per `MONGO_EXPRESS_USER` e `MONGO_EXPRESS_PASSWORD`
- eventualmente aggiungere un middleware Traefik di IP whitelist per limitare l'accesso a soli IP fidati

### Persistenza dei dati

In produzione il volume MongoDB è:

```yaml
volumes:
  app-db-data:    # dati MongoDB
  app-static-data: # file statici del backend (es. upload futuri)
```

I volumi Docker persistono tra i restart dei container. Per un backup:

```bash
# Dump MongoDB
docker exec <nome_container_db> mongodump --out /data/backup
docker cp <nome_container_db>:/data/backup ./backup
```

---

## Test (ambiente CI)

I test non usano Docker né un'istanza MongoDB reale. Usano `mongomock-motor`, una libreria che simula MongoDB
completamente in memoria.

```bash
cd backend
uv run pytest                    # esegue tutti i test
uv run pytest tests/db/          # solo smoke test database
uv run pytest tests/routers/     # solo test router
uv run pytest -v --tb=short      # output verboso
```

L'ambiente di test è configurato nel `conftest.py` radice (`tests/conftest.py`), che:

1. inizializza Beanie con `mongomock-motor` (nessuna connessione reale)
2. crea un `AsyncClient` ASGI (nessun socket di rete)
3. fornisce fixture per utenti, dataset, modelli e experiment pre-creati

Vedi [08_testing.md](./08_testing.md) per la strategia di test completa.

### Variabili d'ambiente per i test

Le variabili d'ambiente per i test sono configurate tramite `pytest-env` o direttamente nel `conftest.py`.
Non è necessario un file `.env` reale: le `Settings` usano valori di default accettabili per i test.

