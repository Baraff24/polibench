import pytest

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset, TaskType
from app.models.experiments import Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel


@pytest.mark.anyio
async def test_leaderboard_top_n_ordered(db):
    dataset = Dataset(name="ML-20M", task=TaskType.RANKING)
    await dataset.create()
    version = DatasetVersion(dataset_id=dataset.id, version="1.0")
    await version.create()

    model_data = [
        ("iALS", 0.3990),
        ("EASE", 0.4512),
        ("MultiVAE", 0.4801),
    ]
    fake_user_id = dataset.id

    for model_name, ndcg_value in model_data:
        model = MLModel(name=model_name)
        await model.create()

        exp = Experiment(
            dataset_version_id=version.id,
            model_id=model.id,
            submitted_by_user_id=fake_user_id,
            status=Status.FINISHED,
        )
        await exp.create()

        await Metric(
            experiment_id=exp.id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            model_id=model.id,
            split=Split.TEST,
            metric="ndcg@10",
            k=10,
            value=ndcg_value,
            direction=Direction.MAX,
        ).create()

    leaderboard = (
        await Metric.find(
            Metric.dataset_id == dataset.id,
            Metric.dataset_version_id == version.id,
            Metric.split == Split.TEST,
            Metric.metric == "ndcg@10",
        )
        .sort(-Metric.value)
        .limit(3)
        .to_list()
    )

    assert len(leaderboard) == 3
    assert leaderboard[0].value == pytest.approx(0.4801, rel=1e-4)
    assert leaderboard[1].value == pytest.approx(0.4512, rel=1e-4)
    assert leaderboard[2].value == pytest.approx(0.3990, rel=1e-4)

    values = [m.value for m in leaderboard]
    assert values == sorted(values, reverse=True)


@pytest.mark.anyio
async def test_leaderboard_filters_by_split(db):
    dataset = Dataset(name="ML-20M", task=TaskType.RANKING)
    await dataset.create()
    version = DatasetVersion(dataset_id=dataset.id, version="2.0")
    await version.create()

    model = MLModel(name="ItemKNN")
    await model.create()
    exp = Experiment(
        dataset_version_id=version.id,
        model_id=model.id,
        submitted_by_user_id=dataset.id,
        status=Status.FINISHED,
    )
    await exp.create()

    await Metric(
        experiment_id=exp.id,
        dataset_id=dataset.id,
        dataset_version_id=version.id,
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
        dataset_version_id=version.id,
        model_id=model.id,
        split=Split.VALIDATION,
        metric="ndcg@10",
        k=10,
        value=0.38,
        direction=Direction.MAX,
    ).create()

    result = await Metric.find(
        Metric.dataset_id == dataset.id,
        Metric.dataset_version_id == version.id,
        Metric.split == Split.TEST,
        Metric.metric == "ndcg@10",
    ).to_list()

    assert len(result) == 1
    assert result[0].split == Split.TEST
