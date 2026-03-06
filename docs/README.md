# Documentazione Polibench

Questa cartella contiene la documentazione tecnica completa del progetto **Polibench**, una piattaforma per la
valutazione comparativa di modelli di raccomandazione.

## Struttura

```
docs/
├── README.md                       ← questo file (indice generale)
├── backend/
│   ├── 00_overview.md              ← panoramica generale e dominio
│   ├── 01_technologies.md          ← stack tecnologico e motivazioni
│   ├── 02_architecture.md          ← architettura applicativa e cartelle
│   ├── 03_data_models.md           ← modelli dati (Document MongoDB/Beanie)
│   ├── 04_schemas.md               ← schemi API (contratto HTTP/Pydantic)
│   ├── 05_authentication.md        ← autenticazione JWT e Google SSO
│   ├── 06_routers.md               ← tutti gli endpoint HTTP implementati
│   ├── 07_configuration.md         ← variabili d'ambiente e configurazione
│   ├── 08_testing.md               ← strategia di test, smoke test DB e test router
│   ├── 09_services.md              ← service layer (logica di business)
│   ├── 10_decisions.md             ← decisioni architetturali e trade-off (ADR)
│   ├── 11_errors_and_api_conventions.md ← codici HTTP, formato errori, convenzioni
│   ├── 12_indexes_and_performance.md    ← query critiche, indici MongoDB, performance
│   ├── 13_deployment.md            ← ambienti, Docker Compose, avvio, produzione
│   ├── 14_future_work.md           ← limiti attuali e sviluppi futuri
│   └── domain_model.puml           ← diagramma UML entità (DB layer)
└── frontend/
    ├── 00_overview.md              ← panoramica generale del frontend
    ├── 01_technologies.md          ← stack tecnologico frontend
    └── 02_architecture.md          ← architettura React, routing, contexts
```

## Stato del progetto (marzo 2026)

| Area                                               | Stato        |
|----------------------------------------------------|--------------|
| Modelli dati (backend)                             | ✅ Completato |
| Schemi API (backend)                               | ✅ Completato |
| Autenticazione JWT + Google SSO                    | ✅ Completato |
| Router Users e Login                               | ✅ Completato |
| Router Datasets / MLModels / Experiments / Metrics | ✅ Completato |
| Router Leaderboard                                 | ✅ Completato |
| Service layer (datasets, experiments, metrics, lb) | ✅ Completato |
| Smoke test database (in-memory)                    | ✅ Completato |
| Test API router end-to-end (in-memory)             | ✅ Completato |
| Decisioni architetturali (ADR)                     | ✅ Completato |
| Convenzioni HTTP ed error handling                 | ✅ Completato |
| Indici, query critiche e performance               | ✅ Completato |
| Deployment e ambienti                              | ✅ Completato |
| Limiti attuali e sviluppi futuri                   | ✅ Completato |
| Frontend — auth, routing, profilo utente           | ✅ Completato |
| Frontend — leaderboard, benchmark UI               | 🔄 In corso  |

## Come leggere questa documentazione

Per chi si avvicina al progetto per la prima volta, il percorso consigliato è:

1. `backend/00_overview.md` — capire il dominio e le entità
2. `backend/01_technologies.md` — capire le scelte tecnologiche
3. `backend/10_decisions.md` — capire il perché di ogni scelta (ADR)
4. `backend/02_architecture.md` — capire la struttura del codice
5. `backend/03_data_models.md` — capire come i dati sono modellati
6. `backend/12_indexes_and_performance.md` — capire le query critiche e gli indici
7. `backend/04_schemas.md` — capire il contratto API
8. `backend/11_errors_and_api_conventions.md` — capire codici HTTP e formato errori
9. `backend/05_authentication.md` — capire il sistema di autenticazione
10. `backend/06_routers.md` — capire gli endpoint HTTP disponibili
11. `backend/09_services.md` — capire la logica di business (service layer)
12. `backend/08_testing.md` — capire la strategia di test
13. `backend/13_deployment.md` — capire come avviare e distribuire il sistema
14. `backend/14_future_work.md` — limiti attuali e sviluppi futuri
15. `frontend/00_overview.md` + `frontend/02_architecture.md` — capire il frontend
