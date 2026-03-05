# Architettura Frontend

## Struttura a strati

Il frontend segue un'architettura a strati orizzontali con responsabilità separate:

```
┌─────────────────────────────────────────┐
│           Routes (pagine)               │  ← routes/
│  home, login, register, profile, users  │
├─────────────────────────────────────────┤
│         Components (UI)                 │  ← components/
│  LoginForm, TopMenuBar, UserProfile...  │
├─────────────────────────────────────────┤
│         Contexts (stato globale)        │  ← contexts/
│  AuthContext, SnackBarContext           │
├─────────────────────────────────────────┤
│         Services (HTTP)                 │  ← services/
│  auth.service, user.service             │
├─────────────────────────────────────────┤
│         Models (tipi TypeScript)        │  ← models/
│  User                                   │
├─────────────────────────────────────────┤
│         Axios (client HTTP)             │  ← axios.ts
│  interceptor JWT                        │
└─────────────────────────────────────────┘
```

Ogni strato dipende solo dagli strati sottostanti, mai da quelli superiori.

---

## Punto di ingresso: `main.tsx`

```tsx
// src/main.tsx
ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <RouterProvider router={router}/>
    </React.StrictMode>
)
```

React monta l'applicazione nel div `#root` di `index.html`. `RouterProvider` gestisce il routing lato client.

---

## Routing: `router.tsx`

Le route sono definite come array di oggetti e passate a `createBrowserRouter`:

```typescript
export const routes = [
    {
        path: '/',
        Component: Root,          // layout principale con TopMenuBar
        errorElement: <ErrorPage / >,
        children: [
            {index: true, Component: Home, loader: homeLoader},
            {path: 'sso-login-callback', Component: SSOLogin, loader: ssoLoader},
            {path: 'profile', Component: Profile},
            {path: 'login', Component: Login},
            {path: 'register', Component: Register},
            {path: 'users', Component: Users, loader: usersLoader},
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
        <Box sx={{display: 'flex'}}>
            <TopMenuBar/>
            <Box component='main' sx={{flexGrow: 1, height: '100vh', overflow: 'auto'}}>
                <Toolbar/> {/* spacer per non sovrapporre la AppBar */}
                <Outlet/>
            </Box>
        </Box>
    )
}
```

`TopMenuBar` (`components/TopMenuBar.tsx`) è una `AppBar` Material UI che:

- mostra il nome dell'applicazione e link di navigazione
- se l'utente è autenticato, mostra un avatar con menu dropdown (profilo, logout)
- se l'utente non è autenticato, mostra i link Login e Register
- usa `useAuth()` dal contesto di autenticazione per leggere lo stato dell'utente
- usa `useNavigate()` di React Router per reindirizzare dopo il logout

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

**`login(data)`**: chiama `authService.login(data)` (che salva il token in `localStorage`), poi
`userService.getProfile()` per aggiornare lo stato utente.

**`logout()`**: chiama `authService.logout()` (che rimuove il token da `localStorage`) e imposta `user = undefined`.

Il contesto è accessibile in qualsiasi componente tramite il hook `useAuth()`.

### SnackBarContext (`contexts/snackbar.tsx`)

Gestisce le notifiche toaste globali (Material UI `Snackbar`). Espone:

```typescript
type SnackBarContextActions = {
    showSnackBar: (message: string, severity: AlertColor, timeout?: number) => void
}
```

Qualsiasi componente può mostrare una notifica con `useSnackBar().showSnackBar("messaggio", "success")`.

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

1. L'utente clicca "Accedi con Google" → il frontend naviga a `authService.getGoogleLoginUrl()` che punta a
   `GET /api/v1/login/google`
2. Il backend esegue il redirect a Google
3. Dopo il consenso, Google redirige al backend (`/api/v1/login/google/callback`)
4. Il backend crea/trova l'utente, genera il JWT, imposta un cookie `HttpOnly` e redirige al frontend su
   `/sso-login-callback`
5. Il componente `SSOLogin` (con loader) chiama `authService.refreshToken()` che legge il JWT dal cookie e lo salva in
   `localStorage`
6. L'utente viene rediretto alla home autenticato

