# Decisioni Architetturali (ADR)

Questo documento raccoglie le principali decisioni architetturali prese durante la progettazione di Polibench, con le
relative motivazioni e i trade-off accettati. L'obiettivo è rendere esplicito il ragionamento dietro ogni scelta, in
modo che chiunque legga il codice (o la tesi) capisca il "perché" e non solo il "come".

---

## ADR-01 — MongoDB invece di PostgreSQL

### Decisione

Il database scelto è **MongoDB** (documentale NoSQL), non un database relazionale come PostgreSQL.

### Motivazione

Il dominio di Polibench ha caratteristiche che si adattano bene al modello documentale:

1. **Schema flessibile per le metriche**: il set di metriche calcolate per un esperimento varia tra algoritmi e task.
   Un modello relazionale richiederebbe o una tabella molto sparsa (molte colonne NULL) o un design EAV
   (Entity-Attribute-Value) che è notoriamente difficile da interrogare. In MongoDB ogni `Metric` è un documento con
   esattamente i campi necessari.

2. **Sotto-documenti senza join**: entità come `CodeInfo`, `Artifacts`, `Splits` sono sotto-documenti annidati che
   vengono sempre letti insieme al documento padre. In un database relazionale sarebbero tabelle separate con join
   obbligatorie.

3. **Performance sulle query di leaderboard**: le query più critiche del sistema (`top-N per dataset/split/metrica`)
   beneficiano degli indici composti di MongoDB e della denormalizzazione controllata del modello `Metric`.
   Vedi [ADR-04](#adr-04--denormalizzazione-di-metric) per i dettagli.

4. **Integrazione con l'ecosistema**: Beanie (l'ODM scelto) è costruito su Pydantic, già usato da FastAPI per la
   validazione degli schemi. Questo crea un continuum coerente: un unico sistema di tipi Python per DB, business logic
   e API.

### Trade-off accettati

- **Niente transazioni ACID multi-document**: MongoDB supporta transazioni multi-documento dalla versione 4.0, ma
  Beanie non le usa per default. In Polibench le operazioni critiche (creazione experiment + inserimento metriche) sono
  sequenziali e non richiedono atomicità cross-collection nel caso base.
- **Niente JOIN dichiarative**: le relazioni tra entità (es. `Experiment → Dataset`) vengono risolte manualmente nel
  service layer. Questo è gestibile con il pattern di risoluzione UUID→ObjectId centralizzato nei service.
- **Meno vincoli di integrità referenziale**: MongoDB non impone foreign key. La coerenza referenziale è garantita
  dalla logica applicativa (i service sollevano 404 se un documento referenziato non esiste).

---

## ADR-02 — UUID come identificatori pubblici (UUID-first API)

### Decisione

L'API espone **UUID (versione 4)** come identificatori pubblici per tutte le entità. Gli `ObjectId` di MongoDB non
vengono mai esposti al client.

### Motivazione

1. **Stabilità del contratto API**: l'`_id` di MongoDB è un dettaglio implementativo del database. Se il database
   cambiasse (es. migrazione a PostgreSQL con UUID o interi auto-increment), i client non dovrebbero cambiare nulla.

2. **Non esporre informazioni strutturali**: un `ObjectId` di MongoDB codifica al suo interno il timestamp di creazione
   e l'ID del server. Esporlo non è una vulnerabilità grave, ma è un leak di informazioni implementative non necessario.

3. **Coerenza con benchmark aperti**: sistemi simili (BARS, OpenBenchmark) usano identificatori opachi e stabili per
   i propri endpoint. Un UUID è la scelta standard per API pubbliche e CLI.

4. **Facilità d'uso per terze parti e script**: un ricercatore che integra Polibench tramite CLI o script Python
   ragiona in termini di `dataset_uuid`, non di `_id` Mongo. L'UUID è leggibile, copiabile e stabile nel tempo.

### Come funziona nella pratica

Ogni Document Beanie ha **due identificatori**:

```python
# _id: assegnato automaticamente da MongoDB (ObjectId)
uuid: Annotated[UUID, Field(default_factory=uuid4), Indexed(unique=True)]
```

| Contesto               | Identificatore usato | Note                                               |
|------------------------|----------------------|----------------------------------------------------|
| Path params (URL)      | UUID                 | `GET /datasets/{dataset_uuid}`                     |
| Body input (Create)    | UUID                 | `dataset_uuid: UUID`, mai `PydanticObjectId`       |
| Response output        | UUID                 | campo `uuid` nell'output, niente `_id`             |
| Relazioni interne DB   | ObjectId             | `dataset_id: PydanticObjectId` nel Document Beanie |
| Query e indici MongoDB | ObjectId             | più efficiente per lookup interno                  |

Il **router** è il solo punto dove avviene la traduzione: riceve UUID dal client, chiama il service per ottenere il
Document (con il suo `_id`), e usa l'`_id` per le operazioni interne.

