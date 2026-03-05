# Modelli Dati

> Il diagramma UML completo si trova in [`docs/backend/domain_model.puml`](./domain_model.puml).
> Rappresenta il **DB layer** (MongoDB/Beanie). Il principio UUID-first si applica all'**API layer**:
> `_id` e gli ObjectId interni non vengono mai esposti al client.

I modelli dati si trovano in `backend/app/models/`. Ogni file definisce una o più classi che estendono
`beanie.Document`, ciascuna corrispondente a una collezione MongoDB. Tutti i modelli sono registrati in
`models/__init__.py` tramite la lista `DOCUMENT_MODELS`, che viene passata a `init_beanie()` all'avvio dell'
applicazione.

```python
# models/__init__.py
DOCUMENT_MODELS = [Dataset, Experiment, Metric, MLModel, Team, User]
```

---

## Convenzioni comuni a tutti i modelli

### Doppio identificatore: `_id` e `uuid`

Ogni Document ha due identificatori:

- **`_id`** (ObjectId): assegnato automaticamente da MongoDB, usato internamente per le relazioni tra documenti. Non
  viene mai esposto direttamente al frontend.
- **`uuid`** (UUID4): generato da Python con `default_factory=uuid4`, usato come identificatore pubblico nell'API. Il
  frontend usa sempre UUID, mai ObjectId.

```python
uuid: Annotated[UUID, Field(default_factory=uuid4), Indexed(unique=True)]
```

### Timestamp di creazione

Tutti i modelli hanno un campo `created_at` popolato automaticamente all'inserimento:

```python
created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

Si usa `datetime.now(UTC)` con il timezone esplicito `UTC`, in quanto `datetime.utcnow()` è deprecato da Python 3.12.

### Indici

Gli indici vengono dichiarati direttamente nell'annotazione del campo tramite `Annotated` e `Indexed()` di Beanie.
L'indice unico su `uuid` garantisce che non possano esistere due documenti con lo stesso UUID pubblico.

---

## User

**File**: `models/users.py`  
**Collezione MongoDB**: `users`

Rappresenta un utente della piattaforma.

| Campo             | Tipo               | Indice | Note                             |
|-------------------|--------------------|--------|----------------------------------|
| `uuid`            | `UUID`             | unique | Identificatore pubblico          |
| `email`           | `EmailStr`         | unique | Validata da Pydantic             |
| `first_name`      | `str \| None`      | —      | Opzionale                        |
| `last_name`       | `str \| None`      | —      | Opzionale                        |
| `hashed_password` | `str \| None`      | —      | `None` per utenti SSO            |
| `provider`        | `str \| None`      | —      | Es. `"google"` per SSO           |
| `picture`         | `str \| None`      | —      | URL avatar (da SSO)              |
| `role`            | `UserRole`         | —      | `admin`, `researcher`, `viewer`  |
| `team_uuid`       | `UUID \| None`     | sì     | Riferimento al Team tramite UUID |
| `is_active`       | `bool`             | —      | Default `True`                   |
| `is_superuser`    | `bool`             | —      | Default `False`                  |
| `created_at`      | `datetime`         | —      | Timestamp creazione              |
| `last_login_at`   | `datetime \| None` | —      | Ultimo accesso                   |

**Note di progettazione**:

- `hashed_password` è `None` per gli utenti che si autenticano tramite Google SSO, i quali non hanno una password
  locale.
- Il riferimento a `Team` usa `team_uuid` (UUID) invece di un ObjectId, coerentemente con il principio di non esporre
  identificatori interni.

---

## Team

**File**: `models/teams.py`  
**Collezione MongoDB**: `teams`

Rappresenta un gruppo di ricerca. Gli utenti appartengono a un team tramite `User.team_uuid`.

| Campo             | Tipo           | Indice | Note                          |
|-------------------|----------------|--------|-------------------------------|
| `uuid`            | `UUID`         | unique | Identificatore pubblico       |
| `name`            | `str`          | unique | Nome univoco del team         |
| `description`     | `str \| None`  | —      | Descrizione opzionale         |
| `owner_user_uuid` | `UUID \| None` | —      | UUID dell'utente proprietario |
| `created_at`      | `datetime`     | —      | Timestamp creazione           |

---

## Dataset

**File**: `models/datasets.py`  
**Collezione MongoDB**: `datasets`

Rappresenta un dataset di valutazione con le relative caratteristiche e partizioni.

| Campo                | Tipo                       | Indice | Note                                  |
|----------------------|----------------------------|--------|---------------------------------------|
| `uuid`               | `UUID`                     | unique | Identificatore pubblico               |
| `name`               | `str`                      | —      | Nome del dataset (es. "MovieLens-1M") |
| `version`            | `str`                      | —      | Versione (es. "1.0")                  |
| `task`               | `TaskType`                 | —      | `ranking` o `rating_prediction`       |
| `description`        | `str \| None`              | —      | Descrizione opzionale                 |
| `visibility`         | `Visibility`               | —      | `public` o `private`                  |
| `splits`             | `Splits \| None`           | —      | Sotto-documento con conteggi          |
| `team_id`            | `PydanticObjectId \| None` | sì     | FK verso Team                         |
| `created_by_user_id` | `PydanticObjectId \| None` | sì     | FK verso User                         |
| `created_at`         | `datetime`                 | —      | Timestamp creazione                   |

**Sotto-documento `Splits`** (classe `BaseModel`):

```python
class Splits(BaseModel):
    train: int | None = None
    test: int | None = None
    validation: int | None = None
