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
│   ├── 06_routers.md               ← endpoint HTTP implementati e da fare
│   ├── 07_configuration.md         ← variabili d'ambiente e configurazione
│   └── 08_testing.md               ← strategia di test e smoke test DB
└── frontend/
    ├── 00_overview.md              ← panoramica generale del frontend
    ├── 01_technologies.md          ← stack tecnologico frontend
    └── 02_architecture.md          ← architettura React, routing, contexts
```

## Stato del progetto (marzo 2026)

| Area                                               | Stato              |
|----------------------------------------------------|--------------------|
| Modelli dati (backend)                             | ✅ Completato       |
| Schemi API (backend)                               | ✅ Completato       |
| Autenticazione JWT + Google SSO                    | ✅ Completato       |
| Router Users e Login                               | ✅ Completato       |
| Smoke test database (in-memory)                    | ✅ Completato       |
| Router Datasets / MLModels / Experiments / Metrics | 🔄 Da implementare |
| Frontend — auth, routing, profilo utente           | ✅ Completato       |
| Frontend — leaderboard, benchmark UI               | 🔄 Da implementare |

## Come leggere questa documentazione

Per chi si avvicina al progetto per la prima volta, il percorso consigliato è:

1. `backend/00_overview.md` — capire il dominio e le entità
2. `backend/01_technologies.md` — capire le scelte tecnologiche
3. `backend/02_architecture.md` — capire la struttura del codice
4. `backend/03_data_models.md` — capire come i dati sono modellati
5. `backend/04_schemas.md` — capire il contratto API
6. `backend/05_authentication.md` — capire il sistema di autenticazione
7. `frontend/00_overview.md` + `frontend/02_architecture.md` — capire il frontend
