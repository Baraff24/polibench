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
name: Amazon
versions:
  - v1
latest_version: v1
citation: "Synthetic citation"
""".strip(),
        "version_yaml_raw": """
dataset_name: Amazon
version: v1
sources:
  - name: source-main
    source_type: url
    downloadable: true
    url: https://example.org/amazon-v1.zip
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

    get_nested = await client.get(
        f"{API}/dataset-versions/{version_uuid}/sources-with-resources"
    )
    assert get_nested.status_code == 200
    nested = get_nested.json()
    assert len(nested) == 1
    assert nested[0]["name"] == "source-main"
    assert len(nested[0]["resources"]) == 1
    assert nested[0]["resources"][0]["name"] == "interactions"

    list_pipelines = await client.get(f"{API}/dataset-versions/{version_uuid}/pipelines")
    assert list_pipelines.status_code == 200
    pipelines = list_pipelines.json()
    assert len(pipelines) >= 1
    pipeline_uuid = pipelines[0]["uuid"]

    get_version_yaml = await client.get(
        f"{API}/dataset-versions/{version_uuid}/yaml/version"
    )
    assert get_version_yaml.status_code == 200
    assert "source-main" in get_version_yaml.json()["content"]

    get_metrics_yaml = await client.get(
        f"{API}/dataset-versions/{version_uuid}/yaml/metrics"
    )
    assert get_metrics_yaml.status_code == 200

    get_pipeline = await client.get(f"{API}/pipelines/{pipeline_uuid}")
    assert get_pipeline.status_code == 200
    assert get_pipeline.json()["code"] == "P001"
    assert len(get_pipeline.json()["blocks"]) == 1

    get_pipeline_yaml = await client.get(f"{API}/pipelines/{pipeline_uuid}/yaml")
    assert get_pipeline_yaml.status_code == 200
    assert "parse_csv" in get_pipeline_yaml.json()["content"]


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
        json={
            "version": "v1",
            "status": "ready",
            "pipeline_yaml_raw": """
pipeline:
  - name: parse
    operation: parse_csv
""".strip(),
        },
        headers=superuser_token_headers,
    )
    assert version_resp.status_code == 200
    version_uuid = version_resp.json()["uuid"]
    pipelines_resp = await client.get(f"{API}/dataset-versions/{version_uuid}/pipelines")
    assert pipelines_resp.status_code == 200
    pipeline_uuid = pipelines_resp.json()[0]["uuid"]

    model_resp = await client.post(
        f"{API}/ml-models",
        json={"name": "Version-Experiments-Model"},
        headers=superuser_token_headers,
    )
    assert model_resp.status_code == 200
    model_uuid = model_resp.json()["uuid"]

    exp_resp = await client.post(
        f"{API}/experiments",
        json={"pipeline_uuid": pipeline_uuid, "model_uuid": model_uuid},
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
    assert rows[0]["pipeline_uuid"] == pipeline_uuid
    assert rows[0]["model_uuid"] == model_uuid
    assert rows[0]["model_name"] == "Version-Experiments-Model"


@pytest.mark.anyio
async def test_preview_dataset_version_payload(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "Preview-DS", "task": "ranking"},
        headers=superuser_token_headers,
    )
    assert ds_resp.status_code == 200
    dataset_uuid = ds_resp.json()["uuid"]

    preview_payload = {
        "version": "v2",
        "status": "ready",
        "dataset_yaml_raw": """
name: Preview-DS
versions: [v1, v2]
latest_version: v2
""".strip(),
        "version_yaml_raw": """
dataset_name: Preview-DS
version: v2
sources:
  - name: source-main
    source_type: url
    downloadable: true
    url: https://example.org/preview-v2.zip
resources:
  - name: interactions
    source_name: source-main
    type: interactions
""".strip(),
        "pipeline_yaml_raw": """
pipeline:
  - name: parse
    operation: parse_csv
  - name: split
    operation: leave_one_out
""".strip(),
        "characteristics_yaml_raw": """
dataset_name: Preview-DS
version: v2
characteristics:
  n_users: 150
  n_items: 90
  n_interactions: 2000
  density: 0.14
""".strip(),
    }

    preview_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions/preview",
        json=preview_payload,
        headers=superuser_token_headers,
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["dataset_uuid"] == dataset_uuid
    assert preview["recognized_dataset_name"] == "Preview-DS"
    assert preview["recognized_version"] == "v2"
    assert preview["source_count"] == 1
    assert preview["resource_count"] == 1
    assert preview["pipeline_steps_count"] == 2
    assert preview["characteristics"]["n_users"] == 150


