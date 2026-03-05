"""
Smoke Test B — Query Leaderboard
==================================
Verifica la query più critica del sistema:
    "per un dato dataset/split/metrica, dammi i top-N ordinati per valore desc"

Usiamo 3 modelli con punteggi volutamente fuori ordine per assicurarci
che l'ordinamento funzioni davvero e non passi per caso.

Beanie query pattern usato:
    Metric.find(filtro1, filtro2, filtro3)
          .sort(-Metric.value)   ← il - significa DESC
          .limit(N)
          .to_list()
"""

import pytest

from app.models.datasets import Dataset, TaskType
from app.models.experiments import Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel


@pytest.mark.anyio
async def test_leaderboard_top_n_ordered(db):
    # --- Setup ---
    dataset = Dataset(name="ML-20M", version="1.0", task=TaskType.RANKING)
    await dataset.create()

    # Tre modelli con punteggi volutamente fuori ordine:
    # iALS viene inserito per primo ma è il peggiore → l'ordinamento deve spostarlo
    model_data = [
        ("iALS", 0.3990),  # terzo posto
        ("EASE", 0.4512),  # secondo posto
        ("MultiVAE", 0.4801),  # primo posto
    ]
    fake_user_id = dataset.id  # ObjectId valido come stub per submitted_by_user_id

    for model_name, ndcg_value in model_data:
        model = MLModel(name=model_name)
        await model.create()

        exp = Experiment(
            dataset_id=dataset.id,
            model_id=model.id,
            submitted_by_user_id=fake_user_id,
            status=Status.FINISHED,
        )
        await exp.create()

        await Metric(
            experiment_id=exp.id,
            dataset_id=dataset.id,
            model_id=model.id,
            split=Split.TEST,
            metric="ndcg@10",
            k=10,
            value=ndcg_value,
            direction=Direction.MAX,
        ).create()

    # --- Query leaderboard ---
    leaderboard = (
        await Metric.find(
            Metric.dataset_id == dataset.id,
            Metric.split == Split.TEST,
            Metric.metric == "ndcg@10",
        )
        .sort(-Metric.value)  # DESC: il migliore in cima
        .limit(3)
        .to_list()
    )

    assert len(leaderboard) == 3

    # Verifica ordine: 0.4801 → 0.4512 → 0.3990
    assert leaderboard[0].value == pytest.approx(0.4801, rel=1e-4)
    assert leaderboard[1].value == pytest.approx(0.4512, rel=1e-4)
    assert leaderboard[2].value == pytest.approx(0.3990, rel=1e-4)

    # Verifica generica: i valori sono strettamente decrescenti
    values = [m.value for m in leaderboard]
    assert values == sorted(values, reverse=True), (
        "Il leaderboard non è ordinato per valore decrescente!"
    )


@pytest.mark.anyio
async def test_leaderboard_filters_by_split(db):
    """Le metriche VALIDATION non devono comparire nel leaderboard TEST."""
    dataset = Dataset(name="ML-20M", version="2.0", task=TaskType.RANKING)
    await dataset.create()

    model = MLModel(name="ItemKNN")
    await model.create()
    exp = Experiment(
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=dataset.id,
        status=Status.FINISHED,
    )
    await exp.create()

    # Una metrica TEST e una VALIDATION, stessa nome metrica
    await Metric(
        experiment_id=exp.id,
        dataset_id=dataset.id,
        model_id=model.id,
        split=Split.TEST,
        metric="ndcg@10",
        k=10,
        value=0.40,
        direction=Direction.MAX,
    ).create()
    await Metric(
        experiment_id=exp.id,
        dataset_id=dataset.id,
        model_id=model.id,
        split=Split.VALIDATION,
        metric="ndcg@10",
        k=10,
        value=0.38,
        direction=Direction.MAX,
    ).create()

    # Il leaderboard TEST deve restituire solo 1 risultato
    result = await Metric.find(
        Metric.dataset_id == dataset.id,
        Metric.split == Split.TEST,
        Metric.metric == "ndcg@10",
    ).to_list()

    assert len(result) == 1
    assert result[0].split == Split.TEST
