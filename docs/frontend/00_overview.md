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

Le funzionalità di benchmark (leaderboard, dettaglio esperimenti, sottomissione run) sono in fase di sviluppo.

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
    ├── axios.ts             ← configurazione client HTTP
    ├── theme.tsx            ← tema Material UI
    ├── error-page.tsx       ← pagina di errore globale
    ├── fallback.tsx         ← componente di loading
    ├── components/          ← componenti riutilizzabili
    │   ├── LoginForm.tsx
    │   ├── RegisterForm.tsx
    │   ├── TopMenuBar.tsx
    │   └── UserProfile.tsx
    ├── contexts/            ← React Context (stato globale)
    │   ├── auth.tsx
    │   └── snackbar.tsx
    ├── models/              ← interfacce TypeScript
    │   └── user.ts
    ├── routes/              ← componenti pagina
    │   ├── home.tsx
    │   ├── login.tsx
    │   ├── profile.tsx
    │   ├── register.tsx
    │   ├── root.tsx
    │   ├── sso.login.tsx
    │   └── users.tsx
    └── services/            ← chiamate HTTP al backend
        ├── auth.service.ts
        └── user.service.ts
```

