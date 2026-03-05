"""
tests/routers_v2/test_datasets.py
===================================
Test API end-to-end per Dataset e MLModel.

Questi test verificano:
- routing HTTP (status code, path)
- autenticazione (401 se non autenticati)
- schema della risposta (campi presenti, UUID come identificatori)
- comportamento POST → GET (creazione e lettura)

Usano la fixture `client` (httpx + mongomock in-memory) e
`superuser_token_headers` definite in tests/conftest.py.
"""

import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


@pytest.mark.anyio
async def test_create_dataset_requires_auth(client: AsyncClient) -> None:
    """POST /datasets senza token → 401."""
    resp = await client.post(
        f"{API}/datasets",
        json={"name": "ML-1M", "version": "1.0", "task": "ranking"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_create_and_list_dataset(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """
    POST /datasets → 200, risposta contiene uuid (non _id).
    GET /datasets  → lista con almeno il dataset appena creato.
    """
    payload = {
        "name": "MovieLens-1M",
        "version": "1.0",
        "task": "ranking",
        "description": "Dataset test",
        "visibility": "public",
    }
    resp = await client.post(
        f"{API}/datasets",
        json=payload,
        headers=superuser_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # Il contratto UUID-first: uuid presente, _id mai esposto
    assert "uuid" in data
    assert "_id" not in data
    assert data["name"] == "MovieLens-1M"
    assert data["task"] == "ranking"

    # GET lista
    resp = await client.get(f"{API}/datasets")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    uuids = [i["uuid"] for i in items]
    assert data["uuid"] in uuids


@pytest.mark.anyio
async def test_get_dataset_by_uuid(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """POST /datasets poi GET /datasets/{uuid} → stesso oggetto."""
    payload = {"name": "Amazon", "version": "2.0", "task": "rating_prediction"}
    create_resp = await client.post(
        f"{API}/datasets",
        json=payload,
        headers=superuser_token_headers,
    )
    assert create_resp.status_code == 200
    created_uuid = create_resp.json()["uuid"]

    get_resp = await client.get(f"{API}/datasets/{created_uuid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["uuid"] == created_uuid
    assert get_resp.json()["name"] == "Amazon"


@pytest.mark.anyio
async def test_get_dataset_not_found(client: AsyncClient) -> None:
    """GET /datasets/{uuid_inesistente} → 404."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"{API}/datasets/{fake_uuid}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_and_list_ml_model(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """POST /ml-models → 200 con uuid. GET /ml-models → lista."""
    payload = {
        "name": "BPR-MF",
        "family": "matrix_factorization",
        "paper_url": "https://arxiv.org/abs/1205.2618",
    }
    resp = await client.post(
        f"{API}/ml-models",
        json=payload,
        headers=superuser_token_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "uuid" in data
    assert "_id" not in data
    assert data["name"] == "BPR-MF"
    assert data["family"] == "matrix_factorization"

    resp = await client.get(f"{API}/ml-models")
    assert resp.status_code == 200
    assert any(m["uuid"] == data["uuid"] for m in resp.json())
