# Schemi API (Contratto HTTP)

Gli schemi si trovano in `backend/app/schemas/`. Definiscono il **contratto pubblico dell'API**: la forma esatta dei
dati che il client può inviare e che il server restituisce. Sono completamente separati dai modelli dati (Document
MongoDB).

---

## Principio UUID-first

L'intera API segue un principio unico e consistente:

| Contesto        | Identificatore usato | Note                                    |
|-----------------|----------------------|-----------------------------------------|
| Path params     | UUID                 | `GET /datasets/{dataset_uuid}`          |
| Body input      | UUID                 | `dataset_uuid: UUID`, mai ObjectId      |
| Response output | UUID                 | `uuid` è l'unico identificatore esposto |
| Interno al DB   | ObjectId (`_id`)     | Mai esposto all'esterno                 |

**Motivazioni:**

- **Stabilità**: se il DB cambia (es. da MongoDB a PostgreSQL), i client non cambiano nulla
- **No leakage**: `_id` MongoDB è un dettaglio implementativo, non un contratto pubblico
- **Ergonomia CLI/script**: chi consuma l'API ragiona con UUID leggibili, non con ObjectId opachi
- **Sicurezza/opsec**: non si regalano informazioni strutturali sul DB

Il router è il solo punto dove avviene la risoluzione `UUID → ObjectId`, internamente e in modo trasparente al client.

---

## Principio fondamentale: separazione model / schema

|            | `models/` (Document)            | `schemas/` (BaseModel)     |
|------------|---------------------------------|----------------------------|
| Scopo      | Rappresentare MongoDB           | Contratto HTTP             |
| Visibilità | Solo backend                    | Pubblica (OpenAPI)         |
| Contiene   | Campi interni, indici, ObjectId | Solo UUID, campi API       |
| Esempio    | `hashed_password`, `_id`        | Mai in uno schema pubblico |

---

## Pattern di ereditarietà

Per ogni entità si seguono queste convenzioni:

```
XBase                campi condivisi tra Create e Public
  ├── XCreate        quello che il CLIENT manda (eredita Base, aggiunge nulla)
  └── XPublic        quello che l'API RITORNA (eredita Base, aggiunge uuid/timestamps)
XSummary             versione ridotta per liste (classe piatta, NON eredita Base)
```

`XSummary` è sempre una classe piatta perché deve **omettere** campi presenti in `Base`. In Pydantic v2 non è possibile
rimuovere un campo ereditato.

### Regola pratica

- Usa `Base` quando le sottoclassi **aggiungono** campi → ereditarietà pulita
- Usa classe piatta quando una sottoclasse deve **omettere** campi → nessuna ereditarietà

---

## `populate_by_name` e alias — non più necessari

Con il passaggio al principio UUID-first, nessuno schema pubblico usa più `Field(alias="_id")`. Di conseguenza
`model_config = {"populate_by_name": True}` è stato rimosso da tutti gli schemi: non c'è più nessun alias da gestire.

---

## Schemi per entità

### tokens.py

```python
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    uuid: UUID | None = None
```

`Token` è la risposta del login. `TokenPayload` è il payload decodificato dal JWT.

---

### users.py

| Schema                      | Direzione | Campi principali                                   |
|-----------------------------|-----------|----------------------------------------------------|
| `UserBase`                  | —         | `first_name`, `last_name`, `picture`               |
| `PrivateUserBase(UserBase)` | —         | `+ email`, `is_active`, `is_superuser`, `provider` |
| `UserUpdate(UserBase)`      | → input   | `+ password`, `email`, `is_active`, `is_superuser` |
| `User(PrivateUserBase)`     | ← output  | `+ uuid`                                           |

`uuid` è l'unico identificatore nella risposta. Niente `_id`.

---

### datasets.py

| Schema                       | Direzione      | Campi principali                                                              |
|------------------------------|----------------|-------------------------------------------------------------------------------|
| `DatasetBase`                | —              | `name`, `version`, `task`, `description`, `visibility`, `splits`, `team_uuid` |
| `DatasetCreate(DatasetBase)` | → input        | (eredita tutto da Base)                                                       |
| `DatasetPublic(DatasetBase)` | ← output       | `+ uuid`, `created_by_user_uuid`, `created_at`                                |
| `DatasetSummary`             | ← output lista | `uuid`, `name`, `version`, `task`, `visibility`                               |