```

**Enumerazioni**:

- `TaskType`: `ranking` | `rating_prediction`
- `Visibility`: `public` | `private`

---

## MLModel

**File**: `models/ml_models.py`  
**Collezione MongoDB**: `models`

Rappresenta un **algoritmo** di raccomandazione registrato nella piattaforma. Non rappresenta un'istanza addestrata, ma
la famiglia algoritmica (es. "BPR-MF", "LightGCN").

| Campo                | Tipo                       | Indice | Note                                          |
|----------------------|----------------------------|--------|-----------------------------------------------|
| `uuid`               | `UUID`                     | unique | Identificatore pubblico                       |
| `name`               | `str`                      | unique | Nome univoco dell'algoritmo                   |
| `family`             | `str \| None`              | —      | Es. "matrix_factorization", "graph"           |
| `paper_url`          | `str \| None`              | —      | URL al paper di riferimento                   |
| `implementation`     | `str \| None`              | —      | URL alla repo di implementazione              |
| `hyperparams`        | `dict[str, Any] \| None`   | —      | Configurazione canonica dell'algoritmo (opz.) |
| `created_by_user_id` | `PydanticObjectId \| None` | sì     | FK verso User                                 |
| `created_at`         | `datetime`                 | —      | Timestamp creazione                           |

**Nota su `hyperparams`**: appartiene a `MLModel` perché rappresenta la configurazione canonica dell'algoritmo
(es. i valori di default riportati nel paper di riferimento: `{"factors": 64, "lr": 0.01}`).
Variazioni run-specific (seed, scheduler) appartengono a `Experiment.training_config`.

---

## Experiment

**File**: `models/experiments.py`  
**Collezione MongoDB**: `experiments`

Rappresenta una **run sperimentale**: l'esecuzione di un algoritmo su un dataset con una configurazione specifica. È
l'entità centrale del sistema.

| Campo                  | Tipo                       | Indice | Note                            |
|------------------------|----------------------------|--------|---------------------------------|
| `uuid`                 | `UUID`                     | unique | Identificatore pubblico         |
| `dataset_id`           | `PydanticObjectId`         | sì     | FK verso Dataset                |
| `model_id`             | `PydanticObjectId`         | sì     | FK verso MLModel                |
| `submitted_by_user_id` | `PydanticObjectId`         | sì     | FK verso User                   |
| `team_id`              | `PydanticObjectId \| None` | sì     | FK verso Team (opzionale)       |
| `run_name`             | `str \| None`              | —      | Nome descrittivo della run      |
| `status`               | `Status`                   | —      | Stato della run                 |
| `training_config`      | `dict[str, Any] \| None`   | —      | Configurazione run-specific     |
| `seed`                 | `int \| None`              | —      | Seed per riproducibilità        |
| `notes`                | `str \| None`              | —      | Note libere                     |
| `code`                 | `CodeInfo \| None`         | —      | Informazioni sul codice         |
| `artifacts`            | `Artifacts \| None`        | —      | Path a log, modello, predizioni |
| `created_at`           | `datetime`                 | —      | Timestamp creazione             |
| `finished_at`          | `datetime \| None`         | —      | Timestamp completamento         |

**Enumerazione `Status`**: `queued` | `running` | `finished` | `failed`

**Sotto-documento `CodeInfo`**:

```python
class CodeInfo(BaseModel):
    git_commit: str | None = None
    repo_url: str | None = None
    docker_image: str | None = None