### Trade-off accettati

- **Doppio indice per entità**: ogni collezione ha un indice su `_id` (automatico MongoDB) e uno su `uuid` (dichiarato
  con `Indexed(unique=True)`). Il costo in termini di spazio e tempo di scrittura è trascurabile per i volumi tipici
  di un sistema di benchmarking accademico.
- **Un round-trip in più per risoluzione**: leggere un Dataset per UUID invece che per ObjectId richiede una query su
  un indice secondario invece che sull'indice primario. In pratica la differenza è irrilevante con volumi normali.

---

## ADR-03 — FastAPI + Beanie invece di Django ORM

### Decisione

Il framework web è **FastAPI** con **Beanie** come ODM, non Django con il suo ORM.

### Motivazione

1. **Async nativo**: FastAPI è costruito su Starlette e asyncio. Beanie è costruito su Motor (driver MongoDB asincrono).
   L'intera stack è non-bloccante, il che è importante per un sistema che potrebbe gestire submission concorrenti.

2. **Pydantic come sistema di tipi unificato**: FastAPI usa Pydantic per la validazione dei body HTTP; Beanie usa
   Pydantic per i Document del database. Questo significa un unico sistema di tipi per tutto il backend, con
   validazione automatica sia in input che in output.

3. **Documentazione OpenAPI automatica**: FastAPI genera Swagger UI e ReDoc senza configurazione aggiuntiva.
   Per un sistema di benchmark che vuole essere consumato da terze parti, avere documentazione interattiva e sempre
   aggiornata è un vantaggio concreto.

4. **Leggerezza e modularità**: Django include ORM, admin, form, template engine. Polibench non usa nessuno di questi.
   FastAPI è un micro-framework: si usa solo ciò che serve.

5. **Django + MongoDB**: l'ORM Django è progettato per database relazionali. Usare Django con MongoDB richiederebbe
   librerie di terze parti (Djongo, MongoEngine) con un supporto meno maturo rispetto a Beanie.

### Trade-off accettati

- **Admin interface**: Django offre una admin UI pronta. Con FastAPI va costruita o si usa un tool esterno.
- **Maturità dell'ecosistema**: Django ha un ecosistema più maturo per autenticazione social, permessi granulari,
  migrazioni. Polibench gestisce queste esigenze manualmente o con librerie specializzate (es. `fastapi-sso` per
  Google OAuth2).

---

## ADR-04 — Denormalizzazione di `Metric`

### Decisione

Il modello `Metric` contiene campi **denormalizzati** (`dataset_id`, `model_id`, `submitted_by_user_id`, `team_id`)
che duplicano informazioni già presenti nel documento `Experiment` collegato.

### Motivazione

La query di leaderboard è la più frequente e critica del sistema:

> *"Dammi i top-N esperimenti per questo dataset, questo split e questa metrica, ordinati per value."*

Senza denormalizzazione, questa query richiederebbe:

```
Metric → $lookup → Experiment → filtra per dataset_id
```

In MongoDB, `$lookup` è equivalente a una join e ha un costo significativo su collezioni grandi. Con la
denormalizzazione, la stessa query diventa:

```python
Metric.find(
    Metric.dataset_id == dataset_id,
    Metric.metric == metric,
    Metric.split == split,
).sort([("value", pymongo.DESCENDING)]).limit(top_n)
```

Questa query usa l'indice composto `{dataset_id, metric, split, value: -1}` e non richiede nessun join.

### Indici definiti sulla collezione `metrics`

| Indice                                            | Usato da                          |
|---------------------------------------------------|-----------------------------------|
| `{dataset_id, split, metric, value: -1}`          | query leaderboard principale      |
| `{dataset_id, metric, split}`                     | filtri leaderboard alternativi    |
| `{experiment_id}`                                 | `GET /experiments/{uuid}/metrics` |
| `{team_id, dataset_id, split, metric, value: -1}` | leaderboard filtrato per team     |
| `{submitted_by_user_id, dataset_id}`              | metriche per utente               |

### Trade-off accettati

- **Ridondanza dei dati**: `dataset_id` e `model_id` sono scritti sia in `Experiment` che in ogni `Metric`
  dell'experiment. Se un Experiment venisse modificato (raro), le Metric non si aggiornerebbero automaticamente.
  Per il modello di Polibench (le submission sono immutabili) questo non è un problema pratico.
- **Maggiore responsabilità al momento dell'inserimento**: il service `metrics.py` deve copiare i campi
  correttamente dall'Experiment nel Metric. Un bug qui causerebbe dati inconsistenti. Questa logica è centralizzata
  in `services/metrics.py` e coperta dai test.

---

## ADR-05 — Service layer separato dai router

### Decisione