Tutti i riferimenti a entità esterne usano UUID: `team_uuid` nell'input, `created_by_user_uuid` nell'output.

---

### ml_models.py

| Schema                       | Direzione      | Campi principali                                               |
|------------------------------|----------------|----------------------------------------------------------------|
| `MLModelBase`                | —              | `name`, `family`, `paper_url`, `implementation`, `hyperparams` |
| `MLModelCreate(MLModelBase)` | → input        | (eredita tutto da Base)                                        |
| `MLModelPublic(MLModelBase)` | ← output       | `+ uuid`, `created_by_user_uuid`, `created_at`                 |
| `MLModelSummary`             | ← output lista | `uuid`, `name`, `family`, `paper_url`                          |

`hyperparams` appartiene a `MLModel` (configurazione canonica dell'algoritmo, es. i valori di default del paper).
`Experiment` usa `training_config` per variazioni run-specific (seed, batch size, scheduler).

---

### experiments.py

| Schema                             | Direzione      | Campi principali                                                                                  |
|------------------------------------|----------------|---------------------------------------------------------------------------------------------------|
| `ExperimentBase`                   | —              | `dataset_uuid`, `model_uuid`, `team_uuid`, `run_name`, `seed`, `notes`, `training_config`, `code` |
| `ExperimentCreate(ExperimentBase)` | → input        | (eredita tutto da Base)                                                                           |
| `ExperimentPublic(ExperimentBase)` | ← output       | `+ uuid`, `submitted_by_user_uuid`, `status`, `artifacts`, `created_at`, `finished_at`            |
| `ExperimentSummary`                | ← output lista | `uuid`, `dataset_uuid`, `model_uuid`, `run_name`, `status`, `created_at`                          |

**Campi esclusi da `ExperimentCreate`** (gestiti dal server):

- `submitted_by_user_uuid`: estratto dal token JWT nel router
- `status`: parte sempre da `queued`
- `created_at`: timestamp server

---

### metrics.py

#### MetricCreate

Una singola metrica all'interno di un batch. Non include riferimenti ad altre entità: li fornisce il batch.

```python
class MetricCreate(BaseModel):
    split: Split
    metric: str  # es. "ndcg@10", "recall@20", "rmse"
    k: int | None = None
    value: float
    direction: Direction
```

#### MetricsBatchCreate

Input per `POST /experiments/{uuid}/metrics`. Il client sottomette tutte le metriche di una run in una sola chiamata. Il
router:

1. risolve `experiment_uuid` → Document `Experiment`
2. copia `dataset_id` e `model_id` dall'Experiment (denormalizzazione, interna al server)
3. crea un Document `Metric` per ogni `MetricCreate`
4. salva tutto in bulk

```python
class MetricsBatchCreate(BaseModel):
    experiment_uuid: UUID
    metrics: list[MetricCreate]
```

#### MetricPublic

Risposta per una singola metrica. Tutti i riferimenti sono UUID.

```python
class MetricPublic(BaseModel):
    uuid: UUID
    experiment_uuid: UUID
    dataset_uuid: UUID
    model_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    computed_at: datetime
```

#### LeaderboardEntry

Schema appiattito per una riga del leaderboard. Tutti i riferimenti sono UUID. `model_name` e `rank` sono calcolati dal
router.

```python
class LeaderboardEntry(BaseModel):
    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None  # popolato dal router
    dataset_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    rank: int | None = None  # calcolato dal router
```

#### ExperimentMetrics

Risposta per `GET /experiments/{uuid}/metrics`. `experiment_uuid` è UUID. Le metriche sono raggruppate per split.

```python
class ExperimentMetrics(BaseModel):
    experiment_uuid: UUID
    metrics_by_split: dict[Split, list[MetricPublic]]
```

---

## Esportazioni pubbliche (`schemas/__init__.py`)

```python
from .datasets import DatasetCreate, DatasetPublic, DatasetSummary
from .experiments import ExperimentCreate, ExperimentPublic, ExperimentSummary
from .metrics import (
    ExperimentMetrics,
    LeaderboardEntry,
    MetricCreate,
    MetricPublic,
    MetricsBatchCreate,
)
from .ml_models import MLModelCreate, MLModelPublic, MLModelSummary
from .tokens import Token, TokenPayload
from .users import User, UserUpdate
```
