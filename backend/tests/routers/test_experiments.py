import asyncio

import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


async def _create_dataset(client, headers) -> str:
    resp = await client.post(
        f"{API}/datasets",
        json={"name": "TestDS", "task": "ranking"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["uuid"]


async def _create_dataset_version(client, headers, dataset_uuid: str) -> str:
    resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json={"version": "1.0", "status": "ready"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["uuid"]


async def _create_model(client, headers, name: str = "BPR-MF") -> str:
    resp = await client.post(
        f"{API}/ml-models",
        json={"name": name, "family": "matrix_factorization"},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()["uuid"]


@pytest.mark.anyio
async def test_submit_experiment_and_metrics_then_get_detail(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid = await _create_dataset(client, superuser_token_headers)
    dataset_version_uuid = await _create_dataset_version(
        client,
        superuser_token_headers,
        dataset_uuid,
    )
    model_uuid = await _create_model(client, superuser_token_headers)

    exp_resp = await client.post(
        f"{API}/experiments",
        json={
            "dataset_version_uuid": dataset_version_uuid,
            "model_uuid": model_uuid,
            "run_name": "run-001",
            "seed": 42,
            "training_config": {"factors": 64, "lr": 0.01},
        },
        headers=superuser_token_headers,
    )
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()

    assert "uuid" in exp_data
    assert "_id" not in exp_data
    assert exp_data["dataset_uuid"] == dataset_uuid
    assert exp_data["dataset_version_uuid"] == dataset_version_uuid
    assert exp_data["model_uuid"] == model_uuid
    assert exp_data["status"] == "queued"
    experiment_uuid = exp_data["uuid"]

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
    assert metrics_data["experiment_uuid"] == experiment_uuid
    assert len(metrics_data["metrics_by_split"]["test"]) == 2

    get_resp = await client.get(f"{API}/experiments/{experiment_uuid}/metrics")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["experiment_uuid"] == experiment_uuid
    assert len(get_data["metrics_by_split"]["test"]) == 2
    assert (
        get_data["metrics_by_split"]["test"][0]["dataset_version_uuid"]
        == dataset_version_uuid
    )


@pytest.mark.anyio
async def test_metric_import_csv_flow(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid = await _create_dataset(client, superuser_token_headers)
    dataset_version_uuid = await _create_dataset_version(
        client,
        superuser_token_headers,
        dataset_uuid,
    )
    model_uuid = await _create_model(client, superuser_token_headers, name="LightGCN")

    create_resp = await client.post(
        f"{API}/experiments",
        json={"dataset_version_uuid": dataset_version_uuid, "model_uuid": model_uuid},
        headers=superuser_token_headers,
    )
    assert create_resp.status_code == 200
    exp_uuid = create_resp.json()["uuid"]

    csv_content = (
        "split,metric,k,value,direction\n"
        "test,ndcg@10,10,0.44,max\n"
        "validation,ndcg@10,10,0.41,max\n"
    )
    import_resp = await client.post(
        f"{API}/experiments/{exp_uuid}/metric-import",
        files={"file": ("metrics.csv", csv_content, "text/csv")},
        headers=superuser_token_headers,
    )
    assert import_resp.status_code == 200
    assert import_resp.json()["status"] in {"queued", "processing", "completed"}

    # Allow background task to complete in tests.
    await asyncio.sleep(0.05)

    jobs_resp = await client.get(
        f"{API}/experiments/{exp_uuid}/metric-imports",
        headers=superuser_token_headers,
    )
    assert jobs_resp.status_code == 200
    assert len(jobs_resp.json()) >= 1

    metrics_resp = await client.get(f"{API}/experiments/{exp_uuid}/metrics")
    assert metrics_resp.status_code == 200
    by_split = metrics_resp.json()["metrics_by_split"]
    assert "test" in by_split
    assert by_split["test"][0]["dataset_version_uuid"] == dataset_version_uuid


@pytest.mark.anyio
async def test_get_experiment_public(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid = await _create_dataset(client, superuser_token_headers)
    dataset_version_uuid = await _create_dataset_version(
        client,
        superuser_token_headers,
        dataset_uuid,
    )
    model_uuid = await _create_model(client, superuser_token_headers, name="EASE")

    create_resp = await client.post(
        f"{API}/experiments",
        json={"dataset_version_uuid": dataset_version_uuid, "model_uuid": model_uuid},
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
    assert data["dataset_version_uuid"] == dataset_version_uuid
    assert data["model_uuid"] == model_uuid
    assert "_id" not in data


@pytest.mark.anyio
async def test_submit_experiment_invalid_dataset_version_uuid(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    model_uuid = await _create_model(client, superuser_token_headers, name="SASRec")

    resp = await client.post(
        f"{API}/experiments",
        json={"dataset_version_uuid": fake_uuid, "model_uuid": model_uuid},
        headers=superuser_token_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_submit_experiment_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/experiments",
        json={
            "dataset_version_uuid": "00000000-0000-0000-0000-000000000001",
            "model_uuid": "00000000-0000-0000-0000-000000000002",
        },
    )
    assert resp.status_code == 401
