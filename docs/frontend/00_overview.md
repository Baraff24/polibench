# Frontend — Panoramica Generale

## Cos'è il frontend di Polibench

Il frontend è un'applicazione **Single Page Application (SPA)** che fornisce l'interfaccia utente per la piattaforma
Polibench. Comunica esclusivamente con il backend tramite la REST API esposta su `/api/v1`.

Al momento dello sviluppo (marzo 2026), il frontend implementa:

- autenticazione con email/password e Google SSO
- registrazione di nuovi utenti
- visualizzazione e modifica del profilo utente
- lista degli utenti (solo per admin)
- pagina home con presentazione dello stack tecnologico
- lista e dettaglio dei dataset
- lista e dettaglio dei modelli ML
- dettaglio degli experiment con metriche per split
- leaderboard con filtri interattivi (dataset, metric, split, top N)

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
    │       └── StatCard.tsx
    ├── contexts/            ← React Context (stato globale)
    │   ├── auth.tsx
    │   └── snackbar.tsx
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
    │   └── experiment-detail.tsx
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

| Path                  | Componente         | Accesso     |
|-----------------------|--------------------|-------------|
| `/`                   | `Home`             | Pubblico    |
| `/login`              | `Login`            | Guest       |
| `/register`           | `Register`         | Guest       |
| `/sso-login-callback` | `SSOLogin`         | Sistema     |
| `/profile`            | `Profile`          | Autenticato |
| `/leaderboard`        | `Leaderboard`      | Pubblico    |
| `/datasets`           | `Datasets`         | Pubblico    |
| `/datasets/:uuid`     | `DatasetDetail`    | Pubblico    |
| `/models`             | `Models`           | Pubblico    |
| `/models/:uuid`       | `ModelDetail`      | Pubblico    |
| `/experiments/:uuid`  | `ExperimentDetail` | Autenticato |
| `/users`              | `Users`            | Admin       |

---

## Documentazione correlata

- `01_technologies.md` — stack tecnologico e motivazioni
- `02_architecture.md` — architettura a strati, pattern e flussi
- `03_scss.md` — sistema di stile SCSS/BEM, variabili, mixin, componenti
