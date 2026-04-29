# Architettura Frontend

## Struttura delle cartelle

```
src/
├── main.tsx              ← punto di ingresso, monta React + Provider
├── router.tsx            ← definizione route con createBrowserRouter
├── axios.ts              ← interceptor JWT globale
├── error-page.tsx        ← pagina di errore (404, crash)
├── fallback.tsx          ← spinner di loading (HydrateFallback)
├── vite-env.d.ts         ← tipi variabili d'ambiente Vite
├── setupTest.ts          ← setup Vitest + jest-dom
├── styles/               ← tutto il CSS, organizzato per responsabilità
│   ├── main.scss         ← entry point: importa tutto in ordine
│   ├── abstracts/        ← variabili e mixin (no output CSS)
│   ├── base/             ← reset e tipografia
│   ├── components/       ← btn, form, card, badge, table, stat-card…
│   ├── layout/           ← sidebar, topbar, layout shell
│   └── pages/            ← stili specifici per pagina
├── components/           ← componenti UI riutilizzabili
│   ├── TopMenuBar.tsx    ← sidebar + topbar con navigazione completa
│   ├── LoginForm.tsx
│   ├── RegisterForm.tsx
│   ├── UserProfile.tsx
│   ├── index.ts          ← barrel file (re-export tutto)
│   └── common/           ← componenti generici riusabili
│       ├── Badge.tsx         ← badge con varianti semantiche
│       ├── DataTable.tsx     ← tabella generica tipizzata
│       ├── EmptyState.tsx    ← stato vuoto con messaggio
│       ├── LoadingSpinner.tsx
│       ├── PageHeader.tsx    ← intestazione pagina (titolo + azioni)
│       └── StatCard.tsx      ← card KPI (label + value + icona)
├── contexts/             ← stato globale (React Context)
│   ├── auth.tsx
│   └── snackbar.tsx
├── models/               ← interfacce TypeScript
│   ├── user.ts
│   ├── dataset.ts        ← DatasetSummary, DatasetPublic, TaskType…
│   ├── ml-model.ts       ← MLModelSummary, MLModelPublic…
│   ├── experiment.ts     ← ExperimentPublic, Status, CodeInfo…
│   ├── metric.ts         ← MetricPublic, ExperimentMetrics, Split…
│   ├── leaderboard.ts    ← LeaderboardEntry
│   └── index.ts          ← barrel file (re-export tutto)
├── services/             ← client HTTP (chiamate al backend)
│   ├── auth.service.ts
│   ├── user.service.ts
│   ├── dataset.service.ts
│   ├── ml-model.service.ts
│   ├── experiment.service.ts
│   ├── leaderboard.service.ts
│   └── index.ts          ← barrel file (re-export tutto)
└── routes/               ← componenti di pagina (un file per route)
    ├── root.tsx          ← layout shell (TopMenuBar + Outlet)
    ├── home.tsx
    ├── login.tsx
    ├── register.tsx
    ├── profile.tsx
    ├── users.tsx         ← admin only
    ├── sso.login.tsx
    ├── leaderboard.tsx   ← filtri + grafico + tabella ordinabile
    ├── datasets.tsx      ← griglia card dataset
    ├── dataset-detail.tsx
    ├── models.tsx        ← tabella modelli ML
    ├── model-detail.tsx
    └── experiment-detail.tsx
```

---

## Struttura a strati

Il frontend segue un'architettura a strati orizzontali con responsabilità separate:

```
┌─────────────────────────────────────────────────────────┐
│                    Routes (pagine)                      │  ← routes/
│  home, login, register, profile, users,                 │
│  leaderboard, datasets, dataset-detail,                 │
│  models, model-detail, experiment-detail                │
├─────────────────────────────────────────────────────────┤
│                  Components (UI)                        │  ← components/
│  TopMenuBar, LoginForm, UserProfile…                    │
│  common/: Badge, DataTable, StatCard, PageHeader…       │
├─────────────────────────────────────────────────────────┤
│                Styles (SCSS + BEM)                      │  ← styles/
│  variables, mixins, components, layout, pages           │
├─────────────────────────────────────────────────────────┤
│               Contexts (stato globale)                  │  ← contexts/
│  AuthContext, SnackBarContext                           │
├─────────────────────────────────────────────────────────┤
│                 Services (HTTP)                         │  ← services/
│  auth, user, dataset, ml-model, experiment, leaderboard │
├─────────────────────────────────────────────────────────┤
│               Models (tipi TypeScript)                  │  ← models/
│  User, Dataset, MLModel, Experiment, Metric, Leaderboard│
└─────────────────────────────────────────────────────────┘
```

