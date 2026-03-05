"""
Smoke Test A — Creazione entità
================================
Verifica che ogni modello Beanie:
  1. si possa istanziare con i campi obbligatori
  2. si possa salvare su MongoDB (.create())
  3. sia recuperabile tramite .get(id)
  4. mantenga i valori corretti dopo il round-trip DB

La fixture `db` è definita in tests/conftest.py e fornisce un DB
MongoDB in-memory (mongomock-motor), senza bisogno di Docker.
"""

import pytest

from app.models.datasets import Dataset, Splits, TaskType, Visibility
from app.models.experiments import Artifacts, CodeInfo, Experiment, Status
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel


@pytest.mark.anyio
async def test_create_dataset(db):
    dataset = Dataset(
        name="MovieLens-1M",
        version="1.0",
        task=TaskType.RANKING,
        description="Dataset classico per recommendation ranking",
        visibility=Visibility.PUBLIC,
        splits=Splits(train=800_000, test=100_000, validation=100_000),
    )
    # .create() → INSERT su MongoDB, popola dataset.id con l'ObjectId assegnato
    await dataset.create()

    # .get(id) → findOne({_id: id})
    found = await Dataset.get(dataset.id)

    assert found is not None, "Il dataset non è stato trovato nel DB"
    assert found.name == "MovieLens-1M"
    assert found.task == TaskType.RANKING
    # Splits è un sotto-documento (EmbeddedModel): verifica il round-trip
    assert found.splits is not None
    assert found.splits.test == 100_000


@pytest.mark.anyio
async def test_create_ml_model(db):
    model = MLModel(
        name="BPR-MF",
        family="matrix_factorization",
        paper_url="https://arxiv.org/abs/1205.2618",
        # hyperparams è dict[str, Any]: verifica che sopravviva al round-trip
        hyperparams={"factors": 64, "lr": 0.01, "reg": 1e-5},
    )
    await model.create()

    found = await MLModel.get(model.id)

    assert found is not None, "Il modello non è stato trovato nel DB"
    assert found.name == "BPR-MF"
    assert found.hyperparams is not None
    assert found.hyperparams["factors"] == 64


@pytest.mark.anyio
async def test_create_experiment(db):
    # Prima creiamo le entità collegate (dataset e model)
    dataset = Dataset(name="ML-1M", version="1.0", task=TaskType.RANKING)
    await dataset.create()
    model = MLModel(name="EASE")
    await model.create()

    experiment = Experiment(
        dataset_id=dataset.id,  # PydanticObjectId → FK verso Dataset
        model_id=model.id,  # PydanticObjectId → FK verso MLModel
        submitted_by_user_id=dataset.id,  # stub: usiamo un ObjectId valido
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

    assert found is not None, "L'experiment non è stato trovato nel DB"
    assert found.run_name == "EASE baseline run #1"
    assert found.status == Status.FINISHED
    # Verifica che le FK (ObjectId) siano state salvate correttamente
    assert found.dataset_id == dataset.id
    assert found.model_id == model.id
    # training_config è dict[str, Any]
    assert found.training_config is not None
    assert found.training_config["epochs"] == 50


@pytest.mark.anyio
async def test_create_metrics(db):
    dataset = Dataset(name="ML-1M", version="1.0", task=TaskType.RANKING)
    await dataset.create()
    model = MLModel(name="BPR-MF")
    await model.create()
    experiment = Experiment(
        dataset_id=dataset.id,
        model_id=model.id,
        submitted_by_user_id=dataset.id,
        status=Status.FINISHED,
    )
    await experiment.create()

    # Creiamo 3 metriche: stessa metrica su split diversi + metrica diversa
    metrics_data = [
        (Split.TEST, "ndcg@10", 10, 0.3821, Direction.MAX),
        (Split.VALIDATION, "ndcg@10", 10, 0.3754, Direction.MAX),
        (Split.TEST, "recall@20", 20, 0.2100, Direction.MAX),
    ]
    for split, name, k, value, direction in metrics_data:
        await Metric(
            experiment_id=experiment.id,
            dataset_id=dataset.id,
            model_id=model.id,
            split=split,
            metric=name,
            k=k,
            value=value,
            direction=direction,
        ).create()

    # .find(...).to_list() → SELECT * WHERE experiment_id = ...
    saved = await Metric.find(Metric.experiment_id == experiment.id).to_list()
    assert len(saved) == 3, f"Attese 3 metriche, trovate {len(saved)}"
