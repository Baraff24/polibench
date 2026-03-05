"""
tests/routers_v2/test_leaderboard.py
======================================
Test API end-to-end per la leaderboard.

Test 1 — test_leaderboard_top_n_sorted:
    Crea 3 modelli con punteggi diversi, verifica che la risposta
    sia ordinata per value DESC e contenga rank progressivo.

Test 2 — test_leaderboard_filters_by_split:
    Verifica che le metriche validation non compaiano nella query test.

Test 3 — test_leaderboard_empty_for_unknown_metric:
    Una metrica inesistente → lista vuota (non errore).

Questi test replicano gli smoke test DB (test_leaderboard.py) ma
passando per HTTP, verificando così routing + auth + service + schema.
"""

import pytest
from httpx import AsyncClient

from app.config.config import settings

API = settings.API_V1_STR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_leaderboard(client, headers) -> tuple[str, list[str]]:
    """
    Crea 1 dataset e 3 modelli, sottomette 3 experiment con metriche.
    Ritorna (dataset_uuid, [exp_uuid1, exp_uuid2, exp_uuid3]).
    Punteggi intenzionalmente fuori ordine per testare il sort.
    """
    # Dataset
    ds_resp = await client.post(
        f"{API}/datasets",
        json={"name": "LB-Dataset", "version": "1.0", "task": "ranking"},
        headers=headers,
    )
    dataset_uuid = ds_resp.json()["uuid"]

    scores = [
        ("iALS", 0.3990),
        ("EASE", 0.4512),
        ("MultiVAE", 0.4801),
    ]

    exp_uuids = []
    for model_name, ndcg_value in scores:
        # Crea modello
        m_resp = await client.post(
            f"{API}/ml-models",
            json={"name": model_name},
            headers=headers,
        )
        model_uuid = m_resp.json()["uuid"]

        # Crea experiment
        e_resp = await client.post(
            f"{API}/experiments",
            json={"dataset_uuid": dataset_uuid, "model_uuid": model_uuid},
            headers=headers,
        )
        exp_uuid = e_resp.json()["uuid"]
        exp_uuids.append(exp_uuid)

        # Sottometti metriche (test + validation)
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
                        "value": ndcg_value - 0.02,  # val sempre un po' sotto
                        "direction": "max",
                    },
                ],
            },
            headers=headers,
        )

    return dataset_uuid, exp_uuids


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_leaderboard_top_n_sorted(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """
    La leaderboard deve essere ordinata per value DESC
    e ogni entry deve avere rank progressivo (1, 2, 3).
    """
    dataset_uuid, _ = await _setup_leaderboard(client, superuser_token_headers)

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "metric": "ndcg@10",
            "split": "test",
            "top_n": 10,
        },
    )
    assert resp.status_code == 200
    entries = resp.json()

    assert len(entries) == 3

    # Ordine: MultiVAE (0.4801) > EASE (0.4512) > iALS (0.3990)
    assert entries[0]["model_name"] == "MultiVAE"
    assert entries[1]["model_name"] == "EASE"
    assert entries[2]["model_name"] == "iALS"

    # Valori decrescenti
    values = [e["value"] for e in entries]
    assert values == sorted(values, reverse=True)

    # Rank progressivo 1, 2, 3
    assert [e["rank"] for e in entries] == [1, 2, 3]

    # Schema UUID-first
    for e in entries:
        assert "experiment_uuid" in e
        assert "model_uuid" in e
        assert "dataset_uuid" in e
        assert "_id" not in e
        assert e["dataset_uuid"] == dataset_uuid


@pytest.mark.anyio
async def test_leaderboard_filters_by_split(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """
    La query split=test non deve restituire le metriche validation
    e viceversa. I valori devono essere diversi (val = test - 0.02).
    """
    dataset_uuid, _ = await _setup_leaderboard(client, superuser_token_headers)

    test_resp = await client.get(
        f"{API}/leaderboard",
        params={"dataset_uuid": dataset_uuid, "metric": "ndcg@10", "split": "test"},
    )
    val_resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
            "metric": "ndcg@10",
            "split": "validation",
        },
    )
    assert test_resp.status_code == 200
    assert val_resp.status_code == 200

    test_values = {e["value"] for e in test_resp.json()}
    val_values = {e["value"] for e in val_resp.json()}

    # I due set non devono coincidere
    assert test_values != val_values
    # Tutti i valori test split nelle entries test
    for e in test_resp.json():
        assert e["split"] == "test"
    for e in val_resp.json():
        assert e["split"] == "validation"


@pytest.mark.anyio
async def test_leaderboard_empty_for_unknown_metric(
    client: AsyncClient,
    superuser_token_headers: dict[str, str],
) -> None:
    """Una metrica inesistente → lista vuota, non errore."""
    dataset_uuid, _ = await _setup_leaderboard(client, superuser_token_headers)

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
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
    """top_n=1 ritorna solo il primo risultato."""
    dataset_uuid, _ = await _setup_leaderboard(client, superuser_token_headers)

    resp = await client.get(
        f"{API}/leaderboard",
        params={
            "dataset_uuid": dataset_uuid,
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
