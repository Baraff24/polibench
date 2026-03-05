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
| Frontend — auth, routing, profilo utente           | ✅ Completato |
| Frontend — leaderboard, benchmark UI               | 🔄 In corso  |

## Come leggere questa documentazione

Per chi si avvicina al progetto per la prima volta, il percorso consigliato è:

1. `backend/00_overview.md` — capire il dominio e le entità
2. `backend/01_technologies.md` — capire le scelte tecnologiche
3. `backend/02_architecture.md` — capire la struttura del codice
4. `backend/03_data_models.md` — capire come i dati sono modellati
5. `backend/04_schemas.md` — capire il contratto API
6. `backend/05_authentication.md` — capire il sistema di autenticazione
7. `backend/06_routers.md` — capire gli endpoint HTTP disponibili
8. `backend/09_services.md` — capire la logica di business (service layer)
9. `backend/08_testing.md` — capire la strategia di test
10. `frontend/00_overview.md` + `frontend/02_architecture.md` — capire il frontend
