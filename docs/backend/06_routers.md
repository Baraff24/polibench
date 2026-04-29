# Router e Endpoint HTTP

I router si trovano in `backend/app/routers/` e sono montati in `api.py` con prefisso `/api/v1`.

```python
api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(experiments.router, tags=["experiments"])
```

`GET /api/v1/` e un health check pubblico.

---

## Principio: router sottili

I router:

1. validano input/path/query con Pydantic/FastAPI
2. applicano auth/permessi
3. delegano al service layer
4. restituiscono response model

La logica di dominio (risoluzione UUID, validazioni semantiche, denormalizzazione, query leaderboard) vive nei service.

---

## `login.py`

Prefisso: `/api/v1/login`

| Endpoint | Metodo | Auth | Output |
|----------|--------|------|--------|
| `/access-token` | POST | no | `Token` |
| `/test-token` | GET | JWT | `User` |
| `/refresh-token` | GET | cookie | `Token` |
| `/google` | GET | no | redirect |
| `/google/callback` | GET | no | redirect + cookie |

---

## `users.py`

Prefisso: `/api/v1/users`

| Endpoint | Metodo | Auth | Note |
|----------|--------|------|------|
| `/` | POST | no | registrazione + email verification |
| `/verify/{token}` | GET | no | conferma email |
| `/resend-verification` | POST | no | reinvio email |
| `/` | GET | superuser | lista utenti |
| `/me` | GET/PATCH/DELETE | utente attivo | profilo corrente |
| `/{userid}` | GET/PATCH/DELETE | superuser | gestione utente per UUID |

---

## `datasets.py` — Dataset, Versioni, Pipeline, Modelli

### Dataset

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/datasets` | POST | verificato | `DatasetPublic` |
| `/api/v1/datasets` | GET | pubblico | `list[DatasetSummary]` |
| `/api/v1/datasets/{dataset_uuid}` | GET | pubblico | `DatasetPublic` |

### DatasetVersion

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/datasets/{dataset_uuid}/versions` | GET | pubblico | `list[DatasetVersionSummary]` |
| `/api/v1/datasets/{dataset_uuid}/versions` | POST | verificato | `DatasetVersionPublic` |
| `/api/v1/datasets/{dataset_uuid}/versions/preview` | POST | verificato | `DatasetVersionPreviewPublic` |
| `/api/v1/dataset-versions/{version_uuid}` | GET | pubblico | `DatasetVersionPublic` |
| `/api/v1/dataset-versions/{version_uuid}/sources` | GET | pubblico | `list[SourcePublic]` |
| `/api/v1/dataset-versions/{version_uuid}/resources` | GET | pubblico | `list[ResourcePublic]` |
| `/api/v1/dataset-versions/{version_uuid}/sources-with-resources` | GET | pubblico | `list[SourceWithResourcesPublic]` |
| `/api/v1/dataset-versions/{version_uuid}/yaml/dataset` | GET | pubblico | `DatasetVersionYamlPublic` |
| `/api/v1/dataset-versions/{version_uuid}/yaml/version` | GET | pubblico | `DatasetVersionYamlPublic` |
| `/api/v1/dataset-versions/{version_uuid}/yaml/characteristics` | GET | pubblico | `DatasetVersionYamlPublic` |
| `/api/v1/dataset-versions/{version_uuid}/yaml/metrics` | GET | pubblico | `DatasetVersionYamlPublic` (alias) |
| `/api/v1/dataset-versions/{version_uuid}/yaml/{kind}/raw` | GET | pubblico | `text/yaml` |
| `/api/v1/dataset-versions/{version_uuid}/experiments` | GET | pubblico | `list[ExperimentSummary]` |

Nota: `DatasetVersionCreate` mantiene `pipeline_yaml_raw` solo per compatibilita transitoria.
Se valorizzato, il backend crea una prima pipeline (`P001`) come entita separata.

### Pipeline

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/dataset-versions/{version_uuid}/pipelines` | GET | pubblico | `list[PipelineSummary]` |
| `/api/v1/dataset-versions/{version_uuid}/pipelines` | POST | verificato | `PipelinePublic` |
| `/api/v1/dataset-versions/{version_uuid}/pipelines/preview` | POST | verificato | `PipelinePreviewPublic` |
| `/api/v1/pipelines/{pipeline_uuid}` | GET | pubblico | `PipelinePublic` |
| `/api/v1/pipelines/{pipeline_uuid}/yaml` | GET | pubblico | `PipelineYamlPublic` |
| `/api/v1/pipelines/{pipeline_uuid}/yaml/raw` | GET | pubblico | `text/yaml` |
| `/api/v1/pipelines/{pipeline_uuid}/experiments` | GET | pubblico | `list[ExperimentSummary]` |

### MLModel

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/ml-models` | POST | verificato | `MLModelPublic` |
| `/api/v1/ml-models` | GET | pubblico | `list[MLModelSummary]` |
| `/api/v1/ml-models/{model_uuid}` | GET | pubblico | `MLModelPublic` |

---

## `experiments.py` — Experiments, Metrics, Leaderboard

### Experiments

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/experiments` | POST | verificato | `ExperimentPublic` |
| `/api/v1/experiments/{experiment_uuid}` | GET | attivo | `ExperimentPublic` |

Flusso preferito per `POST /experiments`:

- input con `pipeline_uuid` + `model_uuid`
- `dataset_version_uuid` e `dataset_uuid` restano supportati solo come fallback legacy

### Metric import (CSV async)

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/experiments/{experiment_uuid}/metric-import` | POST | verificato | `MetricImportPublic` |
| `/api/v1/experiments/{experiment_uuid}/metric-imports` | GET | attivo | `list[MetricImportPublic]` |

### Metrics endpoint (legacy batch + read)

| Endpoint | Metodo | Auth | Response |
|----------|--------|------|----------|
| `/api/v1/experiments/{experiment_uuid}/metrics` | POST | verificato | `ExperimentMetrics` |
| `/api/v1/experiments/{experiment_uuid}/metrics` | GET | pubblico | `ExperimentMetrics` |

### Leaderboard

| Endpoint | Metodo | Auth | Query principali | Response |
|----------|--------|------|------------------|----------|
| `/api/v1/leaderboard` | GET | pubblico | `dataset_uuid`, `metric`, `split`, `top_n=10`, `dataset_version_uuid?`, `pipeline_uuid?`, `model_uuids?`, `author_uuids?` | `list[LeaderboardEntry]` |
| `/api/v1/leaderboard/multi` | GET | pubblico | `dataset_uuid`, `metrics`, `split`, `sort_by`, `top_n=20`, `dataset_version_uuid?`, `pipeline_uuid?`, `model_uuids?`, `author_uuids?` | `list[MultiMetricLeaderboardEntry]` |
| `/api/v1/leaderboard/query` | POST | pubblico | body `LeaderboardQuery` (metriche multiple, filtri model/author/hyperparams) | `list[MultiMetricLeaderboardEntry]` |
| `/api/v1/leaderboard/best-configuration` | POST | pubblico | body `BestConfigurationQuery` | `BestConfigurationResponse` |

Regola validazione:

- se passi `dataset_version_uuid`, devi passare anche `pipeline_uuid`

---

## Flusso dominio aggiornato

1. `Dataset` (catalogo)
2. `DatasetVersion` (versione dati)
3. `Pipeline` (configurazione eseguibile su una versione)
4. `Experiment` (run su pipeline)
5. `ExperimentMetric` (risultati performance, inclusi `pipeline_id` denormalizzato)

In breve: `Dataset -> DatasetVersion -> Pipeline -> Experiment -> ExperimentMetric`.
