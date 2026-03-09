# Configurazione e Variabili d'Ambiente

## Dove si trova la configurazione

La configurazione dell'applicazione è centralizzata in `backend/app/config/config.py`. Il file `.env` si trova nella *
*root del progetto** (un livello sopra `backend/`), e viene letto automaticamente da `pydantic-settings`.

```
polibench/
├── .env               ← variabili d'ambiente (NON committare mai questo file)
├── .env.example       ← template con valori di esempio (si committa)
├── backend/
│   └── app/
│       └── config/
│           └── config.py   ← classe Settings
```

---

## Classe Settings

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
```

- `env_file="../.env"`: il path è relativo alla directory di lavoro da cui viene avviata l'applicazione (tipicamente
  `backend/`)
- `env_ignore_empty=True`: le variabili presenti nel `.env` con valore vuoto vengono ignorate (non sovrascrivono i
  default)
- `extra="ignore"`: le variabili d'ambiente non dichiarate in `Settings` vengono ignorate silenziosamente

All'avvio, viene eseguita `settings = Settings()`. Se una variabile obbligatoria (senza valore di default) è assente,
`pydantic-settings` lancia un `ValidationError` con un messaggio chiaro che elenca i campi mancanti, e l'applicazione
non parte.

---

## Variabili d'ambiente

### Applicazione

| Variabile                     | Tipo               | Default            | Obbligatoria | Descrizione                                                         |
|-------------------------------|--------------------|--------------------|--------------|---------------------------------------------------------------------|
| `PROJECT_NAME`                | `str`              | —                  | ✅            | Nome del progetto (appare in Swagger)                               |
| `API_V1_STR`                  | `str`              | `/api/v1`          | ❌            | Prefisso di tutti gli endpoint                                      |
| `ENVIRONMENT`                 | `Literal`          | `development`      | ❌            | `development`, `test` o `production`                                |
| `SECRET_KEY`                  | `str`              | random             | ❌            | Chiave HMAC per i JWT. **In produzione deve essere fissa e sicura** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int`              | `11520` (8 giorni) | ❌            | Durata dei token JWT in minuti                                      |
| `BACKEND_CORS_ORIGINS`        | `list[AnyHttpUrl]` | `[]`               | ❌            | Origini HTTP ammesse dal middleware CORS                            |

### Superutente iniziale

| Variabile                  | Tipo       | Obbligatoria | Descrizione                            |
|----------------------------|------------|--------------|----------------------------------------|
| `FIRST_SUPERUSER`          | `EmailStr` | ✅            | Email del superutente creato all'avvio |
| `FIRST_SUPERUSER_PASSWORD` | `str`      | ✅            | Password del superutente iniziale      |

All'avvio dell'applicazione, se non esiste nessun utente con questa email, viene creato automaticamente un account
superutente. Questo garantisce che il sistema sia accessibile anche al primo avvio senza dati.

### Database MongoDB

| Variabile        | Tipo  | Obbligatoria | Descrizione                                                    |
|------------------|-------|--------------|----------------------------------------------------------------|
| `MONGO_HOST`     | `str` | ✅            | Hostname del server MongoDB (es. `localhost` o `db` in Docker) |
| `MONGO_PORT`     | `int` | ✅            | Porta MongoDB (tipicamente `27017`)                            |
| `MONGO_DB`       | `str` | ✅            | Nome del database                                              |
| `MONGO_USER`     | `str` | ❌            | Username MongoDB                                               |
| `MONGO_PASSWORD` | `str` | ❌            | Password MongoDB                                               |

In ambiente Docker Compose, `MONGO_HOST` è `db` (il nome del servizio MongoDB nella rete interna di Docker).

### Google SSO

| Variabile                | Tipo  | Obbligatoria | Descrizione                                                    |
|--------------------------|-------|--------------|----------------------------------------------------------------|
| `GOOGLE_CLIENT_ID`       | `str` | ❌            | ID client dell'app Google Cloud Console                        |
| `GOOGLE_CLIENT_SECRET`   | `str` | ❌            | Secret client Google                                           |
| `SSO_CALLBACK_HOSTNAME`  | `str` | ❌            | URL base del backend (es. `https://api.polibench.example.com`) |
| `SSO_LOGIN_CALLBACK_URL` | `str` | ❌            | URL frontend dopo il login SSO                                 |

Se `GOOGLE_CLIENT_ID` o `GOOGLE_CLIENT_SECRET` sono assenti, gli endpoint `/login/google` e `/login/google/callback`
rispondono HTTP 400.

### Email (SMTP)

| Variabile         | Tipo   | Default | Obbligatoria | Descrizione                                     |
|-------------------|--------|---------|--------------|-------------------------------------------------|
| `SMTP_HOST`       | `str`  | `None`  | ❌            | Hostname del server SMTP (es. `smtp.gmail.com`) |
| `SMTP_PORT`       | `int`  | `587`   | ❌            | Porta SMTP                                      |
| `SMTP_USER`       | `str`  | `None`  | ❌            | Username per autenticazione SMTP                |
| `SMTP_PASSWORD`   | `str`  | `None`  | ❌            | Password per autenticazione SMTP                |
| `SMTP_FROM_EMAIL` | `str`  | `None`  | ❌            | Indirizzo mittente (fallback su `SMTP_USER`)    |
| `SMTP_TLS`        | `bool` | `True`  | ❌            | Abilita STARTTLS                                |

Se `SMTP_HOST` non è configurato, le email di verifica **non vengono inviate** e il link di verifica viene loggato
nella console del backend. Questo permette di lavorare in sviluppo locale senza un server SMTP.

### Frontend URL

| Variabile      | Tipo  | Default                 | Obbligatoria | Descrizione                                                   |
|----------------|-------|-------------------------|--------------|---------------------------------------------------------------|
| `FRONTEND_URL` | `str` | `http://localhost:5173` | ❌            | URL base del frontend, usato per costruire i link nelle email |

Deve corrispondere all'URL effettivo del frontend. In produzione sarà `https://polibench.example.com`.

### Mongo Express (pannello web MongoDB)

| Variabile                | Tipo  | Default | Obbligatoria | Descrizione                           |
|--------------------------|-------|---------|--------------|---------------------------------------|
| `MONGO_EXPRESS_USER`     | `str` | `admin` | ❌            | Username per accedere a Mongo Express |
| `MONGO_EXPRESS_PASSWORD` | `str` | `admin` | ❌            | Password per accedere a Mongo Express |

Queste variabili configurano la Basic Auth del pannello web Mongo Express. In produzione **devono essere
cambiate** con credenziali sicure.

---

## Logging

La configurazione del logging è in `backend/app/config/logging.py`. Usa il formato standard Python
`logging.config.dictConfig`:

- **Formatter**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Handler**: `StreamHandler` su stderr
- **Root logger**: livello `INFO`

La funzione `setup_loggers()` può essere chiamata all'avvio per attivare la configurazione.

---

## File .env.example

Il repository include un file `.env.example` con i nomi di tutte le variabili e valori di esempio. Il file `.env` reale
è escluso dal version control tramite `.gitignore`. Per configurare un nuovo ambiente:

```bash
cp .env.example .env
# editare .env con i valori reali
```

