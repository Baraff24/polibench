# Indici, Query Critiche e Performance

Questo documento riepiloga le query piu importanti e gli indici MongoDB che le sostengono nel modello pipeline-first.

---

## Query critiche

### 1) Leaderboard (single metric)

Dove: `services/leaderboard.py` (`GET /api/v1/leaderboard`)

Query tipica:

```python
await Metric.find(
    Metric.dataset_id == dataset_id,
    Metric.dataset_version_id == dataset_version_id,
    Metric.pipeline_id == pipeline_id,
    Metric.metric == metric_name,
    Metric.split == split,
).sort([("value", pymongo.DESCENDING)]).limit(top_n).to_list()
```

Indice principale usato:

```text
{ dataset_id: 1, dataset_version_id: 1, pipeline_id: 1, split: 1, metric: 1, value: -1 }
```

Vantaggio: niente `$lookup` sui run per filtrare dataset/version/pipeline; i campi sono denormalizzati su `metrics`.

---

### 2) Leaderboard multi-metrica

Dove: `services/leaderboard.py` (`GET /api/v1/leaderboard/multi`)

Strategia:

1. fetch metriche per dataset/version/pipeline + split
2. gruppo per `experiment_id`
3. ordinamento secondo `sort_by` (ASC/DESC in base alla direction)

L'indice composto sopra riduce il working set anche in modalita multi.

---

### 3) Metriche per experiment

Dove: `services/metrics.py` (`GET /api/v1/experiments/{uuid}/metrics`)

```python
await Metric.find(Metric.experiment_id == experiment_id).to_list()
```

Indice utile:

```text
{ experiment_id: 1, metric: 1, split: 1 }
```

---

### 4) Pipelines per versione

Dove: `services/pipelines.py` (`GET /api/v1/dataset-versions/{uuid}/pipelines`)

```python
await Pipeline.find(Pipeline.dataset_version_id == version_id).sort([("created_at", -1)]).to_list()
```

Indice usato:

```text
{ dataset_version_id: 1, created_at: -1 }
```

---

## Indici per collezione

### `dataset_versions`

- unique composito: `{ dataset_id: 1, version: 1 }`
- supporto listing per dataset: `{ dataset_id: 1, created_at: -1 }`

### `pipelines`

- unique composito: `{ dataset_version_id: 1, code: 1 }`
- listing cronologico per versione: `{ dataset_version_id: 1, created_at: -1 }`

### `experiments`

Indici dichiarati sui campi:

- `uuid` (unique)
- `pipeline_id`
- `dataset_version_id`
- `dataset_id`
- `model_id`
- `submitted_by_user_id`
- `team_id`

### `metrics`

Indici principali:

- `uuid` (unique)
- indice composto leaderboard:
  `{ dataset_id: 1, dataset_version_id: 1, pipeline_id: 1, split: 1, metric: 1, value: -1 }`
- indice composto per lettura run:
  `{ experiment_id: 1, metric: 1, split: 1 }`

---

## Denormalizzazione: costo e vantaggio

In `ExperimentMetric` vengono duplicati campi dal run (`dataset_id`, `dataset_version_id`, `pipeline_id`, `model_id`).

Costo:

- piu spazio per documento
- write leggermente piu pesanti

Vantaggio:

- leaderboard veloce senza join
- filtri `dataset/version/pipeline` direttamente indicizzabili

Per il benchmark e un trade-off intenzionale.

---

## Rischi futuri e miglioramenti

1. Caching leaderboard (es. Redis) per dataset/version/pipeline ad alta frequenza.
2. Materialized leaderboard periodica per viste statiche.
3. Limiti e chunking per import CSV molto grandi.
4. Monitoraggio cardinalita metriche (nome metrica + split) per evitare esplosione indici non necessari.
