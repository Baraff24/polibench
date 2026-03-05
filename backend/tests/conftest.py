from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from asgi_lifespan import LifespanManager
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.auth.auth import get_hashed_password
from app.config.config import settings
from app.models import DOCUMENT_MODELS, User
from app.routers.api import api_router

from .utils import get_user_auth_headers

MONGO_TEST_DB = "polibenchtest"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _bootstrap_mock_db(test_app: FastAPI) -> None:
    """
    Inizializza Beanie su un MongoDB in-memory (mongomock-motor)
    e crea il superuser necessario per i test autenticati.

    Perché non usiamo LifespanManager sull'app globale di main.py?
    Perché il suo lifespan usa AsyncIOMotorClient che tenta una
    connessione TCP reale a MongoDB — senza Docker attivo va in timeout.
    Qui costruiamo una test_app separata con un lifespan mock.
    """
    mock_motor = AsyncMongoMockClient()
    test_app.state.client = mock_motor
    await init_beanie(
        database=mock_motor[MONGO_TEST_DB],
        document_models=DOCUMENT_MODELS,
    )
    if not await User.find_one({"email": settings.FIRST_SUPERUSER}):
        await User(
            email=settings.FIRST_SUPERUSER,
            hashed_password=get_hashed_password(settings.FIRST_SUPERUSER_PASSWORD),
            is_superuser=True,
        ).create()


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Client HTTP asincrono per i test end-to-end dei router.

    Costruisce una test_app FastAPI fresca con:
    - lifespan mock (mongomock-motor, niente Docker)
    - tutti i router registrati tramite api_router
    - superuser creato automaticamente in startup
    - DB svuotato dopo ogni test per isolamento

    Differenza con la fixture `db`:
    - `db`     → solo Beanie in-memory, nessun layer HTTP
    - `client` → app ASGI completa + HTTP + Beanie in-memory
    """

    @asynccontextmanager
    async def mock_lifespan(app: FastAPI):
        await _bootstrap_mock_db(app)
        yield
        db = app.state.client[MONGO_TEST_DB]
        for col in await db.list_collection_names():
            await db[col].delete_many({})

    test_app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=mock_lifespan,
    )
    test_app.include_router(api_router, prefix=settings.API_V1_STR)

    async with LifespanManager(test_app):
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://test",
        ) as ac:
            yield ac


@pytest.fixture()
async def superuser_token_headers(client: AsyncClient) -> dict[str, str]:
    return await get_user_auth_headers(
        client, settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )


@pytest.fixture()
async def db():
    """
    DB MongoDB in-memory per gli smoke test di database (tests/db/).
    Usa mongomock-motor direttamente, senza HTTP.
    Ogni test parte da un DB vuoto e isolato.
    """
    mock_client = AsyncMongoMockClient()
    await init_beanie(
        database=mock_client["polibench_test"],
        document_models=DOCUMENT_MODELS,
    )
    yield
    await mock_client.drop_database("polibench_test")
