import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


@pytest.mark.anyio
async def test_create_dataset_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        f"{API}/datasets",
        json={"name": "ML-1M", "task": "ranking"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_create_and_list_dataset(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    payload = {
        "name": "MovieLens-1M",
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

    assert "uuid" in data
    assert "_id" not in data
    assert data["name"] == "MovieLens-1M"
    assert data["task"] == "ranking"
    assert data["versions_count"] == 0

    resp = await client.get(f"{API}/datasets")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    uuids = [i["uuid"] for i in items]
    assert data["uuid"] in uuids


@pytest.mark.anyio
async def test_create_and_list_dataset_versions(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "Amazon", "task": "rating_prediction"},
        headers=superuser_token_headers,
    )
    assert ds_resp.status_code == 200
    dataset_uuid = ds_resp.json()["uuid"]

    version_payload = {
        "version": "v1",
        "status": "ready",
        "dataset_yaml_raw": """
dataset_name: Amazon
version: v1
sources:
  - name: source-main
    source_type: url
    downloadable: true
resources:
  - name: interactions
    source_name: source-main
    type: interactions
    required: true
""".strip(),
        "pipeline_yaml_raw": """
pipeline:
  - name: parse
    operation: parse_csv
    params:
      sep: ","
""".strip(),
        "characteristics_yaml_raw": """
characteristics:
  n_users: 1200
  n_items: 450
  n_interactions: 50000
  density: 0.0926
""".strip(),
    }
    create_v = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json=version_payload,
        headers=superuser_token_headers,
    )
    assert create_v.status_code == 200
    version_uuid = create_v.json()["uuid"]
    assert create_v.json()["version"] == "v1"
    assert create_v.json()["n_users"] == 1200

    list_v = await client.get(f"{API}/datasets/{dataset_uuid}/versions")
    assert list_v.status_code == 200
    assert len(list_v.json()) == 1
    assert list_v.json()[0]["uuid"] == version_uuid

    get_v = await client.get(f"{API}/dataset-versions/{version_uuid}")
    assert get_v.status_code == 200
    assert get_v.json()["dataset_uuid"] == dataset_uuid

    get_sources = await client.get(f"{API}/dataset-versions/{version_uuid}/sources")
    assert get_sources.status_code == 200
    assert len(get_sources.json()) == 1

    get_resources = await client.get(f"{API}/dataset-versions/{version_uuid}/resources")
    assert get_resources.status_code == 200
    assert len(get_resources.json()) == 1

    get_pipeline = await client.get(f"{API}/dataset-versions/{version_uuid}/pipeline")
    assert get_pipeline.status_code == 200
    assert len(get_pipeline.json()["blocks"]) == 1


@pytest.mark.anyio
async def test_list_experiments_for_dataset_version(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "Version-Experiments-DS", "task": "ranking"},
        headers=superuser_token_headers,
    )
    assert ds_resp.status_code == 200
    dataset_uuid = ds_resp.json()["uuid"]

    version_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json={"version": "v1", "status": "ready"},
        headers=superuser_token_headers,
    )
    assert version_resp.status_code == 200
    version_uuid = version_resp.json()["uuid"]

    model_resp = await client.post(
        f"{API}/ml-models",
        json={"name": "Version-Experiments-Model"},
        headers=superuser_token_headers,
    )
    assert model_resp.status_code == 200
    model_uuid = model_resp.json()["uuid"]

    exp_resp = await client.post(
        f"{API}/experiments",
        json={"dataset_version_uuid": version_uuid, "model_uuid": model_uuid},
        headers=superuser_token_headers,
    )
    assert exp_resp.status_code == 200
    exp_uuid = exp_resp.json()["uuid"]

    list_resp = await client.get(f"{API}/dataset-versions/{version_uuid}/experiments")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    assert rows[0]["uuid"] == exp_uuid
    assert rows[0]["dataset_uuid"] == dataset_uuid
    assert rows[0]["dataset_version_uuid"] == version_uuid
    assert rows[0]["model_uuid"] == model_uuid
    assert rows[0]["model_name"] == "Version-Experiments-Model"


@pytest.mark.anyio
async def test_get_dataset_not_found(client: AsyncClient) -> None:
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"{API}/datasets/{fake_uuid}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_create_and_list_ml_model(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
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
