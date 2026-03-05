# Service Layer

Il service layer si trova in `backend/app/services/`. Contiene **tutta la logica di business** del backend:
risoluzione UUID→ObjectId, creazione e validazione delle entità, query al database, aggregazioni e denormalizzazione.

---

## Perché un service layer separato

I router FastAPI devono restare "sottili": ricevono la richiesta HTTP, estraggono i parametri, delegano al service e
restituiscono la risposta. Mettere logica nei router porta a codice difficile da testare e da riutilizzare.

Il service layer risolve questo problema:

| Router (sottile)              | Service (logica)                             |
|-------------------------------|----------------------------------------------|
| Estrae body, path params, JWT | Risolve UUID → Document (con 404 se assente) |
| Chiama il service             | Crea e salva Document MongoDB                |
| Ritorna la risposta HTTP      | Converte Document → Schema pubblico          |
|                               | Gestisce la denormalizzazione                |
|                               | Esegue query e aggregazioni                  |

---

## Struttura dei file

```
services/
├── __init__.py
├── datasets.py      ← Dataset + MLModel (creazione, listing, dettaglio)
├── experiments.py   ← Experiment (creazione, lettura, conversione UUID)
├── metrics.py       ← Metric (batch insert, raggruppamento per split)
└── leaderboard.py   ← Query leaderboard top-N
```

---

## services/datasets.py

### Helper di risoluzione UUID → Document

```python
async def get_dataset_by_uuid(dataset_uuid: UUID) -> Dataset


    async def get_ml_model_by_uuid(model_uuid: UUID) -> MLModel


    async def get_team_by_uuid(team_uuid: UUID) -> Team
```

Questi helper sono usati sia internamente che dai service di `experiments.py` (per risolvere `dataset_uuid` e
`model_uuid` durante la creazione di un Experiment). Se il Document non esiste, sollevano `HTTPException(404)`.

### Creazione Dataset

```python
async def create_dataset(data: DatasetCreate, current_user: User) -> DatasetPublic
```

**Flusso**:

1. Se `data.team_uuid` è presente → chiama `get_team_by_uuid` per ottenere il Document `Team`
2. Crea il Document `Dataset` con:
    - `team_id = team_doc.id` (ObjectId interno, non esposto)
    - `created_by_user_id = current_user.id` (estratto dalla dipendenza JWT)
3. Chiama `_dataset_to_public(dataset, creator, team)` per costruire la risposta

### Conversione _dataset_to_public

```python
def _dataset_to_public(dataset, creator, team) -> DatasetPublic
```

Funzione pura che converte un Document `Dataset` (con ObjectId interni) in `DatasetPublic` (con solo UUID).
Riceve `team` e `creator` già risolti come parametri: non fa query al DB.

### Lettura Dataset (con risoluzione completa)

```python
async def get_dataset_public(dataset_uuid: UUID) -> DatasetPublic
```

Usata da `GET /datasets/{uuid}`. Risolve:

- `dataset_uuid → Dataset`
- `dataset.team_id → Team → team.uuid`
- `dataset.created_by_user_id → User → user.uuid`

Poi chiama `_dataset_to_public` con i Document già risolti.

### MLModel — pattern identico

Le funzioni `create_ml_model`, `list_ml_models`, `get_ml_model_public_by_uuid` seguono lo stesso pattern
del Dataset. `_model_to_public` e `_model_to_summary` sono le funzioni di conversione analoghe.

> **Nota**: `_model_to_public` **non include** il campo `hyperparams` nella risposta pubblica per semplicità
> dell'attuale implementazione. Se necessario, può essere aggiunto a `MLModelPublic`.

---

## services/experiments.py

### Helper di risoluzione

```python
async def get_experiment_by_uuid(experiment_uuid: UUID) -> Experiment
```

Usato sia internamente che da `services/metrics.py`.

### Creazione Experiment

```python
async def create_experiment(data: ExperimentCreate, current_user: User) -> ExperimentPublic
```

**Flusso**:

1. Risolve `data.dataset_uuid → Dataset` (404 se non esiste)
2. Risolve `data.model_uuid → MLModel` (404 se non esiste)
3. Crea il Document `Experiment` con:
    - `dataset_id = dataset.id`, `model_id = model.id` (ObjectId interni)
    - `submitted_by_user_id = current_user.id` (dal JWT, non dal client)
    - `status = Status.QUEUED` (fissato lato server)
4. Chiama `_experiment_to_public(exp, data, current_user)` per la risposta