```

**Sotto-documento `Artifacts`**:

```python
class Artifacts(BaseModel):
    logs_url: str | None = None
    model_path: str | None = None
    predictions_path: str | None = None
```

---

## Metric

**File**: `models/metrics.py`  
**Collezione MongoDB**: `metrics`

Rappresenta il risultato numerico di un esperimento per una specifica metrica e split. È il modello più critico per le
performance, in quanto è quello su cui si eseguono le query di leaderboard.

| Campo                  | Tipo                       | Indice | Note                              |
|------------------------|----------------------------|--------|-----------------------------------|
| `uuid`                 | `UUID`                     | unique | Identificatore pubblico           |
| `experiment_id`        | `PydanticObjectId`         | sì     | FK verso Experiment               |
| `dataset_id`           | `PydanticObjectId`         | sì     | FK denormalizzato da Experiment   |
| `model_id`             | `PydanticObjectId`         | sì     | FK denormalizzato da Experiment   |
| `submitted_by_user_id` | `PydanticObjectId \| None` | sì     | FK denormalizzato                 |
| `team_id`              | `PydanticObjectId \| None` | sì     | FK denormalizzato                 |
| `split`                | `Split`                    | —      | `validation` o `test`             |
| `metric`               | `str`                      | sì     | Nome metrica (es. "ndcg@10")      |
| `k`                    | `int \| None`              | —      | Cutoff per metriche @k            |
| `value`                | `float`                    | —      | Valore numerico del risultato     |
| `direction`            | `Direction`                | —      | `max` (più alto = meglio) o `min` |
| `computed_at`          | `datetime`                 | —      | Timestamp calcolo metrica         |

**Enumerazioni**:

- `Split`: `validation` | `test`
- `Direction`: `max` | `min`

### Denormalizzazione intenzionale

`dataset_id`, `model_id`, `submitted_by_user_id` e `team_id` sono campi **denormalizzati**: duplicano informazioni già
presenti nell'`Experiment` collegato. Questa scelta è deliberata per motivi di performance:

La query di leaderboard — che è la query più frequente e critica del sistema — richiede di filtrare per `dataset_id`,
`split` e `metric` e ordinare per `value`. Se `dataset_id` non fosse nella collezione `metrics`, la query richiederebbe
una join con `experiments`, che in MongoDB è costosa (aggregation pipeline `$lookup`). Con la denormalizzazione, la
query è un semplice `find()` con indici:

```python
await Metric.find(
    Metric.dataset_id == dataset_id,
    Metric.split == Split.TEST,
    Metric.metric == "ndcg@10",
).sort(-Metric.value).limit(10).to_list()
```

Il costo è un leggero aumento dello spazio occupato su disco e la necessità di mantenere la coerenza al momento
dell'inserimento (il router deve copiare `dataset_id` e `model_id` dall'`Experiment` nel `Metric`).

---

## Relazioni tra entità

```
User ──────────────────────────────── crea ──→ Dataset
User ──────────────────────────────── crea ──→ MLModel
User ──────────────────────────────── sottomette ──→ Experiment
User ──────────────────────── appartiene a ──→ Team

Team ──────────────────────── possiede ──→ Dataset
Team ──────────────────────── possiede ──→ Experiment

Dataset ──┐
          ├──→ Experiment ──→ Metric (×N)
MLModel ──┘
```

Una singola coppia `(Dataset, MLModel)` può avere più `Experiment` (run diverse con seed o configurazioni diverse). Ogni
`Experiment` produce N `Metric`, una per ogni combinazione di `(split, metric_name)`.