@pytest.mark.anyio
async def test_create_dataset_version_accepts_datarec_dict_yaml_shape(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "AmazonBooks", "task": "rating_prediction"},
        headers=superuser_token_headers,
    )
    assert ds_resp.status_code == 200
    dataset_uuid = ds_resp.json()["uuid"]

    version_payload = {
        "version": "2023",
        "status": "ready",
        "dataset_yaml_raw": """
dataset_name: Amazon Books
versions: ["2023"]
latest_version: "2023"
""".strip(),
        "version_yaml_raw": """
dataset_name: AmazonBooks
version: "2023"
sources:
  ratings:
    source_type: HttpSource
    args:
      downloadable: true
      url: https://example.org/books.csv.gz
      filename: books.csv.gz
resources:
  ratings:
    source_name: ratings
    filename: books.csv
    type: interactions
    format: transactions_tabular
    required: true
""".strip(),
        "characteristics_yaml_raw": """
dataset: amazon_books
version: "2023"
characteristics:
  n_users: 100
  n_items: 50
  n_interactions: 500
  density: 0.1
  gini_user: 0.5
  gini_item: 0.6
""".strip(),
        "pipeline_yaml_raw": """
pipeline:
  - name: parse
    operation: parse_csv
""".strip(),
    }
    resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json=version_payload,
        headers=superuser_token_headers,
    )
    assert resp.status_code == 200
    version_uuid = resp.json()["uuid"]
    assert resp.json()["n_users"] == 100

    nested = await client.get(
        f"{API}/dataset-versions/{version_uuid}/sources-with-resources"
    )
    assert nested.status_code == 200
    payload = nested.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "ratings"
    assert payload[0]["downloadable"] is True
    assert payload[0]["url"] == "https://example.org/books.csv.gz"
    assert len(payload[0]["resources"]) == 1
    assert payload[0]["resources"][0]["name"] == "ratings"
    assert payload[0]["resources"][0]["type"] == "interactions"


@pytest.mark.anyio
async def test_dataset_version_validation_blocks_invalid_source_and_consistency(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "Strict-DS", "task": "ranking"},
        headers=superuser_token_headers,
    )
    assert ds_resp.status_code == 200
    dataset_uuid = ds_resp.json()["uuid"]

    invalid_payload = {
        "version": "v1",
        "status": "ready",
        "version_yaml_raw": """
dataset_name: Other-DS
version: v1
sources:
  - name: source-main
    source_type: url
    downloadable: true
resources:
  - name: interactions
    source_name: source-main
    type: interactions
""".strip(),
    }
    invalid_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json=invalid_payload,
        headers=superuser_token_headers,
    )
    assert invalid_resp.status_code == 422
    assert "version_yaml_raw non coerente" in invalid_resp.json()["detail"]

    invalid_downloadable_payload = {
        "version": "v1",
        "status": "ready",
        "version_yaml_raw": """
dataset_name: Strict-DS
version: v1
sources:
  - name: source-main
    source_type: url
    downloadable: true
resources:
  - name: interactions
    source_name: source-main
    type: interactions
""".strip(),
    }
    invalid_downloadable_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json=invalid_downloadable_payload,
        headers=superuser_token_headers,
    )
    assert invalid_downloadable_resp.status_code == 422
    assert "url obbligatorio" in invalid_downloadable_resp.json()["detail"]

    invalid_source_payload = {
        "version": "v2",
        "status": "ready",
        "version_yaml_raw": """
dataset_name: Strict-DS
version: v2
sources:
  - name: source-main
    source_type: url
    downloadable: true
    url: https://example.org/strict.zip
resources:
  - name: interactions
    source_name: missing-source
    type: interactions
""".strip(),
    }
    invalid_source_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json=invalid_source_payload,
        headers=superuser_token_headers,
    )
    assert invalid_source_resp.status_code == 422
    assert "source_name='missing-source'" in invalid_source_resp.json()["detail"]


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