Ogni strato dipende solo dagli strati sottostanti, mai da quelli superiori.

---

## Punto di ingresso: `main.tsx`

```tsx
import './styles/main.scss'   // unico import CSS globale
import './axios'              // bootstrap interceptor JWT globale

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <AuthProvider>
            <SnackBarProvider>
                <RouterProvider router={router}/>
            </SnackBarProvider>
        </AuthProvider>
    </React.StrictMode>,
)
```

`main.scss` è l'unico foglio di stile importato. Non esistono import CSS nei singoli componenti: tutti gli stili
sono centralizati nella cartella `styles/` e compilati da Vite in un unico bundle CSS ottimizzato.

`axios.ts` viene importato in bootstrap per registrare subito gli interceptor request/response: tutte le chiamate API
successive (incluso `GET /users/me` all'avvio) ereditano automaticamente l'header `Authorization`.

---

## Routing: `router.tsx`

Le route sono definite come array di oggetti e passate a `createBrowserRouter`:

```typescript
export const routes = [
    {
        path: '/',
        Component: Root,           // layout principale con TopMenuBar
        errorElement: <ErrorPage / >,
        children: [
            {index: true, Component: Home, loader: homeLoader},
            {path: 'sso-login-callback', Component: SSOLogin, loader: ssoLoader},
            {path: 'profile', Component: Profile},
            {path: 'login', Component: Login},
            {path: 'register', Component: Register},
            {path: 'users', Component: Users, loader: usersLoader},
            {path: 'leaderboard', Component: Leaderboard},
            {path: 'datasets', Component: Datasets, loader: datasetsLoader},
            {path: 'datasets/:uuid', Component: DatasetDetail, loader: datasetDetailLoader},
            {path: 'dataset-versions/:uuid', Component: DatasetVersionDetail, loader: datasetVersionDetailLoader},
            {path: 'pipelines/:uuid', Component: PipelineDetail, loader: pipelineDetailLoader},
            {path: 'models', Component: Models, loader: modelsLoader},
            {path: 'models/:uuid', Component: ModelDetail, loader: modelDetailLoader},
            {path: 'experiments/new', Component: SubmitExperiment},
            {path: 'experiments/:uuid', Component: ExperimentDetail, loader: experimentDetailLoader},
        ],
    },
]
```

Il componente `Root` funziona da **layout shell**: contiene `TopMenuBar` e `<Outlet />`. Tutte le route figlie vengono
renderizzate dentro `<Outlet />`, condividendo la barra di navigazione.

### Loader pattern

Alcune route dichiarano un `loader`, una funzione asincrona eseguita da React Router **prima** del rendering del
componente. I dati restituiti dal loader sono accessibili nel componente tramite `useLoaderData()`. Questo pattern evita
il "flash" di contenuto vuoto tipico del fetch-on-render.

---

## Layout: `Root` e `TopMenuBar`

`Root` (`routes/root.tsx`) è il layout condiviso da tutte le pagine:

```tsx
export default function Root() {
    return (
        <div className="layout">
            <TopMenuBar/>
            <main className="layout__main">
                <Outlet/>
            </main>
        </div>
    )
}
```

`TopMenuBar` (`components/TopMenuBar.tsx`) implementa sidebar e topbar. Implementa:

- brand link (`.sidebar__brand`, `.sidebar__brand-name`)
- link di navigazione con NavLink attivo (`.sidebar__item`, `.sidebar__item--active`)
- bottone chiudi sidebar X (`.sidebar__close`) e bottone hamburger (`.topbar__toggle`)
- **dropdown utente autenticato**: avatar/iniziale + nome, link Profile, bottone Logout
- **dropdown guest**: icona profilo SVG con voci Login e Register
- overlay backdrop su mobile (`.sidebar-overlay`) che chiude la sidebar al click
- chiusura automatica della sidebar al click di un link su mobile (`closeSidebarOnMobile`)
- sidebar **fullscreen** su viewport < 768px (z-index modale)
- sidebar chiusa di default su mobile (`useState(() => window.innerWidth >= 768)`)
- SVG inline al posto di librerie di icone esterne

Il dropdown si chiude automaticamente cliccando fuori grazie a un `mousedown` listener su `document` (pulito nel
cleanup di `useEffect`).

---

## Sistema di stile: SCSS + BEM

### Principio generale

Nessun componente ha stili inline né fogli CSS propri. Tutti gli stili sono in `src/styles/`. Un componente React
applica classi BEM con `className`:

```tsx
// Block + Modifier
<button className="btn btn--primary btn--full">

    // Block__Element
    <label className="field__label">

        // Block__Element con stato condizionale
        <input className={`field__input${errors.email ? ' field__input--error' : ''}`}/>
```

### Variabili e mixin

Tutti i valori di design (colori, spaziature, breakpoint, tipografia) sono dichiarati in `_variables.scss` e usati
tramite `@use '../abstracts/variables' as *`. Un cambio di colore primario si propaga automaticamente in tutto il CSS.

I mixin `card` e `input` in `_mixins.scss` riducono la duplicazione tra componenti: `@mixin card` applica sfondo,
bordo e border-radius standard; `@mixin input` applica lo stile base di un campo di testo.

Per la documentazione completa — variabili, mixin, blocchi BEM e regole per aggiornamenti — vedere `03_scss.md`.

---

## Gestione dello stato globale: React Context

### AuthContext (`contexts/auth.tsx`)

Il contesto di autenticazione espone:

```typescript
type AuthContextType = {
    user: User | undefined
    setUser: (user: User | undefined) => void
    login: (data: FormData) => void
    logout: () => void
}
```

All'inizializzazione del provider (`useEffect` al primo mount), viene chiamato `userService.getProfile()` per verificare
se esiste una sessione attiva (token in `localStorage`). Se la chiamata ha successo, l'utente viene salvato nello stato;
altrimenti lo stato rimane `undefined`.

### SnackBarContext (`contexts/snackbar.tsx`)

Gestisce le notifiche toast globali senza dipendenze esterne. Ogni toast ha un ID progressivo e viene rimosso
automaticamente dopo il timeout tramite `setTimeout`. Il container `.toast-container` è posizionato fixed in basso e
usa `aria-live="polite"` per accessibilità.

```typescript
type SnackBarContextActions = {
    showSnackBar: (message: string, severity: Severity, timeout?: number) => void
}
// severity: 'success' | 'error' | 'warning' | 'info'
```

---

## Services: chiamate HTTP

I service sono classi singleton che incapsulano le chiamate HTTP al backend. Non contengono logica UI.
Tutti i service sono accessibili tramite il barrel `services/index.ts`.

### `auth.service.ts`

| Metodo                | Endpoint                   | Descrizione                             |
|-----------------------|----------------------------|-----------------------------------------|
| `register(user)`      | `POST /users`              | Registrazione                           |
| `login(data)`         | `POST /login/access-token` | Login, salva token in localStorage      |
| `refreshToken()`      | `GET /login/refresh-token` | Rinnovo token (post-SSO)                |
| `logout()`            | —                          | Rimuove token da localStorage           |
| `getGoogleLoginUrl()` | —                          | Restituisce URL per redirect Google SSO |

### `user.service.ts`

| Metodo                        | Endpoint             | Descrizione              |
|-------------------------------|----------------------|--------------------------|
| `getProfile()`                | `GET /users/me`      | Profilo utente corrente  |
| `updateProfile(profile)`      | `PATCH /users/me`    | Aggiorna profilo         |
| `updateUser(userId, profile)` | `PATCH /users/{id}`  | Aggiorna utente (admin)  |
| `getUsers()`                  | `GET /users`         | Lista utenti (admin)     |
| `deleteUser(userId)`          | `DELETE /users/{id}` | Elimina utente (admin)   |
| `deleteSelf()`                | `DELETE /users/me`   | Elimina account corrente |

### `dataset.service.ts`

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `getAll()` | `GET /datasets` | Lista tutti i dataset |
| `getByUuid(uuid)` | `GET /datasets/{uuid}` | Dettaglio singolo dataset |
| `create(data)` | `POST /datasets` | Crea nuovo dataset |
| `getVersions(datasetUuid)` | `GET /datasets/{uuid}/versions` | Lista versioni dataset |
| `getVersionByUuid(versionUuid)` | `GET /dataset-versions/{uuid}` | Dettaglio versione |
| `getVersionSourcesWithResources(versionUuid)` | `GET /dataset-versions/{uuid}/sources-with-resources` | Sources annidate con resources |
| `getVersionPipelines(versionUuid)` | `GET /dataset-versions/{uuid}/pipelines` | Lista pipeline della versione |
| `getVersionYaml(versionUuid, kind)` | `GET /dataset-versions/{uuid}/yaml/{kind}` | YAML dataset/version/characteristics |

### Comportamento `routes/dataset-version-detail.tsx`

- unica sezione `Sources & Resources` (non due tabelle separate)
- ogni source e' cliccabile (accordion) e mostra sotto solo le resource figlie
- i dati arrivano da `getVersionSourcesWithResources(versionUuid)` per mantenere la gerarchia padre→figlie

### `ml-model.service.ts`

| Metodo            | Endpoint                | Descrizione               |
|-------------------|-------------------------|---------------------------|
| `getAll()`        | `GET /ml-models`        | Lista tutti i modelli     |
| `getByUuid(uuid)` | `GET /ml-models/{uuid}` | Dettaglio singolo modello |
| `create(data)`    | `POST /ml-models`       | Registra nuovo modello    |

### `experiment.service.ts`

| Metodo                           | Endpoint                                     | Descrizione                              |
|----------------------------------|----------------------------------------------|------------------------------------------|
| `create(data)`                   | `POST /experiments`                          | Crea run (path principale: `pipeline_uuid`) |
| `getByUuid(uuid)`                | `GET /experiments/{uuid}`                    | Dettaglio singolo experiment             |
| `getMetrics(uuid)`               | `GET /experiments/{uuid}/metrics`            | Metriche raggruppate per split           |
| `importMetricsCsv(uuid, file)`   | `POST /experiments/{uuid}/metric-import`     | Upload CSV async                         |
| `listMetricImports(uuid)`        | `GET /experiments/{uuid}/metric-imports`     | Storico job import                       |
| `listByDatasetVersion(uuid)`     | `GET /dataset-versions/{uuid}/experiments`   | Esperimenti della versione               |
| `listByPipeline(uuid)`           | `GET /pipelines/{uuid}/experiments`          | Esperimenti della pipeline               |

### `leaderboard.service.ts`

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `get(datasetUuid, metric, split, n, datasetVersionUuid?, pipelineUuid?, modelUuids?, authorUuids?)` | `GET /leaderboard?...` | Top-N con filtri dataset/version/pipeline/model/author |
| `getMultiMetric(datasetUuid, metrics, split, sortBy, n, datasetVersionUuid?, pipelineUuid?, modelUuids?, authorUuids?)` | `GET /leaderboard/multi?...` | Leaderboard multi-metrica con filtri estesi |
| `query(payload)` | `POST /leaderboard/query` | Query avanzata con hyperparam filters |
| `getBestConfiguration(payload)` | `POST /leaderboard/best-configuration` | Best configuration server-side |

### Comportamento `routes/leaderboard.tsx`

- filtri server-side: `dataset`, `dataset_version`, `pipeline`, `split`, `sort_by`, `top_n`, `model_uuids`, `author_uuids`, `hyperparam_filters`
- tabella mostrata prima del grafico (tabella come vista primaria)
- modal `Show best configuration` usato solo per impostazioni; risultati renderizzati in sezione dedicata nella pagina
- filtri `Models` e `Authors` con checkbox (`All ...` + selezioni puntuali), non con select multiple
- column picker persistito in `localStorage` (colonne base + metriche + hyperparams)
- bottone `Show best configuration` (modal con grouping per hyperparams)
- bottone `Export LaTeX` sulla tabella visibile/filtrata
- filtro client-side sempre visibile: `chart_mode` (`auto` | `line` | `bar`)
- tabella con sort client-side su header cliccabili
- toggle asc/desc per ogni colonna; icona direzione nell'intestazione
- ranking visuale ricalcolato in base all'ordine corrente della tabella
- grafico adattivo:
  - modalità `auto`: CTR (`auc` + `logloss`) → line chart dual-axis ordinato per AUC; altrimenti grouped bars
  - modalità `line`: line chart sempre attivo (dual-axis per CTR, single-axis negli altri casi)
  - modalità `bar`: grouped bars sempre attivo

---

## Modelli TypeScript

Tutti i modelli si trovano in `models/` e sono re-esportati dal barrel `models/index.ts`.
Ogni interfaccia rispecchia lo schema Pydantic corrispondente nel backend. I campi opzionali (`?`) corrispondono
ai campi `Optional` di Pydantic. Gli identificatori esposti sono sempre **UUID**, mai ObjectId MongoDB.

### `user.ts`

```typescript
interface User {
    uuid: string;
    email: string;
    first_name?: string;
    last_name?: string
    picture?: string;
    is_active?: boolean;
    is_superuser?: boolean
}
```

### `dataset.ts`

```typescript
type TaskType = 'ranking' | 'rating_prediction'
type Visibility = 'public' | 'private'

interface DatasetSummary {
    uuid;
    name;
    version;
    task;
    visibility
}

interface DatasetPublic {
    uuid;
    name;
    version;
    task;
    description?;
    visibility;
    splits?;
    created_at;
    ...
}
```

### `ml-model.ts`

```typescript
interface MLModelSummary {
    uuid;
    name;
    family?;
    paper_url?
}

interface MLModelPublic {
    uuid;
    name;
    family?;
    paper_url?;
    implementation?;
    hyperparams?;
    created_at;
    ...
}
```

### `experiment.ts`

```typescript
type Status = 'queued' | 'running' | 'finished' | 'failed'

interface ExperimentPublic {
    uuid;
    dataset_uuid;
    model_uuid;
    submitted_by_user_uuid;
    status;
    seed?;
    notes?;
    training_config?;
    code?;
    artifacts?;
    created_at;
    finished_at?
}
```

### `metric.ts`

```typescript
type Split = 'validation' | 'test'
type Direction = 'max' | 'min'

interface MetricPublic {
    uuid;
    experiment_uuid;
    dataset_uuid;
    model_uuid;
    split;
    metric;
    value;
    direction;
    computed_at
}

interface ExperimentMetrics {
    experiment_uuid;
    metrics_by_split: Record<Split, MetricPublic[]>
}
```

### `leaderboard.ts`

```typescript
interface LeaderboardEntry {
    experiment_uuid;
    model_uuid;
    model_name?;
    dataset_uuid;
    split;
    metric;
    value;
    direction;
    rank?
}

interface MultiMetricLeaderboardEntry {
    experiment_uuid;
    model_uuid;
    model_name?;
    dataset_uuid;
    split;
    metrics: Record<string, number>;
    directions: Record<string, Direction>;
    repo_url?;
    rank?
}
```

---

## Flusso SSO Google

1. L'utente clicca "Connect with Google" → redirect a `GET /api/v1/login/google`
2. Il backend esegue il redirect a Google
3. Dopo il consenso, Google redirige al backend (`/api/v1/login/google/callback`)
4. Il backend crea/trova l'utente, genera il JWT, imposta un cookie `HttpOnly` e redirige al frontend su
   `/sso-login-callback`
5. Il componente `SSOLogin` (con loader) chiama `authService.refreshToken()` che legge il JWT dal cookie e lo salva in
   `localStorage`
6. L'utente viene rediretto alla home autenticato
