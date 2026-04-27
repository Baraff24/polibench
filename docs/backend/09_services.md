# Service Layer

Il service layer (`backend/app/services/`) contiene la logica di business:

- risoluzione UUID -> Document
- validazioni semantiche
- parse YAML
- denormalizzazione per query veloci
- trasformazione Document -> schema pubblico

I router restano sottili e delegano tutto qui.

---

## Struttura attuale

```text
services/
├── datasets.py         # Dataset + MLModel
├── dataset_versions.py # DatasetVersion + Source/Resource + YAML dataset/version/characteristics
├── pipelines.py        # Pipeline create/list/preview/yaml/experiments
├── experiments.py      # Experiment create/get/list
├── metrics.py          # Metric batch + read per experiment
├── metric_imports.py   # CSV import async jobs
├── leaderboard.py      # leaderboard single/multi con filtri versione/pipeline
└── email.py            # token verifica email + SMTP
```

---

## `datasets.py`

Responsabilita principali:

- risolvere `dataset_uuid`, `model_uuid`, `team_uuid`
- creare/listare dataset e modelli
- conversione in `DatasetPublic`/`DatasetSummary` e `MLModelPublic`/`MLModelSummary`

Pattern usato ovunque:

```python
async def get_x_by_uuid(x_uuid: UUID) -> X:
    doc = await X.find_one(X.uuid == x_uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="... non trovato")
    return doc
```

---

## `dataset_versions.py`

Responsabilita principali:

- creare/listare/dettagliare `DatasetVersion`
- parse e validazione YAML:
  - dataset-level (`dataset_yaml_raw`)
  - version-level (`version_yaml_raw`)
  - characteristics (`characteristics_yaml_raw`)
- materializzare `Source` e `Resource` da version YAML
- estrarre caratteristiche denormalizzate (`n_users`, `density`, `gini_*`)
- endpoint YAML per `dataset`, `version`, `characteristics`

Validazioni chiave:

- `dataset_name` e `version` nel version YAML devono combaciare col target
- `dataset_name` e `version` nel metrics/characteristics YAML devono combaciare col target
- `resource.source_name` deve riferire una source esistente
- `downloadable=true` richiede `url`
- `checksum` richiede `checksum_algorithm`

Compatibilita transitoria:

- se in create versione arriva anche `pipeline_yaml_raw`, il service crea una prima `Pipeline` separata
  tramite `create_pipeline_for_version(...)`

---

## `pipelines.py`

Nuovo service centrale per il modello pipeline-first.

Responsabilita principali:

- parse YAML pipeline
- normalizzazione step in `blocks` (per UI a blocchi/chain)
- validazioni coerenza con dataset/version target
- creazione pipeline con `code` non semantico (`P001`, `P002`, ...)
- list/dettaglio pipeline
- retrieval YAML pipeline
- preview parse prima del submit
- lista esperimenti legati alla pipeline
- helper `get_latest_pipeline_for_dataset_version(...)` per fallback legacy

---

## `experiments.py`

Responsabilita principali:

- creare un `Experiment` privilegiando `pipeline_uuid`
- fallback legacy da `dataset_version_uuid` / `dataset_uuid`
- denormalizzare `dataset_version_id` e `dataset_id` dentro `Experiment`
- leggere dettaglio run con UUID risolti
- listare esperimenti per dataset version o pipeline

Flusso `create_experiment(...)`:

1. risolve pipeline (path principale) oppure fallback legacy
2. risolve model
3. imposta `submitted_by_user_id` da JWT
4. salva `pipeline_id`, `dataset_version_id`, `dataset_id`, `model_id`
5. ritorna `ExperimentPublic` con UUID e metadati pipeline

---

## `metrics.py`

Responsabilita principali:

- inserimento batch metriche (endpoint legacy diretto)
- lettura metriche per esperimento
- denormalizzazione lato write per query veloci

Durante il write ogni `ExperimentMetric` riceve:

- `experiment_id`
- `dataset_id`
- `dataset_version_id`
- `pipeline_id`
- `model_id`
- eventuali `submitted_by_user_id`/`team_id`

Questo mantiene la leaderboard senza join costose.

---

## `metric_imports.py`

Gestisce import CSV asincrono.

Flusso:

1. crea `MetricImportJob` (`uploaded`)
2. worker async porta a `processing`
3. parse CSV
4. sostituisce metriche precedenti della run e salva nuove `ExperimentMetric`
5. aggiorna stato job (`completed`/`failed`)

Anche qui le metriche persistite includono `pipeline_id` denormalizzato.

---

## `leaderboard.py`

Responsabilita principali:

- leaderboard single metric (`get_leaderboard`)
- leaderboard multi-metric (`get_multi_metric_leaderboard`)
- validazione coerenza tra `dataset_uuid`, `dataset_version_uuid` e `pipeline_uuid`

Regola importante:

- se filtri per dataset version, il filtro pipeline deve essere consistente con quella versione

Query model:

- filtro diretto su collezione `metrics`
- ordinamento per `value` con indici composti
- batch fetch di `Experiment`, `MLModel`, `Pipeline`, `DatasetVersion` per arricchire response

---

## `email.py`

Gestisce token di verifica email e invio SMTP.

- `create_verification_token(user_uuid)`
- `verify_email_token(token)`
- `send_verification_email(to_email, token)`

Se SMTP non e configurato, in sviluppo logga il link senza bloccare la registrazione.

---

## Relazione con il dominio

Il service layer implementa concretamente il modello:

`Dataset -> DatasetVersion -> Pipeline -> Experiment -> ExperimentMetric`

e mantiene separati:

- dataset characteristics (in `DatasetVersion`)
- experiment performance metrics (in `ExperimentMetric`)
