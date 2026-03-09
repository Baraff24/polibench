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
configurate esplicitamente in produzione. Vedi [07_configuration.md](./07_configuration.md) per la lista completa,
incluse le istruzioni per **Gmail** (STARTTLS porta 587) e **Aruba** (SSL porta 465).

> ⚠️ **Importante**: configura `MONGO_USER` e `MONGO_PASSWORD` **prima** del primo `docker compose up`.
> MongoDB inizializza l'utente root solo alla creazione del volume. Se il volume esiste già senza credenziali,
> l'autenticazione fallirà. In quel caso esegui `docker compose down -v` per rimuovere il volume e ripartire.

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
- DNS configurato per puntare al server (`polibench.raffaelegrieco.it → IP del server`)
- Porta 80 e 443 aperte nel firewall

### Avvio in produzione (build locale sul server)

Il `docker-compose.prod.yml` fa il build delle immagini direttamente sul server, senza richiedere una registry Docker
remota. È la modalità più semplice per un deploy diretto.

```bash
# 1. Clona il repo sul server
git clone https://github.com/baraff/polibench.git
cd polibench

# 2. Crea il file .env.production (NON va in git)
cp .env.example .env.production
# Poi modifica .env.production con i valori reali (dominio, password, SMTP…)
# Oppure copia il file .env.production già preparato

# 3. Crea la rete esterna Traefik (operazione una tantum per server)
docker network create traefik-public

# 4. Build e avvio
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

> **Nota `--env-file`**: il flag `--env-file .env.production` indica a Docker Compose quale file `.env` usare.
> Il flag `--build` forza la ricostruzione delle immagini ad ogni avvio (necessario dopo un `git pull`).

### Aggiornamento del deploy (dopo modifiche al codice)

```bash
cd polibench
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### Differenze rispetto allo sviluppo

| Aspetto             | Sviluppo                | Produzione                                  |
|---------------------|-------------------------|---------------------------------------------|
| HTTPS               | No (HTTP puro)          | Sì (Let's Encrypt TLS automatico)           |
| Backend command     | `fastapi run --reload`  | `fastapi run --workers 4` (senza reload)    |
| Frontend build      | Vite dev server (HMR)   | Nginx serve build statica (`npm run build`) |
| Immagini Docker     | Build locale            | Build locale sul server (`--build`)         |
| Rete Traefik        | Rete interna al compose | Rete Docker esterna (`traefik-public`)      |
| Redirect HTTP→HTTPS | No                      | Sì (redirect automatico via Traefik)        |
| File env            | `.env`                  | `.env.production`                           |

### Routing Traefik in produzione

Traefik gestisce il routing tramite label Docker sui servizi:

```
https://polibench.raffaelegrieco.it/api/*           → backend (FastAPI, porta 8000)
https://polibench.raffaelegrieco.it/docs            → backend (Swagger UI)
https://polibench.raffaelegrieco.it/redoc           → backend (ReDoc)
https://polibench.raffaelegrieco.it/mongo-express   → mongo-express (pannello DB)
https://polibench.raffaelegrieco.it/*               → frontend (Nginx, porta 80)
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

---

## Troubleshooting

### 502 Bad Gateway su tutte le richieste

Il backend non è in esecuzione o non è ancora pronto.

**Cause comuni**:

1. Il container `backend` non è partito perché MongoDB non era healthy (controlla con `docker compose ps`)
2. Il `.env` era incompleto o mancava `DOMAIN` / `STACK_NAME` (variabili required dal compose)
3. Il volume MongoDB è corrotto (vedi sotto)

**Verifica rapida**:

```bash
docker compose ps                        # tutti i container devono essere "Up"
docker compose logs backend --tail 30    # cerca errori di connessione a MongoDB
```

---

### AuthenticationFailed su mongo-express (o backend)

```
MongoServerError: Authentication failed.
```

**Causa**: il volume MongoDB `app-db-data` è stato inizializzato **prima** che venissero impostate le credenziali
(`MONGO_USER` / `MONGO_PASSWORD`) nel `.env`. MongoDB ha creato il database senza utenti, e ora rifiuta le credenziali
perché non le riconosce.

Questo accade tipicamente quando:

- il primo `docker compose up` è stato fatto con `MONGO_USER`/`MONGO_PASSWORD` commentati nel `.env`
- poi si decommenta le credenziali e si riavvia senza rimuovere il volume

**Soluzione** (distruttiva — cancella i dati esistenti):

```bash
# 1. Ferma tutto e rimuovi i volumi
docker compose down -v

# 2. Verifica che .env abbia MONGO_USER e MONGO_PASSWORD settati
cat .env | grep MONGO

# 3. Riavvia da zero — MongoDB viene inizializzato con le credenziali corrette
docker compose up -d --build
```

> ⚠️ `docker compose down -v` rimuove **tutti i dati** del database. In produzione, esegui un backup prima.

