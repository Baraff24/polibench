# Schemi API (Contratto HTTP)

Gli schemi si trovano in `backend/app/schemas/` e definiscono il contratto pubblico dell'API.
I `Document` MongoDB (`models/`) restano interni; client e frontend lavorano solo con UUID.

---

## Principio UUID-first

| Contesto | Identificatore |
|----------|----------------|
| Path params | UUID |
| Body input | UUID |
| Response output | UUID |
| Database interno | ObjectId (`_id`) |

La risoluzione `UUID -> ObjectId` avviene nel service layer.

---

## Pattern principali

Per ogni entita:

- `XBase`: campi condivisi
- `XCreate`: input client
- `XPublic`: output completo
- `XSummary`: output ridotto per liste

---

## `tokens.py`

```python
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    uuid: UUID | None = None
```

---

## `users.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `UserBase` | - | `first_name`, `last_name`, `picture` |
| `PrivateUserBase` | - | `email`, `is_active`, `is_superuser`, `provider` |
| `UserUpdate` | input | aggiornamenti profilo/credenziali |
| `User` | output | `uuid` + campi pubblici utente |

---

## `datasets.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `DatasetBase` | - | `name`, `task`, `description`, `visibility`, `team_uuid` |
| `DatasetCreate` | input | eredita `DatasetBase` |
| `DatasetPublic` | output | `uuid`, `created_by_user_uuid`, `created_at`, `versions_count`, `latest_version` |
| `DatasetSummary` | output lista | `uuid`, `name`, `task`, `visibility`, `versions_count`, `latest_version` |

Nota: `Dataset` e catalografico; non contiene pipeline o metriche esperimento.

---

## `dataset_versions.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `DatasetVersionBase` | - | `version`, `status`, `dataset_yaml_raw`, `version_yaml_raw`, `characteristics_yaml_raw` |
| `DatasetVersionCreate` | input | eredita `DatasetVersionBase`; include `pipeline_yaml_raw` solo per compatibilita transitoria |
| `DatasetVersionPublic` | output | `uuid`, `dataset_uuid`, `version`, caratteristiche denormalizzate (`n_users`, `density`, `gini_*`) |
| `DatasetVersionSummary` | output lista | versione ridotta per listing |
| `SourcePublic` | output | source parse da `version_yaml_raw` |
| `ResourcePublic` | output | risorse parse da `version_yaml_raw` |
| `SourceWithResourcesPublic` | output | source con `resources[]` annidate per UI accordion |
| `DatasetVersionYamlPublic` | output | payload YAML (`kind`, `content`) |
| `DatasetVersionPreviewPublic` | output preview | contatori parse e caratteristiche riconosciute |

---

## `pipelines.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `PipelineCreate` | input | `code?`, `yaml_raw?`, `status` |
| `PipelineBlockPublic` | output | `name`, `operation`, `params` |
| `PipelinePublic` | output | `uuid`, `dataset_version_uuid`, `code`, `status`, `blocks`, `created_at` |
| `PipelineSummary` | output lista | `uuid`, `dataset_version_uuid`, `code`, `status`, `steps_count`, `created_at` |
| `PipelineYamlPublic` | output | `pipeline_uuid`, `content` |
| `PipelinePreviewPublic` | output preview | dataset/version riconosciuti + numero step |

---

## `ml_models.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `MLModelBase` | - | `name`, `family`, `paper_url`, `implementation`, `hyperparams` |
| `MLModelCreate` | input | eredita `MLModelBase` |
| `MLModelPublic` | output | `uuid`, `created_by_user_uuid`, `created_at` |
| `MLModelSummary` | output lista | `uuid`, `name`, `family`, `paper_url` |

---

## `experiments.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `ExperimentBase` | - | `pipeline_uuid?`, `dataset_version_uuid?` (legacy), `dataset_uuid?` (legacy), `model_uuid`, `team_uuid`, `run_name`, `seed`, `notes`, `training_config`, `code` |
| `ExperimentCreate` | input | eredita `ExperimentBase` |
| `ExperimentPublic` | output | `uuid`, `dataset_uuid`, `dataset_version_uuid`, `pipeline_uuid`, `model_uuid`, `status`, `submitted_by_user_uuid`, `artifacts`, `created_at` |
| `ExperimentSummary` | output lista | `uuid`, `dataset_uuid`, `dataset_version_uuid`, `pipeline_uuid`, `pipeline_code`, `model_uuid`, `model_name`, `status`, `created_at` |

Flusso preferito: il client invia `pipeline_uuid`.
I campi `dataset_version_uuid` e `dataset_uuid` restano supportati solo in modalita compatibilita.

---

## `metrics.py`

### Input

```python
class MetricCreate(BaseModel):
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
```

