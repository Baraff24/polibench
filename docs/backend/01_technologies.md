# Stack Tecnologico — Backend

## Linguaggio: Python 3.12

Il backend è scritto in **Python 3.12**, l'ultima versione stabile al momento dello sviluppo. La scelta di Python è
motivata dalla sua posizione dominante nell'ecosistema del machine learning e della ricerca, che è il contesto di
utilizzo di Polibench. Python 3.12 introduce miglioramenti alle performance dell'interprete e messaggi di errore più
leggibili rispetto alle versioni precedenti.

La versione minima richiesta è dichiarata nel file `pyproject.toml`:

```toml
requires-python = ">=3.12"
```

---

## Gestore di dipendenze: uv

Il progetto utilizza **uv** come gestore di pacchetti e ambienti virtuali, in sostituzione di pip/venv/poetry. `uv` è
scritto in Rust ed è significativamente più veloce nella risoluzione e installazione delle dipendenze rispetto agli
strumenti tradizionali.

Le dipendenze sono dichiarate in `pyproject.toml` secondo lo standard PEP 517/518. Il file `uv.lock` garantisce la
riproducibilità esatta dell'ambiente su macchine diverse.

Le dipendenze di sviluppo sono separate in un gruppo dedicato:

```toml
[dependency-groups]
dev = [
    "asgi-lifespan>=2.1.0",
    "black>=25.1.0",
    "httpx>=0.28.1",
    "mongomock-motor>=0.0.34",
    "mypy>=1.15.0",
    "pre-commit>=4.2.0",
    "pytest>=8.3.5",
    "pytest-cov>=6.1.1",
    "ruff>=0.11.10",
]
```

---

## Framework web: FastAPI

**FastAPI** (versione `>=0.115.12`) è il framework HTTP scelto per il backend. Le motivazioni principali sono:

- **Prestazioni**: FastAPI è costruito su Starlette e utilizza un event loop asincrono (asyncio). È tra i framework
  Python più veloci disponibili.
- **Tipizzazione nativa**: FastAPI si integra con Pydantic per la validazione automatica dei dati in ingresso e in
  uscita. Ogni endpoint dichiara il tipo atteso del body e della risposta.
- **Documentazione automatica**: FastAPI genera automaticamente la documentazione interattiva OpenAPI (Swagger UI)
  all'indirizzo `/docs` e ReDoc all'indirizzo `/redoc`, senza alcuna configurazione aggiuntiva.
- **Dependency Injection**: il sistema `Depends()` di FastAPI permette di iniettare dipendenze (utente corrente,
  connessione DB) in modo dichiarativo e testabile.

L'applicazione viene eseguita tramite `fastapi run app/main.py` in modalità sviluppo con `--reload`.

---

## Database: MongoDB

Il database scelto è **MongoDB**, un database documentale NoSQL. La scelta è motivata da:

- **Schema flessibile**: le metriche di benchmark possono variare per tipo e struttura; un documento JSON è più adatto
  di una tabella relazionale rigida.
- **Performance su query aggregate**: le query di leaderboard (top-N per dataset/split/metrica) beneficiano degli indici
  compositi di MongoDB.
- **Denormalizzazione controllata**: il modello `Metric` include campi denormalizzati (`dataset_id`, `model_id`) che
  consentono query veloci senza join, un pattern comune nei sistemi di analytics.

In produzione MongoDB gira come servizio Docker con volume persistente (`app-db-data`).

---

## Driver asincrono: Motor

**Motor** (versione `>=3.7.1`) è il driver asincrono ufficiale di MongoDB per Python. Permette di eseguire operazioni
sul database senza bloccare l'event loop di asyncio, che è il requisito fondamentale per un'applicazione FastAPI
performante.

Motor non viene usato direttamente nel codice applicativo: è il livello su cui si appoggia Beanie.

---

## ODM: Beanie

**Beanie** (versione `>=1.29.0`) è un Object Document Mapper (ODM) costruito sopra Motor e Pydantic. Permette di
definire le collezioni MongoDB come classi Python tipizzate (chiamate `Document`) e di eseguire operazioni CRUD con una
API ad alto livello.

Rispetto all'uso diretto di Motor, Beanie offre:

