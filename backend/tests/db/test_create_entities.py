import pytest

from app.models.dataset_versions import DatasetVersion
from app.models.datasets import Dataset, TaskType, Visibility
from app.models.experiments import Artifacts, CodeInfo, Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel
from app.models.pipelines import Pipeline


@pytest.mark.anyio
async def test_create_dataset(db):
    dataset = Dataset(
        name="MovieLens-1M",
        task=TaskType.RANKING,
        description="Dataset classico per recommendation ranking",
        visibility=Visibility.PUBLIC,
    )
    await dataset.create()

    found = await Dataset.get(dataset.id)

    assert found is not None
    assert found.name == "MovieLens-1M"
    assert found.task == TaskType.RANKING


@pytest.mark.anyio
async def test_create_dataset_version(db):
    dataset = Dataset(name="MovieLens-1M", task=TaskType.RANKING)
    await dataset.create()
    version = DatasetVersion(
        dataset_id=dataset.id,
        version="1.0",
        n_users=6040,
        n_items=3706,
        n_interactions=1_000_209,
        density=0.0447,
    )
    await version.create()

    found = await DatasetVersion.get(version.id)
    assert found is not None
    assert found.version == "1.0"
    assert found.dataset_id == dataset.id
    assert found.n_users == 6040


@pytest.mark.anyio
async def test_create_ml_model(db):
    model = MLModel(
        name="BPR-MF",
        family="matrix_factorization",
        paper_url="https://arxiv.org/abs/1205.2618",
        hyperparams={"factors": 64, "lr": 0.01, "reg": 1e-5},
    )
    await model.create()

    found = await MLModel.get(model.id)

    assert found is not None
    assert found.name == "BPR-MF"
    assert found.hyperparams is not None
    assert found.hyperparams["factors"] == 64


@pytest.mark.anyio
async def test_create_experiment(db):
    dataset = Dataset(name="ML-1M", task=TaskType.RANKING)
    await dataset.create()
    version = DatasetVersion(dataset_id=dataset.id, version="1.0")
    await version.create()
    pipeline = Pipeline(dataset_version_id=version.id, code="P001")
    await pipeline.create()
    model = MLModel(name="EASE")
    await model.create()

    experiment = Experiment(
        pipeline_id=pipeline.id,
        dataset_version_id=version.id,
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=dataset.id,
        run_name="EASE baseline run #1",
        status=Status.FINISHED,
        seed=42,
        notes="Prima run di riferimento",
        code=CodeInfo(
            git_commit="abc1234",
            repo_url="https://github.com/example/polibench",
        ),
        artifacts=Artifacts(predictions_path="/mnt/runs/1/predictions.json"),
        training_config={"epochs": 50, "batch_size": 1024},
    )
    await experiment.create()

    found = await Experiment.get(experiment.id)

    assert found is not None
    assert found.run_name == "EASE baseline run #1"
    assert found.status == Status.FINISHED
    assert found.dataset_version_id == version.id
    assert found.model_id == model.id
    assert found.training_config is not None
    assert found.training_config["epochs"] == 50


@pytest.mark.anyio
async def test_create_metrics(db):
    dataset = Dataset(name="ML-1M", task=TaskType.RANKING)
    await dataset.create()
    version = DatasetVersion(dataset_id=dataset.id, version="1.0")
    await version.create()
    pipeline = Pipeline(dataset_version_id=version.id, code="P001")
    await pipeline.create()
    model = MLModel(name="BPR-MF")
    await model.create()
    experiment = Experiment(
        pipeline_id=pipeline.id,
        dataset_version_id=version.id,
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=dataset.id,
        status=Status.FINISHED,
    )
    await experiment.create()

    metrics_data = [
        (Split.TEST, "ndcg@10", 10, 0.3821, Direction.MAX),
        (Split.VALIDATION, "ndcg@10", 10, 0.3754, Direction.MAX),
        (Split.TEST, "recall@20", 20, 0.2100, Direction.MAX),
    ]
    for split, name, k, value, direction in metrics_data:
        await Metric(
            experiment_id=experiment.id,
            dataset_id=dataset.id,
            dataset_version_id=version.id,
            pipeline_id=pipeline.id,
            model_id=model.id,
            split=split,
            metric=name,
            k=k,
            value=value,
            direction=direction,
        ).create()

    saved = await Metric.find(Metric.experiment_id == experiment.id).to_list()
    assert len(saved) == 3
