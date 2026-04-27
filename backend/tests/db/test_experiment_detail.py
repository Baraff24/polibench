import pytest

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset, TaskType
from app.models.experiments import Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel
from app.models.pipelines import Pipeline


@pytest.mark.anyio
async def test_experiment_detail_returns_own_metrics(db):
    dataset = Dataset(name="Amazon-Beauty", task=TaskType.RATING_PREDICTION)
    await dataset.create()
    version = DatasetVersion(dataset_id=dataset.id, version="v1")
    await version.create()
    pipeline = Pipeline(dataset_version_id=version.id, code="P001")
    await pipeline.create()

    model = MLModel(name="SVD++")
    await model.create()

    fake_user_id = dataset.id

    exp_target = Experiment(
        pipeline_id=pipeline.id,
        dataset_version_id=version.id,
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=fake_user_id,
        run_name="SVD++ seed=42",
        status=Status.FINISHED,
    )
    await exp_target.create()

    exp_other = Experiment(
        pipeline_id=pipeline.id,
        dataset_version_id=version.id,
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=fake_user_id,
        run_name="SVD++ seed=99",
        status=Status.FINISHED,
    )
    await exp_other.create()

    for metric_name, split, value in [
        ("rmse", Split.TEST, 0.8721),
        ("mae", Split.TEST, 0.6543),
        ("rmse", Split.VALIDATION, 0.8850),
        ("mae", Split.VALIDATION, 0.6701),
    ]:
        await Metric(
            experiment_id=exp_target.id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            pipeline_id=pipeline.id,
            model_id=model.id,
            split=split,
            metric=metric_name,
            value=value,
            direction=Direction.MIN,
        ).create()

    for value in [0.9100, 0.7200]:
        await Metric(
            experiment_id=exp_other.id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            pipeline_id=pipeline.id,
            model_id=model.id,
            split=Split.TEST,
            metric="rmse",
            value=value,
            direction=Direction.MIN,
        ).create()

    run_metrics = await Metric.find(Metric.experiment_id == exp_target.id).to_list()

    assert len(run_metrics) == 4
    for m in run_metrics:
        assert m.experiment_id == exp_target.id

    assert {m.split for m in run_metrics} == {Split.TEST, Split.VALIDATION}
    assert {m.metric for m in run_metrics} == {"rmse", "mae"}
