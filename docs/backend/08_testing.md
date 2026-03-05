# Strategia di Test

## Panoramica

La suite di test del backend si trova in `backend/tests/`. È divisa in due categorie principali con responsabilità
distinte:

```
tests/
├── conftest.py                  ← fixture condivise da tutti i test
├── db/                          ← smoke test di database (in-memory)
│   ├── test_create_entities.py
│   ├── test_leaderboard.py
│   └── test_experiment_detail.py
└── routers/                     ← test HTTP degli endpoint
    ├── test_login.py
    ├── test_users.py
    ├── test_datasets.py         ← Dataset e MLModel (POST/GET)
    ├── test_experiments.py      ← Experiment + batch metrics (vertical slice)
    └── test_leaderboard.py      ← leaderboard (sort, filter by split, empty)
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
fixture `client`. Tutti i test girano **in-memory** grazie a `mongomock-motor`: non è necessario Docker attivo.

### test_login.py

- **`test_get_access_token`**: verifica che `POST /login/access-token` con le credenziali del superutente restituisca un
  token JWT valido
- **`test_use_access_token`**: verifica che il token ottenuto permetta di chiamare `GET /login/test-token` con successo
- **`test_not_authorized`**: verifica che una chiamata senza token riceva HTTP 401

### test_users.py

Testa il CRUD completo degli utenti: registrazione, lettura profilo, aggiornamento, cancellazione, operazioni admin. Usa
la fixture `superuser_token_headers` per le operazioni che richiedono privilegi elevati.

### test_datasets.py

Testa gli endpoint Dataset e MLModel.

- **`test_create_dataset_requires_auth`**: `POST /datasets` senza token → 401 (verifica autenticazione)
- **`test_create_and_list_dataset`**: crea un Dataset, verifica che la risposta contenga `uuid` e non `_id`
  (UUID-first), poi verifica che `GET /datasets` includa il dataset appena creato
- **`test_get_dataset_by_uuid`**: `POST /datasets` poi `GET /datasets/{uuid}` → stesso oggetto, stesso UUID
- **`test_get_dataset_not_found`**: UUID inesistente → 404
- Test analoghi per `ml-models`: creazione, listing, dettaglio per UUID

### test_experiments.py

Testa la vertical slice completa della submission.

- **`test_submit_experiment_and_metrics_then_get_detail`**: test principale end-to-end:
    1. crea Dataset e MLModel via HTTP
    2. `POST /experiments` con `dataset_uuid` e `model_uuid` → verifica schema UUID-first, `status=queued`
    3. `POST /experiments/{uuid}/metrics` con lista di `MetricCreate` → verifica `ExperimentMetrics` con
       `metrics_by_split` correttamente popolato (2 test, 1 validation)
    4. `GET /experiments/{uuid}/metrics` → stesso risultato
- **`test_get_experiment_public`**: `POST` poi `GET /experiments/{uuid}` → verifica che `dataset_uuid` e `model_uuid`
  siano quelli inviati (risoluzione UUID→ObjectId→UUID andata e ritorno)
- **`test_submit_experiment_invalid_dataset_uuid`**: `dataset_uuid` inesistente → 404
- **`test_submit_experiment_requires_auth`**: senza token → 401

### test_leaderboard.py

Testa l'endpoint `GET /leaderboard` replicando i test DB ma passando per HTTP.

- **`test_leaderboard_top_n_sorted`**: crea 3 modelli con punteggi fuori ordine (`iALS=0.3990`, `EASE=0.4512`,
  `MultiVAE=0.4801`), verifica che la risposta sia ordinata per `value DESC` (`MultiVAE → EASE → iALS`) e che `rank`
  sia progressivo (1, 2, 3)
- **`test_leaderboard_filters_by_split`**: verifica che le metriche `validation` non compaiano nella query filtrata
  per `test` — isola i dati tra split diversi
- **`test_leaderboard_empty_for_unknown_metric`**: metrica inesistente → lista vuota `[]` (non errore 404)

---

## Esecuzione dei test

```bash
# Solo gli smoke test di database (in-memory)
cd backend
uv run pytest tests/db/ -v

# Solo i test dei router (in-memory, non richiede Docker)
cd backend
uv run pytest tests/routers/ -v

# Tutti i test (db + routers)
cd backend
uv run pytest -v

# Con copertura del codice
cd backend
uv run pytest --cov=app --cov-report=html
```

**Nessun Docker necessario**: l'intera suite (sia `tests/db/` che `tests/routers/`) usa `mongomock-motor`
e gira completamente in-memory.

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

