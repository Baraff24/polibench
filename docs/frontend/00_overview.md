# Frontend — Panoramica Generale

## Cos'è il frontend di Polibench

Il frontend è un'applicazione **Single Page Application (SPA)** che fornisce l'interfaccia utente per la piattaforma
Polibench. Comunica esclusivamente con il backend tramite la REST API esposta su `/api/v1`.

Al momento dello sviluppo (marzo 2026), il frontend implementa:

- autenticazione con email/password e Google SSO
- registrazione di nuovi utenti con verifica email
- visualizzazione e modifica del profilo utente
- lista degli utenti (solo per admin)
- pagina home con presentazione della piattaforma
- lista e dettaglio dei dataset, con form di creazione
- lista e dettaglio dei modelli ML, con form di registrazione
- submission di experiment con selezione dataset/model
- submission batch di metriche con form tabellare
- dettaglio degli experiment con metriche per split
- leaderboard con filtri interattivi (dataset, metric, split, top N, chart mode), ordinamento per colonna (asc/desc) e grafico adattivo (linee AUC/Logloss per CTR, barre o linee per altri task in base alla modalità)
- route protette con guard `RequireAuth`
- titolo scheda dinamico per route

---

## Struttura delle cartelle

```
frontend/
├── package.json             ← dipendenze e script
├── vite.config.ts           ← configurazione Vite e Vitest
├── tsconfig.json            ← configurazione TypeScript
├── index.html               ← entry point HTML
├── nginx.conf               ← configurazione Nginx (produzione)
├── Dockerfile               ← immagine di produzione
├── Dockerfile.development   ← immagine di sviluppo
└── src/
    ├── main.tsx             ← punto di ingresso React
    ├── router.tsx           ← definizione delle route
    ├── axios.ts             ← configurazione client HTTP + interceptor JWT
    ├── error-page.tsx       ← pagina di errore globale (404, crash)
    ├── fallback.tsx         ← componente di loading (HydrateFallback)
    ├── components/          ← componenti riutilizzabili
    │   ├── LoginForm.tsx
    │   ├── RegisterForm.tsx
    │   ├── TopMenuBar.tsx
    │   ├── UserProfile.tsx
    │   ├── index.ts         ← barrel file
    │   └── common/          ← componenti UI generici
    │       ├── Badge.tsx
    │       ├── DataTable.tsx
    │       ├── EmptyState.tsx
    │       ├── LoadingSpinner.tsx
    │       ├── PageHeader.tsx
    │       ├── RequireAuth.tsx
    │       └── StatCard.tsx
    ├── contexts/            ← React Context (stato globale)
    │   ├── auth.tsx
    │   └── snackbar.tsx
    ├── hooks/               ← custom React hooks
    │   └── useDocumentTitle.ts
    ├── models/              ← interfacce TypeScript
    │   ├── user.ts
    │   ├── dataset.ts
    │   ├── ml-model.ts
    │   ├── experiment.ts
    │   ├── metric.ts
    │   ├── leaderboard.ts
    │   └── index.ts         ← barrel file
    ├── routes/              ← componenti pagina
    │   ├── home.tsx
    │   ├── login.tsx
    │   ├── profile.tsx
    │   ├── register.tsx
    │   ├── root.tsx
    │   ├── sso.login.tsx
    │   ├── users.tsx
    │   ├── leaderboard.tsx
    │   ├── datasets.tsx
    │   ├── dataset-detail.tsx
    │   ├── models.tsx
    │   ├── model-detail.tsx
    │   ├── experiment-detail.tsx
    │   ├── verify-email.tsx
    │   ├── create-dataset.tsx
    │   ├── create-model.tsx
    │   ├── submit-experiment.tsx
    │   └── submit-metrics.tsx
    ├── services/            ← chiamate HTTP al backend
    │   ├── auth.service.ts
    │   ├── user.service.ts
    │   ├── dataset.service.ts
    │   ├── ml-model.service.ts
    │   ├── experiment.service.ts
    │   ├── leaderboard.service.ts
    │   └── index.ts         ← barrel file
    └── styles/              ← tutto il CSS (SCSS + BEM)
        ├── main.scss        ← entry point
        ├── abstracts/       ← variabili, mixin
        ├── base/            ← reset, tipografia
        ├── components/      ← btn, form, card, badge, table…
        ├── layout/          ← sidebar, topbar, layout shell
        └── pages/           ← stili specifici per pagina
```

---

## Route disponibili

| Path                             | Componente         | Accesso     | Guard                   |
|----------------------------------|--------------------|-------------|-------------------------|
| `/`                              | `Home`             | Pubblico    | —                       |
| `/login`                         | `Login`            | Guest       | —                       |
| `/register`                      | `Register`         | Guest       | —                       |
| `/verify-email`                  | `VerifyEmail`      | Pubblico    | —                       |
| `/sso-login-callback`            | `SSOLogin`         | Sistema     | —                       |
| `/profile`                       | `Profile`          | Autenticato | `RequireAuth`           |
| `/leaderboard`                   | `Leaderboard`      | Pubblico    | —                       |
| `/datasets`                      | `Datasets`         | Pubblico    | —                       |
| `/datasets/new`                  | `CreateDataset`    | Autenticato | `RequireAuth`           |
| `/datasets/:uuid`                | `DatasetDetail`    | Pubblico    | —                       |
| `/dataset-versions/:uuid`        | `DatasetVersionDetail` | Pubblico | —                       |
| `/models`                        | `Models`           | Pubblico    | —                       |
| `/models/new`                    | `CreateModel`      | Autenticato | `RequireAuth`           |
| `/models/:uuid`                  | `ModelDetail`      | Pubblico    | —                       |
| `/experiments/new`               | `SubmitExperiment` | Autenticato | `RequireAuth`           |
| `/experiments/:uuid`             | `ExperimentDetail` | Autenticato | `RequireAuth`           |
| `/experiments/:uuid/metrics/new` | `SubmitMetrics`    | Autenticato | `RequireAuth`           |
| `/users`                         | `Users`            | Admin       | `RequireAuth adminOnly` |

Nota flusso DatasetVersion:

- `CreateDataset` crea solo l'entità catalografica `Dataset`.
- La `DatasetVersion` si crea dalla pagina `/datasets/:uuid` tramite form YAML
  (dataset/version/pipeline/characteristics) con preview parse prima del submit.

---

## Documentazione correlata

- `01_technologies.md` — stack tecnologico e motivazioni
- `02_architecture.md` — architettura a strati, pattern e flussi
- `03_scss.md` — sistema di stile SCSS/BEM, variabili, mixin, componenti