```python
class MetricsBatchCreate(BaseModel):
    experiment_uuid: UUID
    metrics: list[MetricCreate]
```

### Output

```python
class MetricPublic(BaseModel):
    uuid: UUID
    experiment_uuid: UUID
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    model_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    computed_at: datetime
```

```python
class LeaderboardEntry(BaseModel):
    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    pipeline_code: str | None = None
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    training_config: dict[str, Any] | None = None
    status: str | None = None
    run_name: str | None = None
    seed: int | None = None
    created_at: datetime | None = None
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    rank: int | None = None
```

```python
class MultiMetricLeaderboardEntry(BaseModel):
    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    pipeline_code: str | None = None
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    training_config: dict[str, Any] | None = None
    status: str | None = None
    run_name: str | None = None
    seed: int | None = None
    created_at: datetime | None = None
    split: Split
    metrics: dict[str, float]
    directions: dict[str, Direction]
    repo_url: str | None = None
    rank: int | None = None
```

Nota: `Metric` contiene solo performance metric degli esperimenti.
Le dataset characteristics restano in `DatasetVersion`.

### Query leaderboard avanzate

```python
class LeaderboardQuery(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID | None = None
    pipeline_uuid: UUID | None = None
    split: Split
    metrics: list[str]
    sort_by: str | None = None
    top_n: int = 20
    model_uuids: list[UUID] | None = None
    author_uuids: list[UUID] | None = None
    hyperparam_filters: dict[str, Any] | None = None
```

```python
class BestConfigurationQuery(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID
    split: Split
    metrics: list[str] = Field(default_factory=list)
    target_metric: str
    direction: Direction
    group_by_hyperparams: list[str] = Field(default_factory=list)
    model_uuids: list[UUID] | None = None
    author_uuids: list[UUID] | None = None
    hyperparam_filters: dict[str, Any] | None = None
```

```python
class BestConfigurationGroup(BaseModel):
    model_uuid: UUID
    model_name: str | None = None
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    best_value: float
    mean_value: float
    count: int
    std: float | None = None
    best_metrics: dict[str, float] = Field(default_factory=dict)
    directions: dict[str, Direction] = Field(default_factory=dict)
    best_pipeline_uuid: UUID | None = None
    best_pipeline_code: str | None = None
    best_experiment_uuid: UUID | None = None
    best_run_name: str | None = None
    best_training_config: dict[str, Any] | None = None


class BestConfigurationResponse(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID
    split: Split
    metrics: list[str] = Field(default_factory=list)
    target_metric: str
    direction: Direction
    group_by_hyperparams: list[str] = Field(default_factory=list)
    best_group: BestConfigurationGroup | None = None
    groups: list[BestConfigurationGroup] = Field(default_factory=list)
```

`BestConfigurationQuery` confronta solo metriche della stessa `dataset_uuid`, `dataset_version_uuid`, `pipeline_uuid`, `split` e `target_metric`.
La `direction` e' quella scelta dal client e determina sia la run migliore per gruppo sia l'ordinamento dei gruppi.
Il raggruppamento e' sempre almeno per modello; `group_by_hyperparams` aggiunge eventuali chiavi di `training_config`.

---

## `metric_imports.py`

| Schema | Direzione | Campi principali |
|--------|-----------|------------------|
| `MetricImportPublic` | output | `uuid`, `experiment_uuid`, `uploaded_by_user_uuid`, `status`, `csv_filename`, `created_at`, `started_at`, `finished_at`, `error_message` |

---

## Export pubblici (`schemas/__init__.py`)

```python
from .dataset_versions import (
    DatasetVersionCreate,
    DatasetVersionPublic,
    DatasetVersionSummary,
    DatasetVersionYamlPublic,
    ResourcePublic,
    SourcePublic,
    SourceWithResourcesPublic,
)
from .datasets import DatasetCreate, DatasetPublic, DatasetSummary
from .experiments import ExperimentCreate, ExperimentPublic, ExperimentSummary
from .metric_imports import MetricImportPublic
from .metrics import (
    BestConfigurationGroup,
    BestConfigurationQuery,
    BestConfigurationResponse,
    ExperimentMetrics,
    LeaderboardQuery,
    LeaderboardEntry,
    MetricCreate,
    MetricPublic,
    MetricsBatchCreate,
    MultiMetricLeaderboardEntry,
)
from .ml_models import MLModelCreate, MLModelPublic, MLModelSummary
from .pipelines import (
    PipelineBlockPublic,
    PipelineCreate,
    PipelinePreviewPublic,
    PipelinePublic,
    PipelineSummary,
    PipelineYamlPublic,
)
from .tokens import Token, TokenPayload
from .users import User, UserUpdate
```
