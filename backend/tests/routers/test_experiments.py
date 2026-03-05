"""
tests/routers_v2/test_experiments.py
======================================
Test API end-to-end per Experiment e Metric submission.

Test 1 — submit_experiment_and_metrics_then_get_detail:
    Verifica la vertical slice completa:
    POST /datasets → POST /ml-models → POST /experiments →
    POST /experiments/{uuid}/metrics → GET /experiments/{uuid}/metrics

Test 2 — submit_experiment_resolves_uuid:
    Verifica che il router risolva correttamente dataset_uuid e model_uuid
    in ObjectId interni, e che la response contenga solo UUID.

Test 3 — submit_experiment_with_invalid_dataset_uuid:
    Verifica che un UUID inesistente restituisca 404.
"""

import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_dataset(client, headers) -> str:
    """Crea un dataset e ritorna il suo uuid."""
    resp = await client.post(
        f"{API}/datasets",
        json={"name": "TestDS", "version": "1.0", "task": "ranking"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["uuid"]


async def _create_model(client, headers, name: str = "BPR-MF") -> str:
    """Crea un modello e ritorna il suo uuid."""
    resp = await client.post(
        f"{API}/ml-models",
        json={"name": name, "family": "matrix_factorization"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["uuid"]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_submit_experiment_and_metrics_then_get_detail(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """
    Vertical slice completa:
    1. Crea Dataset e MLModel
    2. Sottomette un Experiment (input con UUID)
    3. Sottomette le metriche in batch
    4. Legge il dettaglio delle metriche raggruppate per split
    5. Verifica schema UUID-first in ogni risposta
    """
    # Setup
    dataset_uuid = await _create_dataset(client, superuser_token_headers)
    model_uuid = await _create_model(client, superuser_token_headers)

    # POST /experiments
    exp_resp = await client.post(
        f"{API}/experiments",
        json={
            "dataset_uuid": dataset_uuid,
            "model_uuid": model_uuid,
            "run_name": "run-001",
            "seed": 42,
            "training_config": {"factors": 64, "lr": 0.01},
        },
        headers=superuser_token_headers,
    )
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()

    # Schema UUID-first: uuid presente, _id mai esposto
    assert "uuid" in exp_data
    assert "_id" not in exp_data
    assert exp_data["dataset_uuid"] == dataset_uuid
    assert exp_data["model_uuid"] == model_uuid
    assert exp_data["status"] == "queued"
    assert exp_data["run_name"] == "run-001"

    experiment_uuid = exp_data["uuid"]

    # POST /experiments/{uuid}/metrics
    metrics_resp = await client.post(
        f"{API}/experiments/{experiment_uuid}/metrics",
        json={
            "experiment_uuid": experiment_uuid,
            "metrics": [
                {
                    "split": "test",
                    "metric": "ndcg@10",
                    "k": 10,
                    "value": 0.4512,
                    "direction": "max",
                },
                {
                    "split": "test",
                    "metric": "recall@20",
                    "k": 20,
                    "value": 0.3201,
                    "direction": "max",
                },
                {
                    "split": "validation",
                    "metric": "ndcg@10",
                    "k": 10,
                    "value": 0.4380,
                    "direction": "max",
                },
            ],
        },
        headers=superuser_token_headers,
    )
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()

    # ExperimentMetrics: experiment_uuid + metrics_by_split
    assert metrics_data["experiment_uuid"] == experiment_uuid
    assert "metrics_by_split" in metrics_data
    by_split = metrics_data["metrics_by_split"]

    # 2 metriche su test, 1 su validation
    assert "test" in by_split
    assert "validation" in by_split
    assert len(by_split["test"]) == 2
    assert len(by_split["validation"]) == 1

    # Ogni metrica ha uuid ma non _id
    for m in by_split["test"]:
        assert "uuid" in m
        assert "_id" not in m
        assert m["experiment_uuid"] == experiment_uuid

    # GET /experiments/{uuid}/metrics
    get_resp = await client.get(f"{API}/experiments/{experiment_uuid}/metrics")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["experiment_uuid"] == experiment_uuid
    assert len(get_data["metrics_by_split"]["test"]) == 2


@pytest.mark.anyio
async def test_get_experiment_public(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """
    POST /experiments poi GET /experiments/{uuid}:
    verifica che la risposta sia UUID-first e contenga i campi corretti.
    """
    dataset_uuid = await _create_dataset(client, superuser_token_headers)
    model_uuid = await _create_model(client, superuser_token_headers, name="LightGCN")

    create_resp = await client.post(
        f"{API}/experiments",
        json={"dataset_uuid": dataset_uuid, "model_uuid": model_uuid},
        headers=superuser_token_headers,
    )
    assert create_resp.status_code == 200
    exp_uuid = create_resp.json()["uuid"]

    get_resp = await client.get(
        f"{API}/experiments/{exp_uuid}",
        headers=superuser_token_headers,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["uuid"] == exp_uuid
    assert data["dataset_uuid"] == dataset_uuid
    assert data["model_uuid"] == model_uuid
    assert "_id" not in data


@pytest.mark.anyio
async def test_submit_experiment_invalid_dataset_uuid(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """dataset_uuid inesistente → 404."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    model_uuid = await _create_model(client, superuser_token_headers, name="EASE")

    resp = await client.post(
        f"{API}/experiments",
        json={"dataset_uuid": fake_uuid, "model_uuid": model_uuid},
        headers=superuser_token_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_submit_experiment_requires_auth(client: AsyncClient) -> None:
    """POST /experiments senza token → 401."""
    resp = await client.post(
        f"{API}/experiments",
        json={
            "dataset_uuid": "00000000-0000-0000-0000-000000000001",
            "model_uuid": "00000000-0000-0000-0000-000000000002",
        },
    )
    assert resp.status_code == 401
