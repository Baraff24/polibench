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

Crea un nuovo utente con password hashata. L'utente viene creato con `is_active=True` e `is_superuser=False` per
default.

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

## Router da implementare

I seguenti router sono progettati negli schemi ma non ancora implementati al momento della stesura di questo documento (
marzo 2026):

### datasets (da fare)

Prefisso previsto: `/api/v1/datasets`

| Endpoint  | Metodo | Auth               | Input/Output                      | Note                                    |
|-----------|--------|--------------------|-----------------------------------|-----------------------------------------|
| `/`       | POST   | utente attivo      | `DatasetCreate` → `DatasetPublic` | Il server risolve `team_uuid → team_id` |
| `/`       | GET    | pubblico           | — → `list[DatasetSummary]`        | Lista con filtri                        |
| `/{uuid}` | GET    | pubblico           | — → `DatasetPublic`               | Dettaglio                               |
| `/{uuid}` | PATCH  | proprietario/admin | `DatasetCreate` → `DatasetPublic` |                                         |
| `/{uuid}` | DELETE | proprietario/admin | — → `DatasetPublic`               |                                         |

### ml-models (da fare)

Prefisso previsto: `/api/v1/ml-models`

| Endpoint  | Metodo | Auth          | Input/Output                      | Note |
|-----------|--------|---------------|-----------------------------------|------|
| `/`       | POST   | utente attivo | `MLModelCreate` → `MLModelPublic` |      |
| `/`       | GET    | pubblico      | — → `list[MLModelSummary]`        |      |
| `/{uuid}` | GET    | pubblico      | — → `MLModelPublic`               |      |

### experiments (da fare)

Prefisso previsto: `/api/v1/experiments`

| Endpoint          | Metodo | Auth          | Input/Output                                | Note                                                                                                                  |
|-------------------|--------|---------------|---------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `/`               | POST   | utente attivo | `ExperimentCreate` → `ExperimentPublic`     | Risolve `dataset_uuid`, `model_uuid` → ObjectId internamente; setta `submitted_by_user_uuid` dal JWT; `status=QUEUED` |
| `/{uuid}`         | GET    | utente attivo | — → `ExperimentPublic`                      |                                                                                                                       |
| `/{uuid}/metrics` | POST   | utente attivo | `MetricsBatchCreate` → `list[MetricPublic]` | Denormalizza `dataset_id`, `model_id` dall'Experiment                                                                 |
| `/{uuid}/metrics` | GET    | pubblico      | — → `ExperimentMetrics`                     | Raggruppato per split                                                                                                 |

### leaderboard (da fare)

Prefisso previsto: `/api/v1/leaderboard`

| Endpoint | Metodo | Auth     | Query params                                  | Note                                                                                       |
|----------|--------|----------|-----------------------------------------------|--------------------------------------------------------------------------------------------|
| `/`      | GET    | pubblico | `dataset_uuid`, `split`, `metric`, `limit=10` | Ritorna `list[LeaderboardEntry]`; arricchisce con `model_name` da MLModel; aggiunge `rank` |

