# Strategia di Test

## Panoramica

La suite di test del backend si trova in `backend/tests/`. È divisa in due categorie principali con responsabilità
distinte:

```
tests/
├── conftest.py          ← fixture condivise da tutti i test
├── db/                  ← smoke test di database (in-memory)
│   ├── test_create_entities.py
│   ├── test_leaderboard.py
│   └── test_experiment_detail.py
└── routers/             ← test HTTP degli endpoint
    ├── test_login.py
    └── test_users.py
```

---

## conftest.py — Fixture condivise

Le fixture pytest sono definite in un unico `conftest.py` condiviso da tutti i test. pytest carica automaticamente
questo file per qualsiasi test nella cartella `tests/` e nelle sue sottocartelle.

### Fixture `anyio_backend`

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"
```

Dice ad anyio (il backend asincrono usato da pytest per i test `async`) di usare `asyncio`. Questa fixture è necessaria
perché FastAPI e Beanie sono basati su asyncio.

### Fixture `client`

```python
@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    @asynccontextmanager
    async def mock_lifespan(app: FastAPI):
        await _bootstrap_mock_db(app)
        yield
        # teardown: svuota le collezioni dopo ogni test
        db = app.state.client[MONGO_TEST_DB]
        for col in await db.list_collection_names():
            await db[col].delete_many({})

    test_app = FastAPI(lifespan=mock_lifespan, ...)
    test_app.include_router(api_router, prefix=settings.API_V1_STR)

    async with LifespanManager(test_app):
        async with AsyncClient(transport=ASGITransport(app=test_app), ...) as ac:
            yield ac
```

Questa fixture costruisce una **`test_app` FastAPI separata** (non l'app globale di `main.py`) con un lifespan mock.
Questo è fondamentale: il lifespan di `main.py` usa `AsyncIOMotorClient` che tenta una connessione TCP a MongoDB.
Senza Docker attivo, va in timeout dopo 5 secondi — bloccando tutti i test.

Il lifespan mock (`mock_lifespan`) chiama `_bootstrap_mock_db` che:

1. Crea un `AsyncMongoMockClient()` (MongoDB completamente in-memory)
2. Inizializza Beanie su quel client
3. Crea il superuser di test se non esiste

Nel teardown (dopo `yield`), svuota tutte le collezioni per isolare il test successivo.

**Nessun Docker necessario**: tutta la suite gira in-memory, sia per i test DB che per i test router.

### Fixture `superuser_token_headers`

```python
@pytest.fixture()
async def superuser_token_headers(client: AsyncClient) -> dict[str, str]:
    return await get_user_auth_headers(
        client, settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )
```

Restituisce gli header HTTP con il token JWT del superutente, pronti per essere passati al client in richieste che
richiedono autenticazione admin.

### Fixture `db`

```python
@pytest.fixture()
async def db():
    mock_client = AsyncMongoMockClient()
    await init_beanie(
        database=mock_client["polibench_test"],
        document_models=DOCUMENT_MODELS,
    )
    yield
    await mock_client.drop_database("polibench_test")
