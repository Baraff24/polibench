import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


async def _setup_leaderboard(client, headers) -> tuple[str, str, list[str]]:
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "LB-Dataset", "task": "ranking"},
        headers=headers,
    )
    dataset_uuid = ds_resp.json()["uuid"]

    version_resp = await client.post(
        f"{API}/datasets/{dataset_uuid}/versions",
        json={"version": "1.0", "status": "ready"},
        headers=headers,
    )
    dataset_version_uuid = version_resp.json()["uuid"]

    scores = [
        ("iALS", 0.3990),
        ("EASE", 0.4512),
        ("MultiVAE", 0.4801),
    ]

    exp_uuids = []
    for model_name, ndcg_value in scores:
        m_resp = await client.post(
            f"{API}/ml-models",
            json={"name": model_name},
            headers=headers,
        )
        model_uuid = m_resp.json()["uuid"]

        e_resp = await client.post(
            f"{API}/experiments",
            json={
                "dataset_version_uuid": dataset_version_uuid,
                "model_uuid": model_uuid,
            },
            headers=headers,
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

    return dataset_uuid, dataset_version_uuid, exp_uuids


@pytest.mark.anyio
async def test_leaderboard_top_n_sorted(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
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


@pytest.mark.anyio
async def test_leaderboard_filters_by_split(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    dataset_uuid, dataset_version_uuid, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    test_resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
            "metric": "ndcg@10",
            "split": "test",
        },
    )
    val_resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
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
    dataset_uuid, dataset_version_uuid, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
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
    dataset_uuid, dataset_version_uuid, _ = await _setup_leaderboard(
        client,
        superuser_token_headers,
    )

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "dataset_version_uuid": dataset_version_uuid,
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
