# Indici, Query Critiche e Performance

Questo documento descrive le query più importanti del sistema, gli indici MongoDB che le supportano e le decisioni
di progettazione che impattano le performance. È complementare a [03_data_models.md](./03_data_models.md) (che descrive
la struttura dei dati) e a [10_decisions.md](./10_decisions.md) (che motiva la denormalizzazione).

---

## Query critiche del sistema

### Query 1 — Leaderboard (la più critica)

**Dove**: `services/leaderboard.py` → `GET /api/v1/leaderboard`

**Descrizione**: recupera i top-N risultati per un dataset, uno split e una metrica specifici, ordinati per valore.
È la query che viene eseguita ogni volta che un utente apre la pagina di un dataset.

**Query Beanie**:

```python
await Metric.find(
    Metric.dataset_id == dataset_object_id,
    Metric.metric == "ndcg@10",
    Metric.split == Split.TEST,
).sort([("value", pymongo.DESCENDING)]).limit(10).to_list()
```

**Indice usato**:

```
{ dataset_id: 1, metric: 1, split: 1, value: -1 }
```

**Perché questo indice è efficiente**: i tre campi di filtro (`dataset_id`, `metric`, `split`) riducono il set di
documenti al minimo prima che MongoDB applichi l'ordinamento. L'ordinamento `value: -1` è incluso nell'indice stesso,
quindi MongoDB non deve fare un sort in memoria: scorre l'indice al contrario e prende i primi N.

**Senza denormalizzazione (scenario alternativo)**:

```
Metric.find(Metric.experiment_id == ...) + $lookup su Experiment per filtrare per dataset_id
```

Questa query richiederebbe un `$lookup` (join) su tutti i Metric → Experiment, non indicizzabile nello stesso modo.
Con la denormalizzazione, `dataset_id` è già nel documento `Metric` e l'indice è sfruttabile direttamente.

---

### Query 2 — Metriche per Experiment

**Dove**: `services/metrics.py` → `GET /api/v1/experiments/{uuid}/metrics`

**Descrizione**: recupera tutte le metriche associate a un Experiment specifico. Usata nella pagina di dettaglio run.

**Query Beanie**:

```python
await Metric.find(Metric.experiment_id == experiment_object_id).to_list()
```

**Indice usato**:

```
{ experiment_id: 1 }
```

**Note**: questa query restituisce in genere un numero piccolo di documenti (O(10) metriche per experiment), quindi
l'overhead è basso. L'indice è comunque utile perché evita una collection scan su una collezione potenzialmente grande.

---

### Query 3 — Risoluzione UUID → Document

**Dove**: tutti i service (pattern `get_XXX_by_uuid`)

**Descrizione**: dato un UUID pubblico, trova il documento corrispondente. Usata in ogni operazione di creazione o
lettura che riceve UUID dal client.

**Query Beanie**:

```python
await Dataset.find_one(Dataset.uuid == dataset_uuid)
```

**Indice usato**:

```
{ uuid: 1 }  (unique)
```

Ogni entità ha questo indice dichiarato con `Indexed(unique=True)`. Garantisce che:

- la risoluzione UUID→Document sia O(log N) (indice B-tree)
- non possano esistere duplicati UUID (vincolo di integrità)

---

### Query 4 — Batch fetch per costruzione leaderboard

**Dove**: `services/leaderboard.py`, dopo aver ottenuto i Metric

**Descrizione**: dopo aver recuperato i top-N Metric dalla query di leaderboard, il service deve risolvere
`model_id → MLModel` e `experiment_id → Experiment` per costruire le `LeaderboardEntry`. Invece di farlo in loop
(N+1 query), usa un batch fetch:

```python
# raccogli tutti gli ObjectId distinti
model_ids = {m.model_id for m in metrics}
experiment_ids = {m.experiment_id for m in metrics}

# una sola query per tutti i modelli
models = await MLModel.find({"_id": {"$in": list(model_ids)}}).to_list()

# una sola query per tutti gli experiment
experiments = await Experiment.find({"_id": {"$in": list(experiment_ids)}}).to_list()
```

**Indice usato**: `_id` (indice primario di MongoDB, sempre presente)

**Perché è importante**: senza batch fetch, per 10 risultati in leaderboard si avrebbero 20 query aggiuntive
(10 per MLModel + 10 per Experiment). Con il batch fetch sono 2 query totali, indipendentemente da N.

---

### Query 5 — Lista Dataset / MLModel

**Dove**: `services/datasets.py` → `GET /api/v1/datasets`, `GET /api/v1/ml-models`

**Descrizione**: listing paginato di tutte le entità del catalogo.

**Query Beanie**:

```python
await Dataset.find_all().skip(offset).limit(limit).to_list()
```

**Indice usato**: scansione naturale (nessun filtro). Accettabile perché:

- il numero di dataset e modelli è tipicamente piccolo (O(10)–O(100)) in un sistema di benchmark accademico
- la paginazione limita comunque i documenti restituiti

