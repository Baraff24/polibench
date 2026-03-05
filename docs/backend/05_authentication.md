# Autenticazione e Autorizzazione

Il sistema di autenticazione è implementato in `backend/app/auth/auth.py` e supporta due modalità distinte: *
*credenziali locali** (email + password) e **Google SSO** (OAuth2).

---

## Autenticazione con credenziali locali

### Hashing delle password

Le password non vengono mai salvate in chiaro. Al momento della registrazione o del cambio password, la password viene
hashata con **bcrypt** tramite `passlib`:

```python
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)
```

`bcrypt` è un algoritmo di hashing adattivo con salt automatico. Il parametro di work factor può essere aumentato nel
tempo per compensare l'incremento della potenza computazionale degli attacchi brute-force.

Il campo `hashed_password` nel Document `User` è `None` per gli utenti registrati tramite SSO, che non hanno una
password locale.

### Flusso di login

1. Il client invia `username` (email) e `password` come form data a `POST /api/v1/login/access-token`
2. La funzione `authenticate_user()` cerca l'utente per email e verifica la password con `verify_password()`
3. Se le credenziali sono corrette e l'utente è attivo, viene generato un **JWT** (JSON Web Token)
4. Il token viene restituito al client come `{"access_token": "...", "token_type": "bearer"}`
5. Il client salva il token in `localStorage` e lo include in tutte le richieste successive nell'header
   `Authorization: Bearer <token>`

---

## JWT (JSON Web Token)

I token JWT sono generati e verificati con la libreria **python-jose** usando l'algoritmo **HS256** (HMAC con SHA-256).

### Struttura del payload

```json
{
  "sub": "<uuid-dell-utente>",
  "exp": 1234567890
}
```

- `sub` (subject): l'UUID dell'utente (non l'`_id` MongoDB)
- `exp` (expiration): timestamp Unix di scadenza

### Generazione del token

```python
def create_access_token(subject: str | Any, expires_delta: timedelta | None = None):
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
```

La durata predefinita è configurata tramite `settings.ACCESS_TOKEN_EXPIRE_MINUTES` (default: 8 giorni).

### Verifica del token

```python
async def _get_current_user(token: str) -> models.User:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    userid = payload.get("sub")
    token_data = schemas.TokenPayload(uuid=userid)
    user = await models.User.find_one({"uuid": token_data.uuid})
    return user
```

Se il token è scaduto, malformato o la firma non corrisponde, `jwt.decode()` lancia `JWTError` e il sistema risponde con
HTTP 401.

### Chiave segreta

`settings.SECRET_KEY` è letta dal file `.env`. Se non è impostata, viene generata una chiave casuale ad ogni avvio
dell'applicazione tramite `secrets.token_urlsafe(32)`. In produzione è **obbligatorio** impostare una chiave fissa e
sicura nel `.env`.

---

## Dependency Injection per l'autenticazione

FastAPI utilizza il sistema `Depends()` per iniettare l'utente autenticato negli endpoint. Sono definite tre dipendenze
principali:

```python
# Legge il token dall'header Authorization: Bearer
async def get_current_user(token: str = Depends(oauth2_scheme)) -> models.User


# Uguale, ma legge il token dal cookie HttpOnly (usato dopo SSO)
async def get_current_user_from_cookie(token: str = Depends(oauth2_scheme_with_cookies)) -> models.User


# Verifica che l'utente sia attivo
def get_current_active_user(current_user=Depends(get_current_user)) -> models.User


# Verifica che l'utente sia superuser
def get_current_active_superuser(current_user=Depends(get_current_user)) -> models.User
```

Esempio di uso in un router:

```python
@router.get("/me", response_model=schemas.User)
async def get_profile(
        current_user: models.User = Depends(get_current_active_user)
):
    return current_user
```

Se il token è assente o invalido, FastAPI risponde automaticamente con HTTP 401 prima di eseguire il corpo della
funzione.

---

## Google SSO (OAuth2)

Il sistema supporta il login tramite **Google OAuth2** tramite la libreria `fastapi-sso`. Il flusso è il seguente:

```
Client                    Backend                   Google
  │                          │                         │
  │  GET /login/google        │                         │
  │ ─────────────────────────►│                         │
  │                          │  Redirect a Google       │
  │ ◄─────────────────────────│─────────────────────────►
  │                          │                         │
  │  Utente acconsente        │                         │
  │                          │ ◄─────────────────────── │
  │                          │  GET /login/google/callback
  │                          │  (con authorization code) │
  │                          │                         │
  │                          │  Verifica token Google   │
  │                          │  Crea/trova utente DB    │
  │                          │  Genera JWT              │
  │  Redirect a frontend      │                         │
  │ ◄─────────────────────────│                         │
  │  (cookie HttpOnly con JWT)│                         │
```

### Callback e cookie HttpOnly

Dopo la verifica con Google, il backend:

1. Cerca l'utente per email nel database
2. Se non esiste, lo crea con i dati forniti da Google (`email`, `first_name`, `last_name`, `picture`, `provider`)
3. Genera un JWT con UUID dell'utente
4. Esegue un redirect al frontend (`settings.SSO_LOGIN_CALLBACK_URL`)
5. Imposta il JWT in un **cookie HttpOnly** con scadenza 120 secondi

```python
response = RedirectResponse(settings.SSO_LOGIN_CALLBACK_URL)
response.set_cookie(
    "Authorization",
    value=f"Bearer {access_token}",
    httponly=True,
    max_age=120,
    expires=120,
)
```

Il cookie `HttpOnly` non è accessibile da JavaScript, riducendo il rischio di attacchi XSS. Il frontend ha 120 secondi
per leggere il token dal cookie tramite `GET /login/refresh-token` e salvarlo in `localStorage` per le richieste future.

### Classe `OAuth2PasswordBearerWithCookie`

È una classe custom che estende `fastapi.security.OAuth2` per leggere il token dal cookie `Authorization` invece che
dall'header HTTP standard. Viene usata esclusivamente nella dipendenza `get_current_user_from_cookie`, usata
dall'endpoint `GET /login/refresh-token`.

---

## Configurazione SSO

Le variabili d'ambiente necessarie per abilitare Google SSO:

| Variabile                | Descrizione                                                                                            |
|--------------------------|--------------------------------------------------------------------------------------------------------|
| `GOOGLE_CLIENT_ID`       | ID client dell'applicazione Google Cloud                                                               |
| `GOOGLE_CLIENT_SECRET`   | Secret client                                                                                          |
| `SSO_CALLBACK_HOSTNAME`  | Hostname del backend (es. `https://api.polibench.example.com`)                                         |
| `SSO_LOGIN_CALLBACK_URL` | URL frontend dove reindirizzare dopo il login (es. `https://polibench.example.com/sso-login-callback`) |

Se `GOOGLE_CLIENT_ID` o `GOOGLE_CLIENT_SECRET` non sono impostati, gli endpoint SSO rispondono con HTTP 400.

---

## Riepilogo degli endpoint di autenticazione

| Endpoint                        | Metodo | Auth richiesta | Descrizione              |
|---------------------------------|--------|----------------|--------------------------|
| `/api/v1/login/access-token`    | POST   | No             | Login con email/password |
| `/api/v1/login/test-token`      | GET    | JWT header     | Verifica validità token  |
| `/api/v1/login/refresh-token`   | GET    | JWT cookie     | Rinnova token (post-SSO) |
| `/api/v1/login/google`          | GET    | No             | Redirect a Google OAuth2 |
| `/api/v1/login/google/callback` | GET    | No             | Callback Google OAuth2   |

