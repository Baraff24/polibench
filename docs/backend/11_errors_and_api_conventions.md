# Convenzioni HTTP ed Error Handling

Questo documento definisce le convenzioni usate da Polibench per i codici di stato HTTP, il formato degli errori
e la gestione delle eccezioni. La coerenza in questi aspetti è importante quanto la coerenza del dominio: un client
(frontend, CLI, script) deve poter gestire gli errori in modo prevedibile.

---

## Formato standard degli errori

Tutti gli errori restituiti dall'API hanno questo formato JSON:

```json
{
  "detail": "Messaggio descrittivo dell'errore"
}
```

Questo è il formato nativo di FastAPI per `HTTPException`. Per gli errori di validazione Pydantic (body malformato),
FastAPI restituisce automaticamente:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "dataset_uuid"
      ],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

Il campo `detail` è quindi:

- una **stringa** per errori di business (404 Not Found, 403 Forbidden, 400 Bad Request da logica applicativa)
- una **lista** per errori di validazione Pydantic (422 Unprocessable Entity)

---

## Codici di stato HTTP usati

### 200 OK

Risposta standard per richieste GET riuscite e PATCH riusciti.

```
GET  /api/v1/datasets              → 200  list[DatasetSummary]
GET  /api/v1/datasets/{uuid}       → 200  DatasetPublic
GET  /api/v1/leaderboard           → 200  list[LeaderboardEntry]
PATCH /api/v1/users/me             → 200  UserPublic
```

### 201 Created

Restituito quando una risorsa viene **creata con successo** (POST di creazione).

```
POST /api/v1/datasets              → 201  DatasetPublic
POST /api/v1/ml-models             → 201  MLModelPublic
POST /api/v1/experiments           → 201  ExperimentPublic
POST /api/v1/experiments/{uuid}/metrics → 201  ExperimentMetrics
POST /api/v1/users                 → 201  UserPublic
```

### 400 Bad Request

Errore di business lato client. Il client ha inviato dati sintatticamente validi ma semanticamente errati.

**Quando viene usato in Polibench:**

