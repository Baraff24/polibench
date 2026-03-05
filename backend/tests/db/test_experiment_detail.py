"""
Smoke Test C — Dettaglio run (experiment)
==========================================
Simula la pagina "dettaglio run" dell'UI:
    dato un experiment_id, recupera TUTTE le sue metriche.

Il punto critico da verificare non è solo "trovo le metriche giuste",
ma anche "NON trovo le metriche di altri experiment" (isolamento).
Una query rotta potrebbe ritornare tutto invece di filtrare.
"""

import pytest

from app.models.datasets import Dataset, TaskType
from app.models.experiments import Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel


@pytest.mark.anyio
async def test_experiment_detail_returns_own_metrics(db):
    """Recupera tutte e sole le metriche dell'experiment target."""
    dataset = Dataset(
        name="Amazon-Beauty", version="1.0", task=TaskType.RATING_PREDICTION
    )
    await dataset.create()

    model = MLModel(name="SVD++")
    await model.create()

    fake_user_id = dataset.id

    # Due experiment sullo stesso dataset/model: le loro metriche NON devono mescolarsi
    exp_target = Experiment(
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=fake_user_id,
        run_name="SVD++ seed=42",
        status=Status.FINISHED,
    )
    await exp_target.create()

    exp_other = Experiment(
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=fake_user_id,
        run_name="SVD++ seed=99",
        status=Status.FINISHED,
    )
    await exp_other.create()

    # 4 metriche per exp_target: 2 split × 2 metriche
    for metric_name, split, value in [
        ("rmse", Split.TEST, 0.8721),
        ("mae", Split.TEST, 0.6543),
        ("rmse", Split.VALIDATION, 0.8850),
        ("mae", Split.VALIDATION, 0.6701),
    ]:
        await Metric(
            experiment_id=exp_target.id,
            dataset_id=dataset.id,
            model_id=model.id,
            split=split,
            metric=metric_name,
            value=value,
            direction=Direction.MIN,
        ).create()

    # 2 metriche per exp_other — NON devono comparire nella query di exp_target
    for value in [0.9100, 0.7200]:
        await Metric(
            experiment_id=exp_other.id,
            dataset_id=dataset.id,
            model_id=model.id,
            split=Split.TEST,
            metric="rmse",
            value=value,
            direction=Direction.MIN,
        ).create()

    # --- Query ---
    run_metrics = await Metric.find(Metric.experiment_id == exp_target.id).to_list()

    # Esattamente 4, non 6
    assert len(run_metrics) == 4, (
        f"Attese 4 metriche per exp_target, trovate {len(run_metrics)}"
    )

    # Tutte appartengono all'experiment corretto
    for m in run_metrics:
        assert m.experiment_id == exp_target.id, (
            f"Trovata metrica di un altro experiment: {m.experiment_id}"
        )

    # Coprono entrambi gli split e entrambe le metriche
    assert {m.split for m in run_metrics} == {Split.TEST, Split.VALIDATION}
    assert {m.metric for m in run_metrics} == {"rmse", "mae"}