```

Questa fixture crea un database **MongoDB completamente in-memory** usando `mongomock-motor`. Non richiede alcun server
MongoDB attivo. È usata esclusivamente dagli smoke test di database (`tests/db/`).

Il pattern `yield` è il teardown di pytest: tutto ciò che viene dopo `yield` viene eseguito dopo il test. In questo
caso, il database in-memory viene cancellato, garantendo isolamento tra i test.

**Differenza con `client`**: `db` non avvia alcun server HTTP — è solo Beanie in-memory. Usala quando vuoi testare
query di database direttamente senza passare dal layer HTTP.

---

## Smoke test di database (`tests/db/`)

### Cosa sono gli smoke test

Il termine "smoke test" viene dall'elettronica: quando si monta un nuovo circuito, lo si accende per verificare che
non "fumi" (non si rompa immediatamente). In software, uno smoke test verifica che le funzionalità fondamentali
funzionino a livello basilare, **prima** di testare casi limite o comportamenti complessi.

Gli smoke test di database verificano che:

- i modelli Beanie possano essere salvati e riletti da MongoDB
- le query fondamentali del sistema producano risultati corretti
- i filtri funzionino correttamente (isolamento tra entità diverse)

Se uno smoke test fallisce, non ha senso procedere con test più elaborati: le fondamenta del sistema non reggono.

### Test A — Creazione entità (`test_create_entities.py`)

Verifica il ciclo di vita base di ogni entità: istanziazione → salvataggio → lettura → confronto valori.

**`test_create_dataset`**: crea un `Dataset` con `Splits`, lo salva, lo rilegge con `.get(id)` e verifica che tutti i
campi (incluso il sotto-documento `Splits`) siano stati serializzati e deserializzati correttamente.

**`test_create_ml_model`**: crea un `MLModel` con `hyperparams: dict[str, Any]` e verifica il round-trip del dizionario.

**`test_create_experiment`**: crea un `Experiment` collegato a un `Dataset` e un `MLModel` tramite ObjectId. Verifica
che le FK siano state salvate correttamente e che `training_config: dict[str, Any]` sopravviva al round-trip.

**`test_create_metrics`**: crea 3 `Metric` (stessa metrica su split diversi + metrica diversa) e verifica che tutte e
tre siano recuperabili con `.find(Metric.experiment_id == experiment.id).to_list()`.

### Test B — Query leaderboard (`test_leaderboard.py`)

**`test_leaderboard_top_n_ordered`**: crea 3 modelli con punteggi `ndcg@10` intenzionalmente fuori ordine (iALS=0.3990,
EASE=0.4512, MultiVAE=0.4801) e verifica che la query:

```python
await Metric.find(
    Metric.dataset_id == dataset.id,
    Metric.split == Split.TEST,
    Metric.metric == "ndcg@10",
).sort(-Metric.value).limit(3).to_list()
```

restituisca i modelli nell'ordine corretto (MultiVAE → EASE → iALS).

Il test usa `pytest.approx()` per il confronto di valori float, evitando problemi di precisione numerica.

**`test_leaderboard_filters_by_split`**: verifica che le metriche `VALIDATION` non compaiano nella query filtrata per
`TEST`.

### Test C — Dettaglio esperimento (`test_experiment_detail.py`)

**`test_experiment_detail_returns_own_metrics`**: crea due `Experiment` sullo stesso dataset, aggiunge 4 metriche al
primo e 2 al secondo, poi verifica che la query:

```python
await Metric.find(Metric.experiment_id == exp_target.id).to_list()
```

restituisca esattamente 4 metriche (solo quelle dell'experiment target, non le 2 dell'altro). Questo test verifica l'*
*isolamento** dei dati: una query rotta che non filtra potrebbe restituire tutte le 6 metriche.

---

## Test HTTP dei router (`tests/routers/`)

I test dei router testano il comportamento degli endpoint HTTP usando il client `httpx.AsyncClient` configurato dalla
fixture `client`. Questi test richiedono un MongoDB reale attivo (normalmente tramite Docker Compose).

### test_login.py

- **`test_get_access_token`**: verifica che `POST /login/access-token` con le credenziali del superutente restituisca un
  token JWT valido
- **`test_use_access_token`**: verifica che il token ottenuto permetta di chiamare `GET /login/test-token` con successo
- **`test_not_authorized`**: verifica che una chiamata senza token riceva HTTP 401

### test_users.py

Testa il CRUD completo degli utenti: registrazione, lettura profilo, aggiornamento, cancellazione, operazioni admin. Usa
la fixture `superuser_token_headers` per le operazioni che richiedono privilegi elevati.

---

## Esecuzione dei test

```bash
# Solo gli smoke test di database (non richiede Docker)
cd backend
uv run pytest tests/db/ -v

# Solo i test dei router (richiede MongoDB attivo)
cd backend
uv run pytest tests/routers/ -v

# Tutti i test
cd backend
uv run pytest -v

# Con copertura del codice
cd backend
uv run pytest --cov=app --cov-report=html
```

---

## Tecnologie di test

| Tool                | Versione     | Scopo                                                 |
|---------------------|--------------|-------------------------------------------------------|
| **pytest**          | `>=8.3.5`    | Framework principale                                  |
| **anyio**           | (transitiva) | Esecuzione di test `async def` con asyncio            |
| **httpx**           | `>=0.28.1`   | Client HTTP asincrono per test endpoint               |
| **asgi-lifespan**   | `>=2.1.0`    | Avvia il lifespan FastAPI nei test senza server reale |
| **mongomock-motor** | `>=0.0.34`   | MongoDB in-memory per smoke test DB                   |
| **pytest-cov**      | `>=6.1.1`    | Report di copertura del codice                        |

