from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from asgi_lifespan import LifespanManager
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.config.config import settings
from app.main import app
from app.models import DOCUMENT_MODELS

from .utils import get_user_auth_headers

MONGO_TEST_DB = "polibenchtest"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def clear_database(server: FastAPI) -> None:
    test_db = server.state.client[MONGO_TEST_DB]
    collections = await test_db.list_collections()
    async for collection in collections:
        await test_db[collection["name"]].delete_many({})


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async server client che gestisce lifespan e teardown."""
    with patch("app.config.config.settings.MONGO_DB", MONGO_TEST_DB):
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                try:
                    yield client
                finally:
                    await clear_database(app)


@pytest.fixture()
async def superuser_token_headers(client: AsyncClient) -> dict[str, str]:
    return await get_user_auth_headers(
        client, settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )


@pytest.fixture()
async def db():
    """
    DB MongoDB in-memory per gli smoke test di database.

    Usa mongomock-motor: un'implementazione in-memory di Motor su cui
    Beanie funziona senza sapere la differenza. Niente Docker, niente
    server MongoDB attivo. Ogni test parte da un DB vuoto e isolato.

    Come funziona:
    - prima dello yield → crea il client e inizializza Beanie
    - yield            → il test gira qui
    - dopo lo yield    → cancella il DB così il prossimo test è pulito
    """
    mock_client = AsyncMongoMockClient()
    await init_beanie(
        database=mock_client["polibench_test"],
        document_models=DOCUMENT_MODELS,
    )
    yield
    await mock_client.drop_database("polibench_test")
