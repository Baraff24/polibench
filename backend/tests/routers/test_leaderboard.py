import pytest
from httpx import AsyncClient

from app.config.config import settings
from tests.utils import create_test_user, generate_user_auth_headers

API = settings.API_V1_STR


async def _setup_leaderboard(
    client,
    headers,
) -> tuple[str, str, str, list[str], dict[str, str]]:
    secondary_user = await create_test_user()
    secondary_headers = await generate_user_auth_headers(client, secondary_user)

    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "LB-Dataset", "task": "ranking"},
        headers=headers,
    )
    dataset_uuid = ds_resp.json()["uuid"]

    version_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json={
            "version": "1.0",
            "status": "ready",
            "pipeline_yaml_raw": """
pipeline:
  - name: parse
    operation: parse_csv
""".strip(),
        },
        headers=headers,
    )
    dataset_version_uuid = version_resp.json()["uuid"]
    pipelines_resp = await client.get(
        f"{API}/dataset-versions/{dataset_version_uuid}/pipelines"
    )
    assert pipelines_resp.status_code == 200
    pipeline_uuid = pipelines_resp.json()[0]["uuid"]

    scores = [
        (
            "iALS",
            0.3990,
            {"embedding_dim": 64, "learning_rate": 0.001, "batch_size": 256},
            headers,
        ),
        (
            "EASE",
            0.4512,
            {"embedding_dim": 128, "learning_rate": 0.0005, "batch_size": 512},
            secondary_headers,
        ),
        (
            "MultiVAE",
            0.4801,
            {"embedding_dim": 256, "learning_rate": 0.0008, "batch_size": 512},
            headers,
        ),
    ]

    exp_uuids = []
    for model_name, ndcg_value, training_config, submitter_headers in scores:
        m_resp = await client.post(
            f"{API}/ml-models",
            json={"name": model_name},
            headers=headers,
        )
        model_uuid = m_resp.json()["uuid"]

        e_resp = await client.post(
            f"{API}/experiments",
            json={
                "pipeline_uuid": pipeline_uuid,
                "model_uuid": model_uuid,
                "training_config": training_config,
            },
            headers=submitter_headers,
        )
        exp_uuid = e_resp.json()["uuid"]
        exp_uuids.append(exp_uuid)

        await client.post(
            f"{API}/experiments/{exp_uuid}/metrics",
            json={
                "experiment_uuid": exp_uuid,
                "metrics": [
                    {
                        "split": "test",
                        "metric": "ndcg@10",
                        "k": 10,
                        "value": ndcg_value,
                        "direction": "max",
                    },
                    {
                        "split": "validation",
                        "metric": "ndcg@10",
                        "k": 10,
                        "value": ndcg_value - 0.02,
                        "direction": "max",
                    },
                ],
            },
            headers=headers,
        )

    return dataset_uuid, dataset_version_uuid, pipeline_uuid, exp_uuids, {
        "secondary_user_uuid": str(secondary_user.uuid),
    }


@pytest.mark.anyio
async def test_leaderboard_top_n_sorted(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, pipeline_uuid, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "metric": "ndcg@10",
            "split": "test",
            "top_n": 10,
        },
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 3

    assert entries[0]["model_name"] == "MultiVAE"
    assert entries[1]["model_name"] == "EASE"
    assert entries[2]["model_name"] == "iALS"

    values = [e["value"] for e in entries]
    assert values == sorted(values, reverse=True)
    assert [e["rank"] for e in entries] == [1, 2, 3]

    for e in entries:
        assert e["dataset_uuid"] == dataset_uuid
        assert e["dataset_version_uuid"] == dataset_version_uuid
        assert e["pipeline_uuid"] == pipeline_uuid


@pytest.mark.anyio
async def test_leaderboard_filters_by_split(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, pipeline_uuid, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    test_resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "metric": "ndcg@10",
            "split": "test",
        },
    )
    val_resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "metric": "ndcg@10",
            "split": "validation",
        },
    )
    assert test_resp.status_code == 200
    assert val_resp.status_code == 200

    test_values = {e["value"] for e in test_resp.json()}
    val_values = {e["value"] for e in val_resp.json()}
    assert test_values != val_values


@pytest.mark.anyio
async def test_leaderboard_empty_for_unknown_metric(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, pipeline_uuid, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "metric": "metrica_che_non_esiste",
            "split": "test",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_leaderboard_top_n_limit(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, pipeline_uuid, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "metric": "ndcg@10",
            "split": "test",
            "top_n": 1,
        },
    )
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["rank"] == 1
    assert entries[0]["model_name"] == "MultiVAE"


@pytest.mark.anyio
async def test_leaderboard_query_endpoint_filters_author_and_hyperparams(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    (
        dataset_uuid,
        dataset_version_uuid,
        pipeline_uuid,
        _,
        metadata,
    ) = await _setup_leaderboard(client, superuser_token_headers)

    resp = await client.post(
        f"{API}/leaderboard/query",
        json={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "split": "test",
            "metrics": ["ndcg@10", "recall@20"],
            "sort_by": "ndcg@10",
            "top_n": 10,
            "author_uuids": [metadata["secondary_user_uuid"]],
            "hyperparam_filters": {"embedding_dim": 128},
        },
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["model_name"] == "EASE"
    assert rows[0]["submitted_by_user_uuid"] == metadata["secondary_user_uuid"]
    assert rows[0]["training_config"]["embedding_dim"] == 128


@pytest.mark.anyio
async def test_leaderboard_query_requires_pipeline_when_version_selected(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, _, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.post(
        f"{API}/leaderboard/query",
        json={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "split": "test",
            "metrics": ["ndcg@10"],
            "sort_by": "ndcg@10",
        },
    )
    assert resp.status_code == 422
    assert "pipeline_uuid" in resp.json()["detail"]


@pytest.mark.anyio
async def test_best_configuration_endpoint_returns_best_group(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, pipeline_uuid, _, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.post(
        f"{API}/leaderboard/best-configuration",
        json={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "pipeline_uuid": pipeline_uuid,
            "split": "test",
            "target_metric": "ndcg@10",
            "direction": "max",
            "group_by_hyperparams": ["embedding_dim", "batch_size"],
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["best_group"] is not None
    assert payload["best_group"]["model_name"] == "MultiVAE"
    assert payload["best_group"]["hyperparams"]["embedding_dim"] == 256
    assert len(payload["groups"]) >= 3
