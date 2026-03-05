# Stack Tecnologico — Frontend

## Linguaggio: TypeScript

Il frontend è scritto in **TypeScript 5.8**, un superset di JavaScript con tipizzazione statica. TypeScript viene
compilato in JavaScript prima del deploy. La tipizzazione statica garantisce che i contratti tra componenti, servizi e
modelli siano verificati a compile-time, riducendo gli errori a runtime.

---

## Framework UI: React 19

**React 19** è la libreria per la costruzione dell'interfaccia utente. Il progetto usa la modalità moderna basata su
componenti funzionali e hooks. React non viene mai usato direttamente per il routing o la gestione dello stato globale:
queste responsabilità sono delegate a librerie specifiche.

---

## Build tool: Vite

**Vite 6** è il build tool e dev server. Vite usa ES modules nativi del browser in sviluppo (nessun bundling
necessario), il che lo rende significativamente più veloce di webpack in fase di sviluppo. In produzione, Vite usa
Rollup per creare un bundle ottimizzato.

La configurazione si trova in `vite.config.ts`:

```typescript
export default defineConfig({
    plugins: [react()],
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['src/setupTest.ts'],
    },
})
```

Il plugin `@vitejs/plugin-react` abilita il Fast Refresh (aggiornamento istantaneo dei componenti senza perdere lo
stato).

---

## Routing: React Router 7

**React Router 7** gestisce la navigazione client-side. Il progetto usa la modalità dichiarativa con
`createBrowserRouter`. Le route sono definite in `src/router.tsx` e alcune di esse dichiarano un `loader`, una funzione
asincrona eseguita prima del rendering del componente per caricare i dati necessari.

Struttura delle route:

```
/                    → Home (con loader per GitHub stars)
/login               → Pagina di login
/register            → Pagina di registrazione
/profile             → Profilo utente (autenticato)
/users               → Lista utenti (autenticato, admin)
/sso-login-callback  → Callback dopo Google SSO
```

---

## Component library: Material UI (MUI) 7

**Material UI 7** fornisce i componenti UI pronti all'uso seguendo le linee guida Material Design di Google. Il progetto
usa:

- `@mui/material`: componenti base (Button, TextField, AppBar, Card, ecc.)
- `@mui/icons-material`: icone SVG
- `@emotion/react` e `@emotion/styled`: sistema CSS-in-JS usato internamente da MUI

Il tema è personalizzato in `src/theme.tsx`.

---

## Client HTTP: Axios

**Axios 1.9** è il client HTTP usato per comunicare con il backend. La configurazione base si trova in `src/axios.ts`:

```typescript
axios.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
})
```

L'interceptor aggiunge automaticamente il token JWT (salvato in `localStorage`) all'header `Authorization` di ogni
richiesta. Questo centralizza la logica di autenticazione HTTP: i service non devono preoccuparsi di aggiungere il token
manualmente.

L'URL base del backend è letto dalla variabile d'ambiente `VITE_BACKEND_API_URL`, dichiarata nel file `.env` del
frontend e iniettata da Vite a compile-time.

---

## Gestione form: React Hook Form

**React Hook Form 7** gestisce i form di login e registrazione. A differenza di soluzioni come Formik, React Hook Form
usa ref non controllati, minimizzando i re-render durante la digitazione.

---

## Testing: Vitest + Testing Library

Il frontend usa **Vitest** come test runner (integrato in Vite, compatibile con l'API di Jest) e **Testing Library** per
il rendering dei componenti nei test.

| Tool                            | Versione          | Scopo                                              |
|---------------------------------|-------------------|----------------------------------------------------|
| **vitest**                      | (incluso in vite) | Test runner, compatibile con Jest API              |
| **@testing-library/react**      | `^16.3.0`         | Rendering componenti nei test                      |
| **@testing-library/user-event** | `^14.6.1`         | Simulazione interazioni utente                     |
| **@testing-library/jest-dom**   | `^6.6.3`          | Matcher aggiuntivi per il DOM                      |
| **jsdom**                       | `^26.1.0`         | Emulazione DOM per i test (ambiente non-browser)   |
| **msw**                         | `^2.8.2`          | Mock Service Worker per intercettare chiamate HTTP |

I test si trovano nei file `*.test.tsx` accanto ai componenti che testano:

- `LoginForm.test.tsx`
- `RegisterForm.test.tsx`
- `TopMenuBar.test.tsx`
- `UserProfile.test.tsx`
- `users.test.tsx`

---

## Linting e formattazione

| Tool                    | Scopo                                       |
|-------------------------|---------------------------------------------|
| **ESLint 9**            | Analisi statica del codice TypeScript/React |
| **Prettier 3.5**        | Formattazione automatica del codice         |
| **eslint-plugin-react** | Regole specifiche per React                 |
| **typescript-eslint**   | Regole TypeScript per ESLint                |

