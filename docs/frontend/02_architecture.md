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
│   ├── components/       ← btn, form, card, alert, avatar, dialog
│   ├── layout/           ← navbar, layout shell, container
│   └── pages/            ← stili specifici per pagina
├── components/           ← componenti UI riutilizzabili
│   ├── TopMenuBar.tsx
│   ├── LoginForm.tsx
│   ├── RegisterForm.tsx
│   └── UserProfile.tsx
├── contexts/             ← stato globale (React Context)
│   ├── auth.tsx
│   └── snackbar.tsx
├── models/               ← interfacce TypeScript
│   └── user.ts
├── services/             ← client HTTP (chiamate al backend)
│   ├── auth.service.ts
│   └── user.service.ts
└── routes/               ← componenti di pagina (un file per route)
    ├── root.tsx
    ├── home.tsx
    ├── login.tsx
    ├── register.tsx
    ├── profile.tsx
    ├── users.tsx
    └── sso.login.tsx
```

---

## Struttura a strati

Il frontend segue un'architettura a strati orizzontali con responsabilità separate:

```
┌─────────────────────────────────────────┐
│           Routes (pagine)               │  ← routes/
│  home, login, register, profile, users  │
├─────────────────────────────────────────┤
│         Components (UI)                 │  ← components/
│  LoginForm, TopMenuBar, UserProfile…    │
├─────────────────────────────────────────┤
│         Styles (SCSS + BEM)             │  ← styles/
│  variables, mixins, components, pages  │
├─────────────────────────────────────────┤
│         Contexts (stato globale)        │  ← contexts/
│  AuthContext, SnackBarContext           │
├─────────────────────────────────────────┤
│         Services (HTTP)                 │  ← services/
│  auth.service, user.service             │
├─────────────────────────────────────────┤
│         Models (tipi TypeScript)        │  ← models/
│  User                                   │
└─────────────────────────────────────────┘
```

Ogni strato dipende solo dagli strati sottostanti, mai da quelli superiori.

---

## Punto di ingresso: `main.tsx`

```tsx
import './styles/main.scss'   // unico import CSS globale

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <SnackBarProvider>
        <RouterProvider router={router} />
      </SnackBarProvider>
    </AuthProvider>
  </React.StrictMode>,
)
```

`main.scss` è l'unico foglio di stile importato. Non esistono import CSS nei singoli componenti: tutti gli stili
sono centralizati nella cartella `styles/` e compilati da Vite in un unico bundle CSS ottimizzato.

---

## Routing: `router.tsx`

Le route sono definite come array di oggetti e passate a `createBrowserRouter`:

```typescript
export const routes = [
  {
    path: '/',
    Component: Root,           // layout principale con TopMenuBar
    errorElement: <ErrorPage />,
    children: [
      { index: true, Component: Home, loader: homeLoader },
      { path: 'sso-login-callback', Component: SSOLogin, loader: ssoLoader },
      { path: 'profile', Component: Profile },
      { path: 'login', Component: Login },
      { path: 'register', Component: Register },
      { path: 'users', Component: Users, loader: usersLoader },
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

`TopMenuBar` (`components/TopMenuBar.tsx`) usa le classi BEM `.navbar` e `.dropdown`. Implementa:

- brand link a sinistra (`.navbar__brand`)
- link di navigazione contestuali a destra (`.navbar__link`, `.navbar__link--active`)
- avatar button con dropdown accessibile via `aria-expanded` e click-outside handler
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
<input className={`field__input${errors.email ? ' field__input--error' : ''}`} />
```

### Variabili e mixin

Tutti i valori di design (colori, spaziature, breakpoint, tipografia) sono dichiarati in `_variables.scss` e usati
tramite `@use '../abstracts/variables' as *`. Un cambio di colore primario si propaga automaticamente in tutto il CSS.

I mixin riutilizzabili (`flex-center`, `card-surface`, `input-base`, `button-base`, `respond-to`) sono in
`_mixins.scss` e riducono la duplicazione tra componenti.

### Responsive design

Il breakpoint system usa `@include respond-to(md)` (mobile-first):

```scss
.card-grid {
  grid-template-columns: 1fr;             // mobile

  @include respond-to(sm) {
    grid-template-columns: repeat(2, 1fr); // ≥576px
  }

  @include respond-to(lg) {
    grid-template-columns: repeat(3, 1fr); // ≥992px
  }
}
```

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

---

## Modelli TypeScript: `models/user.ts`

```typescript
export interface User {
  uuid: string
  email: string
  password?: string
  first_name?: string
  last_name?: string
  provider?: string
  picture?: string
  is_active?: boolean
  is_superuser?: boolean
}
```

Questa interfaccia rispecchia lo schema `schemas.User` del backend. I campi opzionali (`?`) corrispondono ai campi
`Optional` di Pydantic.

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

