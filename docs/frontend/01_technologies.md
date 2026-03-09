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
/users               → Lista utenti (admin)
/sso-login-callback  → Callback dopo Google SSO
/leaderboard         → Classifica run (filtri dataset/metric/split/top_n)
/datasets            → Lista dataset
/datasets/:uuid      → Dettaglio dataset (splits, info, descrizione)
/models              → Lista modelli ML
/models/:uuid        → Dettaglio modello (family, paper, hyperparams)
/experiments/:uuid   → Dettaglio experiment (run + metriche per split)
```

---

## Styling: SASS (SCSS) + BEM

Il progetto usa **SASS (SCSS)** come preprocessore CSS. Non viene usato nessun framework di componenti (niente
Material UI, niente Tailwind, niente Bootstrap). Tutta la stilizzazione è scritta a mano seguendo la metodologia
**BEM** (Block Element Modifier) per i nomi delle classi.

### Perché SASS senza framework

- **Controllo totale**: lo stile riflette esattamente il design system del progetto, senza override di componenti di
  terze parti.
- **Zero dipendenze CSS a runtime**: il CSS generato è statico e ottimizzato da Vite. Nessun CSS-in-JS, nessun
  runtime overhead.
- **Leggibilità**: un componente React usa classi descrittive (`className="btn btn--primary btn--full"`) che
  documentano visivamente la struttura.
- **Manutenibilità**: una modifica al design system (es. cambiare il colore primario) richiede di toccare un unico
  file (`_variables.scss`).

### Metodologia BEM

BEM organizza le classi CSS in tre concetti:

| Concetto     | Sintassi           | Esempio                           |
|--------------|--------------------|-----------------------------------|
| **Block**    | `.block`           | `.btn`, `.card`, `.navbar`        |
| **Element**  | `.block__element`  | `.card__title`, `.btn__icon`      |
| **Modifier** | `.block--modifier` | `.btn--primary`, `.card--compact` |

Esempio concreto in React:

```tsx
<button className="btn btn--primary btn--full">
    <svg className="btn__icon"
    .../>
    Sign In
</button>
```

Il modifier è sempre aggiunto **accanto** al block, mai al posto: `btn btn--primary`, non solo `btn--primary`.

### Struttura dei file SCSS (pattern 7-1 semplificato)

```
src/styles/
├── abstracts/
│   ├── _variables.scss   ← colori, spaziature, tipografia, breakpoint
│   └── _mixins.scss      ← card, input (mixin base)
├── base/
│   ├── _reset.scss       ← reset CSS moderno (box-sizing, margini, font)
│   └── _typography.scss  ← utility classes di testo (.text-muted, .text-center)
├── components/
│   ├── _button.scss      ← .btn, varianti, dimensioni
│   ├── _form.scss        ← .form, .field (label + input + errore)
│   ├── _card.scss        ← .card, .card-grid
│   ├── _alert.scss       ← .alert (inline), .toast (notifica a scomparsa)
│   ├── _avatar.scss      ← .avatar con varianti di dimensione
│   ├── _dialog.scss      ← .dialog, .dialog-backdrop
│   ├── _table.scss       ← .table-wrap, .table, righe cliccabili
│   ├── _badge.scss       ← .badge con varianti semantiche (success/error/…)
│   ├── _stat-card.scss   ← .stat-card, .stat-grid (card KPI)
│   ├── _spinner.scss     ← .spinner (animazione di caricamento)
│   └── _empty-state.scss ← .empty-state (stato vuoto)
├── layout/
│   ├── _layout.scss      ← .layout, .container, .page, .page-header
│   └── _navbar.scss      ← .sidebar, .topbar, .dropdown
├── pages/
│   ├── _home.scss        ← .hero, .features
│   ├── _auth.scss        ← .auth (login/register)
│   ├── _profile.scss     ← .profile
│   ├── _users.scss       ← .users-layout, .user-list
│   ├── _leaderboard.scss ← .leaderboard-filters, .leaderboard-rank, .leaderboard-chart, .leaderboard-link
│   ├── _datasets.scss    ← .dataset-card
│   └── _detail.scss      ← .detail-section, .detail-grid, .detail-field
└── main.scss             ← entry point: importa tutto in ordine
```

Per la documentazione completa del sistema di stile — variabili, mixin, blocchi BEM e regole per gli aggiornamenti —
vedere `03_scss.md`.

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

## Grafici: Recharts

**Recharts** è la libreria per la visualizzazione dati nel frontend. È una libreria dichiarativa basata su componenti
React e D3.js, con licenza MIT (completamente gratuita).

Nel progetto viene usata per:

- **Leaderboard chart**: un grafico a barre che mostra le metriche (es. AUC e LogLoss) per ogni modello, sopra la
  tabella leaderboard. Ispirato alla leaderboard BARS CTR Leaderboard di OpenBenchmark.

Il componente `LeaderboardChart` si trova in `src/components/leaderboard/LeaderboardChart.tsx` e usa:

- `<BarChart>` con `<ResponsiveContainer>` per adattarsi alla larghezza
- `<Bar>` con colori distinti per ogni metrica
- `<Tooltip>` stilizzato in tema dark per coerenza con il design system
- `<Legend>` per identificare le metriche

Recharts è stata scelta come alternativa gratuita a Plotly perché:

- API dichiarativa e React-native (nessun wrapper imperativo)
- Leggera e senza dipendenze pesanti
- Personalizzazione completa dello stile (colori, font, bordi)
- Licenza MIT

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
| **sass**                | Compilazione SCSS → CSS (dev dependency)    |
