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
├── email.py         ← Token di verifica email e invio SMTP
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

> **Nota**: `_model_to_public` include il campo `hyperparams` nella risposta pubblica `MLModelPublic`.

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

### get_multi_metric_leaderboard (stile BARS)

```python
async def get_multi_metric_leaderboard(
        dataset_uuid: UUID,
        metrics_list: list[str],
        split: Split,
        sort_by: str,
        top_n: int = 20,
) -> list[MultiMetricLeaderboardEntry]
```

**Flusso**:

1. Risolve `dataset_uuid → Dataset` (404 se non esiste)
2. Fetch tutte le `Metric` per `(dataset_id, split)` dove `metric ∈ metrics_list`
3. Raggruppa per `experiment_id`: ogni experiment ottiene un dizionario `{metric_name: Metric}`
4. Determina la `direction` della metrica `sort_by` (max → DESC, min → ASC)
5. Ordina per il valore della metrica `sort_by` e limita a `top_n`
6. Batch fetch di `Experiment` e `MLModel` per popolare `model_name`, `repo_url`
7. Assembla `MultiMetricLeaderboardEntry` con `metrics: dict[str, float]`, `directions: dict[str, Direction]`

Questo endpoint alimenta la leaderboard multi-colonna nel frontend (con grafico Recharts).
È ispirato alla BARS CTR Leaderboard di OpenBenchmark.

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

---

## services/email.py

Gestisce la generazione dei token di verifica email e l'invio tramite SMTP.

### Funzioni principali

```python
def create_verification_token(user_uuid: UUID) -> str
```

Genera un JWT con `purpose: email-verification`, `sub: user.uuid` e scadenza di 48 ore. Usa la stessa `SECRET_KEY`
dei token di login, ma si distingue per il campo `purpose`.

```python
def verify_email_token(token: str) -> UUID | None
```

Decodifica il token, verifica che `purpose == "email-verification"` e ritorna lo UUID dell'utente. Ritorna `None`
se il token è scaduto, malformato o non ha il purpose corretto.

```python
def send_verification_email(to_email: str, token: str) -> None
```

Costruisce un'email HTML con il link di verifica (`{FRONTEND_URL}/verify-email?token={token}`) e la invia via SMTP.

**Fallback senza SMTP**: se `SMTP_HOST` non è configurato, la funzione logga il link di verifica nella console
del backend tramite `logger.warning()` e ritorna senza errore. Questo permette di completare il flusso di
registrazione anche in sviluppo locale senza un server SMTP.

### Configurazione SMTP

Vedi [07_configuration.md](./07_configuration.md) per la lista completa delle variabili d'ambiente SMTP.

