# Backend — Panoramica Generale

Polibench e una piattaforma web per benchmark comparativo di recommender systems,
allineata al modello DataRec:

- `Dataset` catalografico
- `DatasetVersion` operativa
- `Pipeline` separata dalla versione
- `Experiment` agganciato a pipeline
- `ExperimentMetric` per performance
- `MetricImportJob` per import CSV async

---

## Obiettivo

Fornire un backend che renda tracciabili e confrontabili i risultati sperimentali, separando in modo netto:

- dataset characteristics (strutturali del dataset)
- experiment performance metrics (NDCG, Recall, RMSE, ...)

---

## Architettura

```text
HTTP (FastAPI routers)
  -> Schemi API (Pydantic)
    -> Service layer (business logic)
      -> Modelli dati (Beanie)
        -> MongoDB (Motor)
```

Router sottili, logica nei service.

---

## Entita principali

| Entita | Descrizione |
|--------|-------------|
| `User` | utente con ruoli (`admin`, `researcher`, `viewer`) |
| `Team` | namespace di ricerca |
| `Dataset` | catalogo logico |
| `DatasetVersion` | versione reale con YAML dataset/version/characteristics |
| `Pipeline` | configurazione eseguibile (YAML + blocks) su una versione |
| `Source` / `Resource` | provenance parse dal version YAML |
| `MLModel` | algoritmo registrato |
| `Experiment` | run su pipeline + modello |
| `ExperimentMetric` | metriche performance denormalizzate per leaderboard |
| `MetricImportJob` | job async CSV (`uploaded/processing/completed/failed`) |

Relazione core:

`Dataset -> DatasetVersion -> Pipeline -> Experiment -> ExperimentMetric`

---

## Entry point

`app/main.py`:

1. apre connessione MongoDB
2. inizializza Beanie con `DOCUMENT_MODELS`
3. crea superuser iniziale (se assente)
4. configura CORS
5. monta `api_router` su `/api/v1`