Se il volume crescesse, si potrebbe aggiungere un indice su `created_at` per ordinamento cronologico stabile.

---

## Indici dichiarati per collezione

### Collezione `users`

| Campo   | Tipo   | Nota                    |
|---------|--------|-------------------------|
| `uuid`  | unique | Identificatore pubblico |
| `email` | unique | Login e deduplicazione  |

### Collezione `datasets`

| Campo                | Tipo     | Nota                    |
|----------------------|----------|-------------------------|
| `uuid`               | unique   | Identificatore pubblico |
| `team_id`            | semplice | Filtro per team         |
| `created_by_user_id` | semplice | Filtro per autore       |

### Collezione `models` (MLModel)

| Campo                | Tipo     | Nota                    |
|----------------------|----------|-------------------------|
| `uuid`               | unique   | Identificatore pubblico |
| `name`               | unique   | Nome univoco algoritmo  |
| `created_by_user_id` | semplice | Filtro per autore       |

### Collezione `experiments`

| Campo                  | Tipo     | Nota                    |
|------------------------|----------|-------------------------|
| `uuid`                 | unique   | Identificatore pubblico |
| `dataset_id`           | semplice | Filtro per dataset      |
| `model_id`             | semplice | Filtro per modello      |
| `submitted_by_user_id` | semplice | Filtro per autore       |
| `team_id`              | semplice | Filtro per team         |

> **Nota**: un indice composto `{dataset_id, model_id, created_at: -1}` potrebbe essere utile per trovare
> tutti gli experiment di una coppia (dataset, model). Non è dichiarato nell'implementazione corrente;
> può essere aggiunto se la query diventa frequente.

### Collezione `metrics` (la più importante)

| Campo/Indice                                                  | Tipo     | Query supportata               |
|---------------------------------------------------------------|----------|--------------------------------|
| `uuid`                                                        | unique   | Risoluzione UUID               |
| `experiment_id`                                               | semplice | Metriche per experiment        |
| `dataset_id`                                                  | semplice | —                              |
| `model_id`                                                    | semplice | —                              |
| `submitted_by_user_id`                                        | semplice | Metriche per utente            |
| `team_id`                                                     | semplice | Metriche per team              |
| `metric`                                                      | semplice | Filtro per nome metrica        |
| `{dataset_id, split, metric, value: -1}`                      | composto | **Leaderboard principale**     |
| `{dataset_id, metric, split}`                                 | composto | Filtri leaderboard alternativi |
| `{team_id, dataset_id, split, metric, value: -1}`             | composto | Leaderboard per team           |
| `{submitted_by_user_id, dataset_id, split, metric, value:-1}` | composto | Leaderboard per utente         |

---

## Costo della denormalizzazione

La denormalizzazione di `Metric` introduce un costo di consistenza che vale la pena esplicitare:

| Aspetto             | Costo                                                                    |
|---------------------|--------------------------------------------------------------------------|
| Spazio disco        | `dataset_id` + `model_id` duplicati in ogni Metric (≈24 byte per Metric) |
| Scrittura           | Al momento dell'inserimento batch, il service deve copiare i campi       |
| Consistenza         | Se un Experiment venisse modificato, le Metric non si aggiornerebbero    |
| Manutenzione indici | Ogni indice composto su `Metric` rallenta leggermente le scritture       |

**Perché è accettabile**: in Polibench le submission sono **immutabili** dopo la creazione. Un Experiment non viene
modificato dopo che le sue metriche sono state sottomesse. Quindi il rischio di inconsistenza per modifica è teorico,
non pratico.

---

## Possibili colli di bottiglia futuri

### 1. Leaderboard senza caching

La query di leaderboard viene eseguita ogni volta che un utente apre la pagina. Con un numero elevato di metriche
per un dataset molto popolare, anche con gli indici ottimali ci sarà un costo non nullo.

**Soluzione futura**: aggiungere un layer di caching (es. Redis) che materializza la leaderboard per i dataset più
acceduti e la invalida solo quando arrivano nuove submission. Non implementato nell'MVP corrente.

### 2. Batch di metriche molto grandi

`POST /experiments/{uuid}/metrics` accetta un intero batch in un singolo request. Se un esperimento produce
centinaia di metriche (es. @k per k in {1,5,10,20,50,100} × N split × M metriche), il payload può diventare grande.

**Soluzione futura**: aggiungere un limite massimo al batch (es. 200 metriche per request) o supportare upload
asincrono con job queue.

### 3. Indici composti non coperti

La query di leaderboard filtrata per team (`{team_id, dataset_id, split, metric, value: -1}`) è dichiarata ma non
ancora usata nei router correnti. Se aggiunta, sarà già supportata dall'indice.

### 4. Nessun TTL o archivio

Non esiste un meccanismo di archivio o TTL (Time-To-Live) per le metriche vecchie. In un sistema di benchmark
a lungo termine, le collezioni crescono indefinitamente.