- **Modelli tipizzati**: ogni documento è una classe Pydantic, con validazione automatica dei campi.
- **Indici dichiarativi**: gli indici MongoDB si dichiarano direttamente nell'annotazione del campo (
  `Indexed(unique=True)`).
- **Query builder**: `MyDocument.find(MyDocument.campo == valore).sort(...).limit(N).to_list()` genera la query MongoDB
  corretta.
- **Inizializzazione centralizzata**: `init_beanie(database=..., document_models=[...])` registra tutte le collezioni
  all'avvio dell'applicazione.

---

## Validazione dati: Pydantic

**Pydantic** (versione `>=2.11.4`) è la libreria di validazione dei dati utilizzata sia da FastAPI (per gli schemi HTTP)
sia da Beanie (per i Document). Pydantic v2 è scritto in Rust (tramite `pydantic-core`) ed è molto più veloce della
versione 1.

Nel progetto Pydantic è usato in due contesti distinti:

1. **`BaseModel`** — per gli schemi API (cartella `schemas/`): definisce la forma dei dati in ingresso e in uscita
   dall'API HTTP.
2. **`Document`** (sottoclasse di `BaseModel` fornita da Beanie) — per i modelli dati (cartella `models/`): definisce la
   struttura dei documenti MongoDB.

La separazione tra i due usi è deliberata e fondamentale per l'architettura del sistema.

---

## Configurazione: pydantic-settings

**pydantic-settings** (versione `>=2.9.1`) estende Pydantic per la lettura di configurazioni da variabili d'ambiente e
file `.env`. La classe `Settings` in `app/config/config.py` dichiara tutti i parametri di configurazione come campi
tipizzati: se una variabile obbligatoria manca all'avvio, l'applicazione fallisce immediatamente con un messaggio di
errore chiaro.

---

## Autenticazione: JWT + passlib + python-jose

L'autenticazione è basata su token **JWT** (JSON Web Token):

- **python-jose** (versione `>=3.4.0`): codifica e decodifica i token JWT con algoritmo HS256.
- **passlib** (versione `>=1.7.4`) con backend **bcrypt** (versione `>=4.3.0`): hashing sicuro delle password. `bcrypt`
  è un algoritmo di hashing adattivo, progettato per essere computazionalmente costoso e resistente agli attacchi
  brute-force.

---

## SSO: fastapi-sso

**fastapi-sso** (versione `>=0.18.0`) fornisce l'integrazione con provider OAuth2 esterni. Il progetto supporta il login
tramite **Google OAuth2**. Il flusso SSO utilizza un cookie `HttpOnly` per trasportare il token JWT dopo il redirect da
Google, evitando l'esposizione del token in URL o JavaScript.

---

## Containerizzazione: Docker e Docker Compose

L'intero stack (backend, frontend, database, reverse proxy) è containerizzato con **Docker**. L'orchestrazione in
sviluppo avviene tramite **Docker Compose** con la funzionalità `watch` per il live-reload automatico del codice.

Il reverse proxy è **Traefik** (versione 3.2), che instrada le richieste verso backend e frontend in base al path (
`/api` → backend, `/` → frontend).

---

## Qualità del codice

| Tool           | Versione    | Scopo                                             |
|----------------|-------------|---------------------------------------------------|
| **Ruff**       | `>=0.11.10` | Linter e formattatore (sostituisce flake8, isort) |
| **Black**      | `>=25.1.0`  | Formattatore del codice (line length 90)          |
| **mypy**       | `>=1.15.0`  | Type checker statico                              |
| **pre-commit** | `>=4.2.0`   | Hook git per eseguire linter prima di ogni commit |

Ruff è configurato per controllare stile (`E`, `W`), errori (`F`) e ordinamento degli import (`I001`).

---

## Testing

| Tool                | Versione     | Scopo                                            |
|---------------------|--------------|--------------------------------------------------|
| **pytest**          | `>=8.3.5`    | Framework di test                                |
| **anyio**           | (transitiva) | Backend asincrono per pytest (asyncio)           |
| **httpx**           | `>=0.28.1`   | Client HTTP asincrono per i test dei router      |
| **asgi-lifespan**   | `>=2.1.0`    | Gestisce il lifespan FastAPI nei test            |
| **mongomock-motor** | `>=0.0.34`   | Implementazione in-memory di Motor per i test DB |
| **pytest-cov**      | `>=6.1.1`    | Copertura del codice                             |