**Ottimizzazione post-creazione**: `_experiment_to_public` usa i UUID già noti dal payload `data` invece di fare
ulteriori query al DB. Questo evita 2 round-trip inutili subito dopo la creazione.

### Lettura Experiment (risoluzione completa)

```python
async def get_experiment_public(experiment_uuid: UUID) -> ExperimentPublic
```

Usata da `GET /experiments/{uuid}`. Risolve tutti gli ObjectId interni:

- `dataset_id → Dataset → uuid`
- `model_id → MLModel → uuid`
- `submitted_by_user_id → User → uuid`
- `team_id → Team → uuid` (se presente)

---

## services/metrics.py

### Inserimento batch

```python
async def create_metrics_batch(data: MetricsBatchCreate) -> None
```

**Flusso**:

1. Risolve `data.experiment_uuid → Experiment`
2. Per ogni `MetricCreate` nel batch, costruisce un Document `Metric` **copiando** dall'Experiment:
    - `experiment_id`, `dataset_id`, `model_id` → denormalizzazione intenzionale
    - `submitted_by_user_id`, `team_id` → denormalizzazione opzionale
3. Inserisce tutti in bulk con `Metric.insert_many(documents)`

Non ritorna nulla: è il router a chiamare `get_experiment_metrics` per costruire la risposta.

**Denormalizzazione**: i campi `dataset_id` e `model_id` vengono copiati dall'Experiment nel Metric per consentire
query di leaderboard veloci (senza `$lookup`). Il costo è accettabile: vengono scritti una volta sola al momento
della submission.

### Lettura metriche per experiment

```python
async def get_experiment_metrics(experiment_uuid) -> ExperimentMetrics
```

**Flusso**:

1. Risolve `experiment_uuid → Experiment`
2. Fetch tutte le `Metric` con `experiment_id == exp.id`
3. Risolve `dataset_id → Dataset` e `model_id → MLModel` **una volta sola** (non in loop)
4. Per ogni Metric costruisce `MetricPublic` con UUID risolti
5. Raggruppa in `dict[Split, list[MetricPublic]]` (struttura di `ExperimentMetrics.metrics_by_split`)

---

## services/leaderboard.py

```python
async def get_leaderboard(
        dataset_uuid: UUID,
        metric: str,
        split: Split,
        top_n: int = 10,
) -> list[LeaderboardEntry]
```

**Flusso**:

1. Risolve `dataset_uuid → Dataset` (404 se non esiste)
2. Query su `Metric`:
   ```python
   Metric.find(
       Metric.dataset_id == dataset.id,
       Metric.metric == metric,
       Metric.split == split,
   ).sort([("value", pymongo.DESCENDING)]).limit(top_n)
   ```
3. Raccoglie tutti gli `model_id` e `experiment_id` distinti nei risultati
4. **Batch fetch**: una singola query per tutti i `MLModel` distinti, una per tutti gli `Experiment` distinti
   (evita N+1 query)
5. Costruisce dizionari `model_name_by_id`, `model_uuid_by_id`, `exp_uuid_by_id`
6. Assembla `list[LeaderboardEntry]` con `rank` progressivo (1-based, da `enumerate(..., start=1)`)

**Perché è veloce**: la query su `Metric` usa l'indice composto `{dataset_id, metric, split, value: -1}`.
Non ci sono join (niente `$lookup`): `dataset_id` è già nel Metric per effetto della denormalizzazione.
Il batch fetch di MLModel e Experiment avviene con `{"_id": {"$in": [...]}}` — una sola query per ciascuno.

---

## Pattern ricorrenti

### Risoluzione UUID → Document con 404

Tutti i service usano questo pattern:

```python
async def get_XXX_by_uuid(uuid: UUID) -> XXX:
    doc = await XXX.find_one(XXX.uuid == uuid)
    if doc is None:
        raise HTTPException(status_code=404, detail="XXX non trovato")
    return doc
```

Centralizzare la risoluzione in una funzione dedicata garantisce che:

- il messaggio di errore sia consistente
- il codice HTTP sia sempre 404 (non 500)
- il service chiamante non debba gestire `None`

### Conversione Document → Schema pubblico

Le funzioni `_xxx_to_public` e `_xxx_to_summary` sono funzioni pure (nessuna query al DB):

- ricevono Document già risolti come parametri
- restituiscono uno schema Pydantic
- nessun side effect

Questo le rende facilmente testabili in isolamento.