| Situazione                                                | Endpoint                   |
|-----------------------------------------------------------|----------------------------|
| Email già registrata (DuplicateKeyError MongoDB)          | `POST /users`              |
| Google SSO non configurato (variabili d'ambiente assenti) | `GET /login/google`        |
| Password errata o account non attivo                      | `POST /login/access-token` |

**Esempio risposta:**

```json
{
  "detail": "Email già in uso"
}
```

### 401 Unauthorized

Il client non ha fornito credenziali valide (token JWT assente, scaduto o non valido).

**Quando viene usato:**

| Situazione                                    | Dove                           |
|-----------------------------------------------|--------------------------------|
| Token JWT assente nell'header                 | Qualsiasi endpoint autenticato |
| Token JWT scaduto                             | Qualsiasi endpoint autenticato |
| Token JWT con firma non valida                | Qualsiasi endpoint autenticato |
| Utente nel token non più esistente nel DB     | Qualsiasi endpoint autenticato |
| Account utente non attivo (`is_active=False`) | Qualsiasi endpoint autenticato |

**Header atteso dal client:**

```
Authorization: Bearer <token_jwt>
```

**Risposta FastAPI standard:**

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

Il client è autenticato ma non ha i permessi necessari per l'operazione richiesta.

**Quando viene usato:**

| Situazione                                  | Endpoint                             |
|---------------------------------------------|--------------------------------------|
| Utente non-superuser tenta operazione admin | `GET /users`, `DELETE /users/{uuid}` |
| Utente tenta di modificare un altro utente  | `PATCH /users/{uuid}` (non-admin)    |

**Differenza da 401**: 401 significa "non so chi sei"; 403 significa "so chi sei, ma non puoi farlo".

**Risposta:**

```json
{
  "detail": "The user doesn't have enough privileges"
}
```

### 404 Not Found

La risorsa referenziata non esiste nel database.

**Quando viene usato:**

| Situazione                               | Endpoint / Service                     |
|------------------------------------------|----------------------------------------|
| Dataset con UUID richiesto non esiste    | `get_dataset_by_uuid()` in services    |
| MLModel con UUID richiesto non esiste    | `get_ml_model_by_uuid()` in services   |
| Experiment con UUID richiesto non esiste | `get_experiment_by_uuid()` in services |
| Team con UUID richiesto non esiste       | `get_team_by_uuid()` in services       |
| Utente con UUID richiesto non esiste     | `GET /users/{uuid}` (admin)            |

Tutti i service centralizzano la risoluzione UUID→Document in helper dedicati che sollevano 404 in modo consistente:

```python
async def get_dataset_by_uuid(dataset_uuid: UUID) -> Dataset:
    doc = await Dataset.find_one(Dataset.uuid == dataset_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dataset non trovato")
    return doc
```

**Risposta:**

```json
{
  "detail": "Dataset non trovato"
}
```

### 422 Unprocessable Entity

Il body della richiesta è sintatticamente valido (JSON ben formato) ma fallisce la validazione Pydantic.

**Quando viene usato:**

- campo obbligatorio mancante nel body
- tipo errato (es. stringa dove si aspetta UUID)
- valore fuori dall'enum (es. `split: "train"` quando `Split` accetta solo `validation | test`)
- violazione di constraint (es. email malformata)

Questo codice è **generato automaticamente da FastAPI/Pydantic**, non dal codice applicativo.

**Risposta (esempio: campo mancante):**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body",
        "dataset_uuid"
      ],
      "msg": "Field required",
      "input": {
        "model_uuid": "550e8400-..."
      }
    }
  ]
}
```

---

## Differenza tra errori di validazione e errori di business

Questa distinzione è importante per chi consuma l'API:

| Tipo                        | Codice HTTP | Causa                                        | Formato `detail` |
|-----------------------------|-------------|----------------------------------------------|------------------|
| Validazione Pydantic        | `422`       | Body malformato, tipo errato, campo mancante | lista di oggetti |
| Errore di business (logica) | `400`       | Dati validi ma semanticamente errati         | stringa          |
| Risorsa non trovata         | `404`       | UUID non corrisponde a nessun documento      | stringa          |
| Non autenticato             | `401`       | Token assente o non valido                   | stringa          |
| Non autorizzato             | `403`       | Permessi insufficienti                       | stringa          |

**Regola pratica per il frontend**: se ricevi 422, il problema è nel formato del payload (da correggere lato client).
Se ricevi 400/404, il problema è nei dati (es. UUID sbagliato, email già usata).

---

## Convenzioni di risposta

### Endpoint di creazione (POST)

- Restituiscono sempre lo schema `XPublic` della risorsa creata, non solo l'UUID.
- Il codice di stato è `201 Created`.
- L'utente che ha creato la risorsa è estratto dal JWT (non dal body): il client non può impostare
  `created_by_user_id` o `submitted_by_user_id` direttamente.

### Endpoint di listing (GET su collezione)

- Restituiscono sempre `list[XSummary]` (versione ridotta, senza tutti i campi).
- Supportano `limit` e `offset` come query parameter per la paginazione.
- Non restituiscono metadati di paginazione (`total`, `pages`): la paginazione è semplice.

### Endpoint di dettaglio (GET su risorsa singola)

- Restituiscono sempre `XPublic` (versione completa).
- Identificano la risorsa tramite il suo UUID nel path (`/{resource_uuid}`).

### Endpoint di batch (POST su sotto-risorsa)

- `POST /experiments/{uuid}/metrics` accetta `MetricsBatchCreate` (lista di metriche).
- Restituisce `ExperimentMetrics` (le metriche raggruppate per split) con stato `201`.

---

## Note su DuplicateKeyError di MongoDB

Quando un'operazione di insert viola un indice unique di MongoDB (es. email già registrata, nome MLModel duplicato),
MongoDB solleva un `DuplicateKeyError`. I router di Polibench catturano questa eccezione e la trasformano in HTTP 400:

```python
from pymongo.errors import DuplicateKeyError

try:
    await new_user.create()
except DuplicateKeyError:
    raise HTTPException(status_code=400, detail="Email già in uso")
```

Questo assicura che il client riceva un errore leggibile invece di un generico HTTP 500.