Tutta la logica di business (risoluzione UUID→ObjectId, denormalizzazione, query, aggregazioni) vive nel **service
layer** (`app/services/`), non nei router.

### Motivazione

1. **Testabilità**: i service possono essere testati direttamente, senza HTTP. I test del service layer non richiedono
   client HTTP né parsing di response body.

2. **Riusabilità**: la stessa funzione `get_dataset_by_uuid` è usata da `services/datasets.py`,
   `services/experiments.py` e `services/leaderboard.py`. Se vivesse nel router, sarebbe duplicata.

3. **Chiarezza della responsabilità**: un router non dovrebbe sapere come risolvere un UUID in un ObjectId, né come
   costruire una risposta denormalizzata. Queste sono responsabilità del service.

4. **Manutenibilità**: se la logica di creazione di un Experiment cambia (es. aggiunta di un campo obbligatorio),
   si modifica solo `services/experiments.py`, non il router.

### Struttura del flusso

```
HTTP Request
    │
    ▼
Router (routers/)
    │  valida input, estrae JWT, chiama service
    ▼
Service (services/)
    │  risolve UUID, crea/legge Document, costruisce risposta
    ▼
Beanie Document (models/)
    │  query MongoDB
    ▼
MongoDB
```

---

## ADR-06 — `hyperparams` in `MLModel`, non in `Experiment`

### Decisione

Il campo `hyperparams` è definito nel modello `MLModel`, non in `Experiment`. In `Experiment` è presente invece
`training_config` per la configurazione run-specific.

### Motivazione

La distinzione è semantica:

- **`MLModel.hyperparams`**: parametri canonici dell'algoritmo come riportati nel paper di riferimento
  (es. `{"factors": 64, "lr": 0.01, "regularization": 0.001}`). Rappresentano la "configurazione di default" o
  "raccomandata" dell'algoritmo, indipendente da una run specifica.

- **`Experiment.training_config`**: parametri specifici di una singola run (es. seed, scheduler, learning rate
  modificato). Possono variare tra run dello stesso algoritmo sullo stesso dataset.

Questa separazione riflette la distinzione tra *algoritmo* (cosa è LightGCN per definizione) e *run* (come è stato
eseguito LightGCN in questo esperimento specifico).

---

## ADR-07 — `Dataset` catalografico + `DatasetVersion` come unità operativa

### Decisione

Il dominio viene evoluto verso un modello versionato:

- `Dataset` diventa entità catalografica (nome, task, ownership, visibilità)
- `DatasetVersion` diventa il nodo operativo per YAML dataset/version/characteristics e provenance
- `Pipeline` diventa entità autonoma collegata a `DatasetVersion`
- `Experiment` referenzia `pipeline_id` (con `dataset_version_id` denormalizzato)
- le metriche vengono separate in:
  - `Dataset characteristics` (strutturali, per versione dataset)
  - `Experiment performance metrics` (leaderboard)
- la submission metriche passa da batch diretto a upload CSV + job asincrono (`MetricImportJob`)

### Motivazione

La richiesta accademica attuale non è più un benchmark "piatto" dataset/modello, ma un benchmark con:

1. provenance (`sources` e `resources`)
2. pipeline esplicita, separata dalla versione e referenziabile
3. caratteristiche dataset distinte dalle metriche prestazionali del modello
4. tracciamento del processo di import metriche asincrono

Mantenere il modello precedente (`Dataset.version`, `Experiment.dataset_id`, upload metriche diretto) crea ambiguità
semantica e rende fragile l'evoluzione.

### Trade-off accettati

- **Maggiore complessità di dominio**: più collezioni e più endpoint.
- **Migrazione dati necessaria**: backfill da dataset legacy a dataset versionati.
- **Compatibilità transitoria**: per ridurre impatto frontend servono endpoint legacy temporanei.

### Impatto architetturale

L'architettura applicativa non cambia:

- FastAPI + Beanie
- UUID-first API
- router sottili + service layer
- denormalizzazione controllata per query leaderboard

Cambia il **core del dominio**, non la struttura tecnica del backend.

---

## Riepilogo decisioni

| ADR    | Decisione                         | Alternativa scartata             |
|--------|-----------------------------------|----------------------------------|
| ADR-01 | MongoDB come database             | PostgreSQL                       |
| ADR-02 | UUID come identificatori pubblici | Esporre ObjectId direttamente    |
| ADR-03 | FastAPI + Beanie                  | Django + Django ORM              |
| ADR-04 | Denormalizzazione di `Metric`     | Join via `$lookup`               |
| ADR-05 | Service layer separato            | Logica nei router                |
| ADR-06 | `hyperparams` in `MLModel`        | `hyperparams` solo in Experiment |
| ADR-07 | Dominio pipeline-first (`Dataset -> DatasetVersion -> Pipeline -> Experiment`) | Dataset con versione "piatta"  |
