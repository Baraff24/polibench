# Polibench

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-%3E=3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

**Polibench** è una piattaforma web per il **benchmarking comparativo di modelli di raccomandazione** (Recommender
Systems). Consente a ricercatori e team di registrare dataset, algoritmi, esperimenti e metriche di valutazione in un
unico ambiente strutturato, e di consultare leaderboard ordinate per performance.

Il progetto nasce in contesto accademico e si ispira a piattaforme come [BARS](https://openbenchmark.github.io/BARS/)
e [OpenBenchmark](https://openbenchmark.github.io/), con l'obiettivo di centralizzare i risultati sperimentali e
facilitare la riproducibilità.

---

## Funzionalità principali

- **Gestione Dataset e Versioni** — dataset catalografico + dataset versioning con YAML (`dataset`, `version`,
  `characteristics`) e tracciamento `sources/resources`.
- **Pipeline Registry** — pipeline separate dalla versione (`P001`, `P002`, …), visualizzazione a blocchi/chain e YAML
  dedicato per pipeline.
- **Registrazione Modelli** — catalogo di algoritmi di raccomandazione (BPR, LightGCN, SGL, …) con iperparametri di
  riferimento, paper e implementazione.
- **Submission di Esperimenti** — associazione pipeline–modello con configurazione di training, seed, codice sorgente e
  artefatti per la riproducibilità.
- **Metriche di Valutazione** — registrazione batch di metriche (AUC, LogLoss, NDCG@k, Recall@k, …) per split (
  test/validation) con direzione (max/min).
- **Leaderboard** — classifica in tempo reale dei modelli per dataset, metrica e split, con grafici interattivi (
  Recharts).
- **Autenticazione** — JWT con email/password, Google OAuth2 (SSO), verifica email via SMTP.
- **Ruoli utente** — `admin`, `researcher`, `viewer` con controlli di accesso differenziati.
- **API UUID-first** — tutti gli endpoint pubblici usano UUID; gli ObjectId MongoDB restano interni.
- **Pannello MongoDB** — Mongo Express integrato per ispezionare il database via web.

---

## Stack tecnologico

| Layer                  | Tecnologia                                                                     | Ruolo                                     |
|------------------------|--------------------------------------------------------------------------------|-------------------------------------------|
| **Backend**            | [FastAPI](https://fastapi.tiangolo.com/)                                       | Framework API async                       |
| **ODM**                | [Beanie](https://beanie-odm.dev/)                                              | Object-Document Mapper per MongoDB        |
| **Validazione**        | [Pydantic v2](https://docs.pydantic.dev/)                                      | Schemi API e modelli dati                 |
| **Database**           | [MongoDB](https://www.mongodb.com/)                                            | Database documentale NoSQL                |
| **Driver DB**          | [Motor](https://motor.readthedocs.io/)                                         | Client MongoDB async per Python           |
| **Frontend**           | [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) | UI reattiva type-safe                     |
| **Build tool**         | [Vite](https://vitejs.dev/)                                                    | Dev server con HMR e build ottimizzato    |
| **Stili**              | [SCSS (BEM)](https://getbem.com/)                                              | CSS modulare senza framework esterni      |
| **Grafici**            | [Recharts](https://recharts.org/)                                              | Visualizzazione dati (leaderboard charts) |
| **Routing**            | [React Router v7](https://reactrouter.com/)                                    | Client-side routing con loader            |
| **Form**               | [React Hook Form](https://react-hook-form.com/)                                | Gestione form performante                 |
| **HTTP client**        | [Axios](https://axios-http.com/)                                               | Chiamate API con interceptor JWT          |
| **Reverse proxy**      | [Traefik](https://traefik.io/)                                                 | Routing, TLS automatico (Let's Encrypt)   |
| **Containerizzazione** | [Docker Compose](https://docs.docker.com/compose/)                             | Orchestrazione servizi (dev + prod)       |
| **Package manager**    | [uv](https://docs.astral.sh/uv/) (backend), npm (frontend)                     | Gestione dipendenze                       |
| **Testing**            | pytest + httpx (backend), Vitest (frontend)                                    | Test DB, API e componenti                 |
| **Linting**            | Ruff + Black (backend), ESLint + Prettier (frontend)                           | Qualità del codice                        |

---

## Struttura del progetto

```
polibench/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── auth/               # Autenticazione JWT e OAuth2
│   │   ├── config/             # Configurazione (Pydantic Settings)
│   │   ├── models/             # Documenti Beanie (MongoDB)
│   │   ├── routers/            # Endpoint HTTP (sottili)
│   │   ├── schemas/            # Schemi Pydantic (input/output API)
│   │   ├── services/           # Logica di business
│   │   └── main.py             # Entry point dell'applicazione
│   ├── scripts/
│   │   └── seed.py             # Popolazione DB con dati di esempio
│   └── tests/
│       ├── db/                 # Smoke test database
│       └── routers/            # Test API end-to-end
│
├── frontend/                   # Web app React
│   ├── src/
│   │   ├── components/         # Componenti UI (common, auth, leaderboard, layout)
│   │   ├── contexts/           # React Context (auth, snackbar)
│   │   ├── hooks/              # Custom hooks
│   │   ├── models/             # Tipi TypeScript
│   │   ├── routes/             # Pagine (home, datasets, models, experiments, leaderboard, …)
│   │   ├── services/           # Chiamate API (auth, dataset, experiment, leaderboard, …)
│   │   └── styles/             # SCSS organizzato in BEM
│   └── public/                 # Asset statici
│
├── docs/                       # Documentazione estesa
│   ├── backend/                # 15 documenti (panoramica → sviluppi futuri)
│   └── frontend/               # 4 documenti (overview, tecnologie, architettura, SCSS)
│
├── docker-compose.yml          # Sviluppo locale (hot reload)
├── docker-compose.prod.yml     # Produzione (TLS, build ottimizzate)
├── .env.example                # Template variabili d'ambiente
└── LICENSE                     # MIT
```

---

## Architettura

### Backend — layer separati

```
┌──────────────────────────────────────────┐
│            HTTP (FastAPI routers)         │  ← routers/
├──────────────────────────────────────────┤
│         Schemi API (Pydantic)            │  ← schemas/
├──────────────────────────────────────────┤
│         Service Layer (logica)           │  ← services/
├──────────────────────────────────────────┤
│         Autenticazione (JWT)             │  ← auth/
├──────────────────────────────────────────┤
│        Modelli dati (Beanie/ODM)         │  ← models/
├──────────────────────────────────────────┤
│           Database (MongoDB)             │  ← via Motor (async)
└──────────────────────────────────────────┘
```

I router sono volutamente **sottili**: ricevono la richiesta, delegano al service layer e restituiscono la risposta.
Tutta la logica (risoluzione UUID → ObjectId, denormalizzazione, query leaderboard) vive nei service.

### Frontend — layout

```
┌────────────────────────────────────────────────────┐
│  TopMenuBar (logo, profilo, login/logout)          │
├──────────────┬─────────────────────────────────────┤
│  Sidebar     │  Contenuto principale               │
│              │                                     │
│  Dashboard   │  PageHeader                         │
│  Leaderboard │  KPI Cards / Tabelle / Grafici      │
│  Datasets    │  Form di submission                 │
│  Models      │  Dettagli entità                    │
│  Experiments │                                     │
└──────────────┴─────────────────────────────────────┘
```

---

## Entità del dominio

| Entità         | Descrizione                                                                                           |
|----------------|-------------------------------------------------------------------------------------------------------|
| **User**       | Utente della piattaforma con ruolo (`admin`, `researcher`, `viewer`), autenticazione e verifica email |
| **Team**       | Gruppo di ricerca che aggrega utenti sotto uno stesso namespace                                       |
| **Dataset**    | Catalogo logico del dataset (nome, task, visibilità, metadati)                                        |
| **DatasetVersion** | Unità operativa versionata con YAML raw, sources/resources e dataset characteristics               |
| **Pipeline**   | Configurazione eseguibile su una DatasetVersion (YAML + blocchi normalizzati + status)                 |
| **MLModel**    | Algoritmo di raccomandazione con iperparametri di riferimento                                         |
| **Experiment** | Associazione pipeline–modello con configurazione, seed, codice e stato                                |
| **ExperimentMetric** | Risultato numerico di performance (CSV import) denormalizzato per leaderboard/query veloci      |
| **MetricImportJob** | Job async di import metriche da CSV con stati (`uploaded`, `processing`, `completed`, `failed`) |

---

## Avvio rapido

### Prerequisiti

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Clona il repository

```bash
git clone https://github.com/baraff/polibench.git
cd polibench
```

### 2. Configura le variabili d'ambiente

```bash
cp .env.example .env
# Modifica .env con i tuoi valori (vedi sezione "Configurazione" più sotto)
```

### 3. Avvia lo stack in sviluppo

```bash
docker compose watch
```

Questo avvia tutti i servizi con hot reload per backend e frontend.

### 4. Accedi all'applicazione

| Servizio              | URL                                                              |
|-----------------------|------------------------------------------------------------------|
| **Frontend**          | [http://localhost](http://localhost)                             |
| **API root**          | [http://localhost/api/v1](http://localhost/api/v1)               |
| **Swagger UI**        | [http://localhost/docs](http://localhost/docs)                   |
| **ReDoc**             | [http://localhost/redoc](http://localhost/redoc)                 |
| **Mongo Express**     | [http://localhost/mongo-express](http://localhost/mongo-express) |
| **Traefik Dashboard** | [http://localhost:8090](http://localhost:8090)                   |

### 5. Popola il database con dati di esempio (opzionale)

```bash
docker compose exec backend uv run python scripts/seed.py --mode minimal
```

Per svuotare il database prima di popolare:

```bash
docker compose exec backend uv run python scripts/seed.py --mode demo --reset
```

Modalità disponibili:

- `minimal`: seed rapido con 1 dataset/versione + 1 modello + 1 esperimento.
- `demo`: seed esteso multi-dataset/multi-versione con stati esperimenti misti e metric import realistici.
- `edge`: casi limite validi per test UI/consistenza (senza dati volutamente invalidi).

---

## Sviluppo locale (senza Docker)

### Backend

```bash
cd backend
uv sync                        # Installa le dipendenze nel venv
uv run fastapi dev app/main.py # Avvia il server di sviluppo
```

Il server sarà disponibile su `http://127.0.0.1:8000`.

- API: `http://localhost:8000/api/v1/`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend

```bash
cd frontend
npm install     # Installa le dipendenze
npm run dev     # Avvia il dev server con hot reload
```

Il frontend sarà disponibile su `http://localhost:5173`.

---

## Test

### Backend — test database (smoke test)

```bash
cd backend
uv run pytest tests/db/ -v
```

### Backend — test API end-to-end

```bash
cd backend
uv run pytest tests/routers/ -v
```

### Backend — tutti i test

```bash
cd backend
uv run pytest -v
```

### Frontend

```bash
cd frontend
npm run test
```

---

## Configurazione

Tutte le variabili d'ambiente sono definite nel file `.env` alla radice del progetto. Un template con valori di esempio
è disponibile in [`.env.example`](.env.example).

### Variabili principali

| Variabile                  | Descrizione                                                  | Default                    |
|----------------------------|--------------------------------------------------------------|----------------------------|
| `DOMAIN`                   | Dominio dell'applicazione                                    | `localhost`                |
| `ENVIRONMENT`              | Ambiente (`development`, `test`, `production`)               | `development`              |
| `PROJECT_NAME`             | Nome del progetto                                            | `polibench`                |
| `SECRET_KEY`               | Chiave segreta per JWT (generala con `openssl rand -hex 32`) | —                          |
| `FIRST_SUPERUSER`          | Email del superutente creato al primo avvio                  | `admin@polibench.com`      |
| `FIRST_SUPERUSER_PASSWORD` | Password del superutente                                     | —                          |
| `MONGO_HOST`               | Host MongoDB                                                 | `localhost`                |
| `MONGO_PORT`               | Porta MongoDB                                                | `27017`                    |
| `MONGO_DB`                 | Nome del database                                            | `polibench`                |
| `MONGO_USER`               | Username MongoDB                                             | —                          |
| `MONGO_PASSWORD`           | Password MongoDB                                             | —                          |
| `VITE_BACKEND_API_URL`     | URL dell'API usato dal frontend                              | `http://localhost/api/v1/` |
| `FRONTEND_URL`             | URL del frontend (per link di verifica email)                | `http://localhost:5173`    |

### SMTP (invio email di verifica)

Polibench supporta la verifica dell'email degli utenti registrati. Configura un provider SMTP per abilitare l'invio. Se
SMTP non è configurato, il link di verifica viene stampato nella console del backend.

Opzioni supportate:

- **Gmail** — STARTTLS su porta 587 (richiede [App Password](https://myaccount.google.com/apppasswords))
- **Aruba** — SSL diretto su porta 465
- Qualsiasi provider SMTP compatibile

### SSO Google (opzionale)

Per abilitare il login con Google, configura `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` ottenuti
dalla [Google Cloud Console](https://console.cloud.google.com/). Lascia vuoti per disabilitare.

### Mongo Express

Il pannello web Mongo Express è protetto da HTTP Basic Auth. Configura `MONGO_EXPRESS_USER` e `MONGO_EXPRESS_PASSWORD`
nel file `.env`. In produzione cambia sempre le credenziali di default.

---

## Deploy in produzione

Il file [`docker-compose.prod.yml`](docker-compose.prod.yml) è configurato per il deploy su un server con:

- **Traefik** come reverse proxy con TLS automatico (Let's Encrypt)
- Redirect automatico HTTP → HTTPS e www → non-www
- Frontend compilato e servito da **nginx**
- Mongo Express protetto e accessibile su `/mongo-express`

### Avviare in produzione

```bash
# Crea la rete Traefik (solo la prima volta)
docker network create traefik-public

# Avvia lo stack
docker compose -f docker-compose.prod.yml up -d
```

### Variabili specifiche per produzione

Nel file `.env` aggiorna almeno:

| Variabile                  | Valore produzione                |
|----------------------------|----------------------------------|
| `DOMAIN`                   | `tuodominio.com`                 |
| `ENVIRONMENT`              | `production`                     |
| `SECRET_KEY`               | Valore casuale (32+ byte hex)    |
| `FIRST_SUPERUSER_PASSWORD` | Password forte                   |
| `MONGO_PASSWORD`           | Password forte                   |
| `MONGO_EXPRESS_PASSWORD`   | Password forte                   |
| `TRAEFIK_TLS_EMAIL`        | Email valida per Let's Encrypt   |
| `VITE_BACKEND_API_URL`     | `https://tuodominio.com/api/v1/` |
| `FRONTEND_URL`             | `https://tuodominio.com`         |
| `BACKEND_CORS_ORIGINS`     | `["https://tuodominio.com"]`     |

> ⚠️ **Non usare mai i valori di default del `.env.example` in produzione.** Genera sempre password e chiavi casuali.

---

## Endpoint API principali

| Metodo  | Endpoint                             | Descrizione                                       |
|---------|--------------------------------------|---------------------------------------------------|
| `POST`  | `/api/v1/login/access-token`         | Ottieni JWT (email/password)                      |
| `GET`   | `/api/v1/login/google`               | Avvia OAuth2 con Google                           |
| `POST`  | `/api/v1/users`                      | Registrazione utente                              |
| `GET`   | `/api/v1/users/me`                   | Profilo utente corrente                           |
| `PATCH` | `/api/v1/users/me`                   | Aggiorna profilo                                  |
| `GET`   | `/api/v1/users/verify/{token}`       | Verifica email con token                          |
| `GET`   | `/api/v1/datasets`                   | Lista dataset                                     |
| `POST`  | `/api/v1/datasets`                   | Crea dataset (autenticato + verificato)           |
| `GET`   | `/api/v1/datasets/{uuid}`            | Dettaglio dataset                                 |
| `GET`   | `/api/v1/datasets/{uuid}/versions`   | Lista DatasetVersion del dataset                  |
| `POST`  | `/api/v1/datasets/{uuid}/versions`   | Crea DatasetVersion da YAML                       |
| `POST`  | `/api/v1/datasets/{uuid}/versions/preview` | Preview parse/validazione YAML               |
| `GET`   | `/api/v1/dataset-versions/{uuid}`    | Dettaglio DatasetVersion                          |
| `GET`   | `/api/v1/dataset-versions/{uuid}/sources` | Sources della DatasetVersion                 |
| `GET`   | `/api/v1/dataset-versions/{uuid}/resources` | Resources della DatasetVersion              |
| `GET`   | `/api/v1/dataset-versions/{uuid}/pipelines` | Lista pipeline della DatasetVersion          |
| `POST`  | `/api/v1/dataset-versions/{uuid}/pipelines` | Crea pipeline per DatasetVersion             |
| `POST`  | `/api/v1/dataset-versions/{uuid}/pipelines/preview` | Preview parse pipeline YAML            |
| `GET`   | `/api/v1/pipelines/{uuid}`           | Dettaglio Pipeline                                |
| `GET`   | `/api/v1/pipelines/{uuid}/yaml`      | YAML della Pipeline                               |
| `GET`   | `/api/v1/pipelines/{uuid}/experiments` | Esperimenti collegati alla Pipeline            |
| `GET`   | `/api/v1/dataset-versions/{uuid}/yaml/{kind}` | YAML (`dataset`, `version`, `characteristics`) |
| `GET`   | `/api/v1/dataset-versions/{uuid}/experiments` | Esperimenti collegati alla versione         |
| `GET`   | `/api/v1/ml-models`                  | Lista modelli                                     |
| `POST`  | `/api/v1/ml-models`                  | Registra modello (autenticato + verificato)       |
| `GET`   | `/api/v1/ml-models/{uuid}`           | Dettaglio modello                                 |
| `POST`  | `/api/v1/experiments`                | Sottometti esperimento (autenticato + verificato) |
| `GET`   | `/api/v1/experiments/{uuid}`         | Dettaglio esperimento                             |
| `GET`   | `/api/v1/experiments/{uuid}/metrics` | Metriche dell'esperimento                         |
| `POST`  | `/api/v1/experiments/{uuid}/metric-import` | Import metriche da CSV (async)              |
| `GET`   | `/api/v1/leaderboard`                | Leaderboard filtrata per dataset/version/pipeline |

La documentazione interattiva completa è disponibile su `/docs` (Swagger UI) e `/redoc`.

### Contratto YAML (allineato a DataRec)

- `dataset_yaml_raw`: metadata catalografici dataset-level (`datasets/*.yml`)
- `version_yaml_raw`: definizione version-level con `sources` e `resources` (`versions/*_*.yml`)
- `characteristics_yaml_raw`: dataset characteristics (`metrics/*_*.yml`)
- `pipeline_yaml_raw`: compatibilità transitoria in create-version; la source of truth pipeline è il model `Pipeline`
  (`yaml_raw` + `blocks`)

Le **dataset characteristics** (`n_users`, `density`, `gini_*`) restano in `DatasetVersion`;  
le **experiment metrics** (`ndcg`, `recall`, `rmse`, ...) entrano solo in `ExperimentMetric` via CSV import.

---

## Documentazione

La cartella [`docs/`](docs/) contiene documentazione estesa divisa per area:

### Backend (`docs/backend/`)

| File                                                                                | Contenuto                                   |
|-------------------------------------------------------------------------------------|---------------------------------------------|
| [`00_overview.md`](docs/backend/00_overview.md)                                     | Panoramica generale e obiettivi             |
| [`01_technologies.md`](docs/backend/01_technologies.md)                             | Stack tecnologico e motivazioni             |
| [`02_architecture.md`](docs/backend/02_architecture.md)                             | Architettura a layer e struttura cartelle   |
| [`03_data_models.md`](docs/backend/03_data_models.md)                               | Modelli dati Beanie e diagramma di dominio  |
| [`04_schemas.md`](docs/backend/04_schemas.md)                                       | Schemi Pydantic per input/output API        |
| [`05_authentication.md`](docs/backend/05_authentication.md)                         | JWT, OAuth2, verifica email, ruoli          |
| [`06_routers.md`](docs/backend/06_routers.md)                                       | Endpoint HTTP e convenzioni                 |
| [`07_configuration.md`](docs/backend/07_configuration.md)                           | Pydantic Settings e variabili d'ambiente    |
| [`08_testing.md`](docs/backend/08_testing.md)                                       | Strategia di test (DB smoke test + API e2e) |
| [`09_services.md`](docs/backend/09_services.md)                                     | Service layer e logica di business          |
| [`10_decisions.md`](docs/backend/10_decisions.md)                                   | Decisioni architetturali (ADR) e trade-off  |
| [`11_errors_and_api_conventions.md`](docs/backend/11_errors_and_api_conventions.md) | Gestione errori e convenzioni HTTP          |
| [`12_indexes_and_performance.md`](docs/backend/12_indexes_and_performance.md)       | Query critiche, indici e performance        |
| [`13_deployment.md`](docs/backend/13_deployment.md)                                 | Deploy con Docker e Traefik                 |
| [`14_future_work.md`](docs/backend/14_future_work.md)                               | Limiti attuali e sviluppi futuri            |
| [`domain_model.puml`](docs/backend/domain_model.puml)                               | Diagramma UML del dominio (PlantUML)        |

### Frontend (`docs/frontend/`)

| File                                                     | Contenuto                             |
|----------------------------------------------------------|---------------------------------------|
| [`00_overview.md`](docs/frontend/00_overview.md)         | Panoramica e struttura                |
| [`01_technologies.md`](docs/frontend/01_technologies.md) | Stack tecnologico frontend            |
| [`02_architecture.md`](docs/frontend/02_architecture.md) | Architettura componenti e routing     |
| [`03_scss.md`](docs/frontend/03_scss.md)                 | Organizzazione SCSS e convenzioni BEM |

---

## Pagine dell'applicazione

| Pagina                | Route                            | Descrizione                                         |
|-----------------------|----------------------------------|-----------------------------------------------------|
| Home                  | `/`                              | Landing page con panoramica del progetto            |
| Login                 | `/login`                         | Accesso con email/password o Google SSO             |
| Registrazione         | `/register`                      | Registrazione nuovo utente                          |
| Verifica email        | `/verify-email`                  | Conferma indirizzo email                            |
| Profilo               | `/profile`                       | Profilo utente (protetta)                           |
| Datasets              | `/datasets`                      | Lista di tutti i dataset                            |
| Dettaglio dataset     | `/datasets/:uuid`                | Informazioni dataset + lista versioni               |
| Dettaglio versione    | `/dataset-versions/:uuid`        | Sources, resources, YAML e lista pipeline           |
| Dettaglio pipeline    | `/pipelines/:uuid`               | Chain blocchi pipeline, YAML e lista esperimenti    |
| Nuovo dataset         | `/datasets/new`                  | Form creazione dataset (protetta)                   |
| Modelli               | `/models`                        | Lista di tutti i modelli                            |
| Dettaglio modello     | `/models/:uuid`                  | Informazioni e esperimenti del modello              |
| Nuovo modello         | `/models/new`                    | Form registrazione modello (protetta)               |
| Leaderboard           | `/leaderboard`                   | Classifica globale con filtri e grafici             |
| Dettaglio esperimento | `/experiments/:uuid`             | Dettaglio di un esperimento e relative metriche     |
| Nuovo esperimento     | `/experiments/new`               | Form submission esperimento (protetta)              |
| Submission metriche   | `/experiments/:uuid/metrics/new` | Form invio batch metriche (protetta)                |
| Gestione utenti       | `/users`                         | Pannello admin per la gestione utenti (solo admin)  |

---

## Licenza

Questo progetto è distribuito con licenza [MIT](LICENSE).

---

## Autore

Sviluppato da [Raffaele Grieco](https://github.com/baraff) come progetto di tesi.
