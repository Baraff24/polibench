"""
scripts/seed.py
===============

Seed registry-aware allineato al modello DataRec:
- Dataset (catalogo)
- DatasetVersion con YAML raw (dataset/version/pipeline/characteristics)
- Source / Resource derivate dal version YAML
- Experiment agganciati a DatasetVersion
- ExperimentMetric importate via CSV con MetricImportJob

Uso:
  cd backend
  uv run python scripts/seed.py --mode minimal
  uv run python scripts/seed.py --mode demo
  uv run python scripts/seed.py --mode demo --reset
"""

import argparse
import asyncio
import io
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from textwrap import dedent

from beanie import init_beanie
from fastapi import UploadFile
from pymongo import AsyncMongoClient

sys.path.insert(0, ".")

from app.auth.auth import get_hashed_password
from app.config.config import settings
from app.models import DOCUMENT_MODELS
from app.models.dataset_versions import DatasetVersion, VersionStatus
from app.models.datasets import Dataset, TaskType, Visibility
from app.models.experiments import Experiment, Status
from app.models.metric_import_jobs import MetricImportJob
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel
from app.models.resources import Resource
from app.models.sources import Source
from app.models.users import User
from app.schemas.dataset_versions import DatasetVersionCreate
from app.schemas.datasets import DatasetCreate
from app.schemas.experiments import ExperimentCreate
from app.schemas.ml_models import MLModelCreate
from app.services.dataset_versions import create_dataset_version
from app.services.datasets import create_dataset, create_ml_model
from app.services.experiments import create_experiment
from app.services.metric_imports import (
    create_metric_import_job,
    process_metric_import_job,
)


@dataclass(frozen=True)
class MetricCsvRow:
    split: Split
    metric: str
    value: float
    direction: Direction
    k: int | None = None


@dataclass(frozen=True)
class DatasetFixture:
    name: str
    task: TaskType
    description: str
    visibility: Visibility
    version: str
    dataset_yaml_raw: str
    version_yaml_raw: str
    characteristics_yaml_raw: str
    pipeline_yaml_raw: str


@dataclass(frozen=True)
class ModelFixture:
    name: str
    family: str
    paper_url: str | None = None
    implementation: str | None = None
    hyperparams: dict | None = None


@dataclass(frozen=True)
class ExperimentFixture:
    dataset_name: str
    dataset_version: str
    model_name: str
    run_name: str
    seed: int
    status: Status
    metrics: list[MetricCsvRow] = field(default_factory=list)


def _yaml(raw: str) -> str:
    return dedent(raw).strip()


DATASET_FIXTURES: dict[str, DatasetFixture] = {
    "alibaba_ifashion_v1": DatasetFixture(
        name="Alibaba-iFashion",
        task=TaskType.RANKING,
        description=(
            "Fashion recommendation benchmark with implicit feedback and side metadata."
        ),
        visibility=Visibility.PUBLIC,
        version="v1",
        dataset_yaml_raw=_yaml(
            """
            name: Alibaba-iFashion
            versions:
              - v1
            latest_version: v1
            source: DataRecHub
            description: Fashion recommendation benchmark.
            citation: "DataRecHub examples"
            """
        ),
        version_yaml_raw=_yaml(
            """
            dataset_name: Alibaba-iFashion
            version: v1
            sources:
              - name: raw-archive
                source_type: url
                downloadable: true
                url: https://example.org/datasets/alibaba_ifashion_v1.zip
                filename: alibaba_ifashion_v1.zip
                checksum: "sha256:abc123"
                checksum_algorithm: sha256
              - name: docs
                source_type: url
                downloadable: true
                url: https://example.org/datasets/alibaba_ifashion_readme.txt
                filename: alibaba_ifashion_readme.txt
            resources:
              - name: interactions
                source_name: raw-archive
                type: interactions
                format: csv
                required: true
              - name: users
                source_name: raw-archive
                type: user_features
                format: csv
                required: false
              - name: items
                source_name: raw-archive
                type: item_features
                format: csv
                required: false
            """
        ),
        characteristics_yaml_raw=_yaml(
            """
            dataset_name: Alibaba-iFashion
            version: v1
            characteristics:
              n_users: 62010
              n_items: 35402
              n_interactions: 781453
              density: 0.000356
              gini_user: 0.612
              gini_item: 0.701
            """
        ),
        pipeline_yaml_raw=_yaml(
            """
            pipeline:
              - name: ingest
                operation: load_csv
                params:
                  file: interactions.csv
              - name: normalize
                operation: normalize_ids
                params:
                  user_col: user_id
                  item_col: item_id
              - name: split
                operation: leave_one_out
                params:
                  min_interactions: 5
            """
        ),
    ),
    "epinions_v1": DatasetFixture(
        name="Epinions",
        task=TaskType.RANKING,
        description="Trust-aware recommendation benchmark from Epinions reviews.",
        visibility=Visibility.PUBLIC,
        version="v1",
        dataset_yaml_raw=_yaml(
            """
            name: Epinions
            versions:
              - v1
            latest_version: v1
            source: DataRecHub
            description: Epinions trust/review benchmark.
            citation: "DataRecHub examples"
            """
        ),
        version_yaml_raw=_yaml(
            """
            dataset_name: Epinions
            version: v1
            sources:
              - name: epinions-main
                source_type: url
                downloadable: true
                url: https://example.org/datasets/epinions_v1.tar.gz
                filename: epinions_v1.tar.gz
            resources:
              - name: interactions
                source_name: epinions-main
                type: interactions
                format: tsv
                required: true
              - name: trust_network
                source_name: epinions-main
                type: graph
                format: tsv
                required: false
            """
        ),
        characteristics_yaml_raw=_yaml(
            """
            dataset_name: Epinions
            version: v1
            characteristics:
              n_users: 40163
              n_items: 139738
              n_interactions: 664824
              density: 0.000118
              gini_user: 0.674
              gini_item: 0.752
            """
        ),
        pipeline_yaml_raw=_yaml(
            """
            pipeline:
              - name: parse
                operation: parse_tsv
                params:
                  delimiter: "\\t"
              - name: clean
                operation: drop_duplicates
                params: {}
              - name: split
                operation: temporal_split
                params:
                  train_ratio: 0.8
            """
        ),
    ),
    "movielens_100k_v1": DatasetFixture(
        name="MovieLens-100K",
        task=TaskType.RATING_PREDICTION,
        description="Classic explicit-feedback benchmark for rating prediction.",
        visibility=Visibility.PUBLIC,
        version="v1",
        dataset_yaml_raw=_yaml(
            """
            name: MovieLens-100K
            versions:
              - v1
            latest_version: v1
            source: DataRecHub
            description: MovieLens 100K benchmark.
            citation: "GroupLens Research"
            """
        ),
        version_yaml_raw=_yaml(
            """
            dataset_name: MovieLens-100K
            version: v1
            sources:
              - name: ml100k-main
                source_type: url
                downloadable: true
                url: https://example.org/datasets/movielens_100k_v1.zip
                filename: movielens_100k_v1.zip
            resources:
              - name: ratings
                source_name: ml100k-main
                type: interactions
                format: csv
                required: true
            """
        ),
        characteristics_yaml_raw=_yaml(
            """
            dataset_name: MovieLens-100K
            version: v1
            characteristics:
              n_users: 943
              n_items: 1682
              n_interactions: 100000
              density: 0.063046
              gini_user: 0.321
              gini_item: 0.417
            """
        ),
        pipeline_yaml_raw=_yaml(
            """
            pipeline:
              - name: load
                operation: load_csv
                params:
                  file: ratings.csv
              - name: split
                operation: random_split
                params:
                  train_ratio: 0.8
                  validation_ratio: 0.1
            """
        ),
    ),
}


MODEL_FIXTURES = [
    ModelFixture(
        name="LightGCN",
        family="graph-neural-network",
        paper_url="https://arxiv.org/abs/2002.02126",
        implementation="https://github.com/gusye1234/LightGCN-PyTorch",
        hyperparams={"n_layers": 3, "embedding_dim": 64, "lr": 0.001},
    ),
    ModelFixture(
        name="BPR",
        family="matrix-factorization",
        paper_url="https://arxiv.org/abs/1205.2618",
        implementation="https://github.com/guoyang9/BPR-pytorch",
        hyperparams={"embedding_dim": 64, "lr": 0.001, "reg": 0.0001},
    ),
    ModelFixture(
        name="SVD",
        family="matrix-factorization",
        paper_url="https://dl.acm.org/doi/10.1145/1401890.1401944",
        implementation="https://surpriselib.com",
        hyperparams={"n_factors": 100, "n_epochs": 20, "lr_all": 0.005},
    ),
]


MINIMAL_EXPERIMENT_FIXTURES = [
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-minimal-lightgcn-alibaba-v1",
        seed=42,
        status=Status.FINISHED,
        metrics=[
            MetricCsvRow(Split.TEST, "ndcg@10", 0.1832, Direction.MAX, k=10),
            MetricCsvRow(Split.TEST, "recall@20", 0.2583, Direction.MAX, k=20),
            MetricCsvRow(Split.VALIDATION, "ndcg@10", 0.1711, Direction.MAX, k=10),
        ],
    ),
]


DEMO_EXPERIMENT_FIXTURES = [
    *MINIMAL_EXPERIMENT_FIXTURES,
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v1",
        model_name="BPR",
        run_name="seed-demo-bpr-epinions-v1",
        seed=7,
        status=Status.FINISHED,
        metrics=[
            MetricCsvRow(Split.TEST, "ndcg@10", 0.0861, Direction.MAX, k=10),
            MetricCsvRow(Split.TEST, "recall@20", 0.1197, Direction.MAX, k=20),
            MetricCsvRow(Split.VALIDATION, "ndcg@10", 0.0819, Direction.MAX, k=10),
        ],
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v1",
        model_name="SVD",
        run_name="seed-demo-svd-ml100k-v1",
        seed=21,
        status=Status.FINISHED,
        metrics=[
            MetricCsvRow(Split.TEST, "rmse", 0.9341, Direction.MIN),
            MetricCsvRow(Split.TEST, "mae", 0.7382, Direction.MIN),
            MetricCsvRow(Split.VALIDATION, "rmse", 0.9425, Direction.MIN),
        ],
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-epinions-running",
        seed=99,
        status=Status.RUNNING,
        metrics=[],
    ),
]


FORBIDDEN_DATASET_CHARACTERISTICS_METRICS = {
    "n_users",
    "n_items",
    "n_interactions",
    "density",
    "gini_user",
    "gini_item",
}


def _metrics_to_csv(rows: list[MetricCsvRow]) -> str:
    lines = ["split,metric,k,value,direction"]
    for row in rows:
        k_value = "" if row.k is None else str(row.k)
        lines.append(
            f"{row.split.value},{row.metric},{k_value},{row.value:.6f},{row.direction.value}"
        )
    return "\n".join(lines) + "\n"


async def _ensure_admin() -> User:
    admin = await User.find_one({"email": settings.FIRST_SUPERUSER})
    if admin is not None:
        print(f"admin: present ({admin.email})")
        return admin

    admin = User(
        email=settings.FIRST_SUPERUSER,
        hashed_password=get_hashed_password(settings.FIRST_SUPERUSER_PASSWORD),
        is_superuser=True,
        is_verified=True,
    )
    await admin.create()
    print(f"admin: created ({admin.email})")
    return admin


async def _upsert_dataset(fixture: DatasetFixture, admin: User) -> tuple[Dataset, bool]:
    existing = await Dataset.find_one(Dataset.name == fixture.name)
    if existing is not None:
        return existing, False

    public = await create_dataset(
        DatasetCreate(
            name=fixture.name,
            task=fixture.task,
            description=fixture.description,
            visibility=fixture.visibility,
        ),
        admin,
    )
    created = await Dataset.find_one(Dataset.uuid == public.uuid)
    if created is None:
        raise RuntimeError(f"Dataset appena creato non trovato: {fixture.name}")
    return created, True


async def _upsert_dataset_version(
    dataset: Dataset,
    fixture: DatasetFixture,
) -> tuple[DatasetVersion, bool]:
    existing = await DatasetVersion.find_one(
        {"dataset_id": dataset.id, "version": fixture.version}
    )
    if existing is not None:
        return existing, False

    public = await create_dataset_version(
        dataset.uuid,
        DatasetVersionCreate(
            version=fixture.version,
            status=VersionStatus.READY,
            dataset_yaml_raw=fixture.dataset_yaml_raw,
            version_yaml_raw=fixture.version_yaml_raw,
            characteristics_yaml_raw=fixture.characteristics_yaml_raw,
            pipeline_yaml_raw=fixture.pipeline_yaml_raw,
        ),
    )
    created = await DatasetVersion.find_one(DatasetVersion.uuid == public.uuid)
    if created is None:
        raise RuntimeError(
            f"DatasetVersion appena creata non trovata: {fixture.name} {fixture.version}"
        )
    return created, True


async def _upsert_model(fixture: ModelFixture, admin: User) -> tuple[MLModel, bool]:
    existing = await MLModel.find_one(MLModel.name == fixture.name)
    if existing is not None:
        return existing, False

    public = await create_ml_model(
        MLModelCreate(
            name=fixture.name,
            family=fixture.family,
            paper_url=fixture.paper_url,
            implementation=fixture.implementation,
            hyperparams=fixture.hyperparams,
        ),
        admin,
    )
    created = await MLModel.find_one(MLModel.uuid == public.uuid)
    if created is None:
        raise RuntimeError(f"MLModel appena creato non trovato: {fixture.name}")
    return created, True


async def _upsert_experiment(
    fixture: ExperimentFixture,
    dataset_version: DatasetVersion,
    model: MLModel,
    admin: User,
) -> tuple[Experiment, bool]:
    existing = await Experiment.find_one(Experiment.run_name == fixture.run_name)
    if existing is not None:
        return existing, False

    public = await create_experiment(
        ExperimentCreate(
            dataset_version_uuid=dataset_version.uuid,
            model_uuid=model.uuid,
            run_name=fixture.run_name,
            seed=fixture.seed,
            training_config=model.hyperparams,
            notes="Seeded via scripts/seed.py",
        ),
        admin,
    )
    created = await Experiment.find_one(Experiment.uuid == public.uuid)
    if created is None:
        raise RuntimeError(f"Experiment appena creato non trovato: {fixture.run_name}")
    return created, True


async def _sync_experiment_status(exp: Experiment, status: Status) -> None:
    changed = False
    if exp.status != status:
        exp.status = status
        changed = True

    if status == Status.FINISHED and exp.finished_at is None:
        exp.finished_at = datetime.now(UTC)
        changed = True
    if status != Status.FINISHED and exp.finished_at is not None:
        exp.finished_at = None
        changed = True

    if changed:
        await exp.save()


async def _import_metrics_from_csv_if_needed(
    exp: Experiment,
    rows: list[MetricCsvRow],
    admin: User,
) -> bool:
    if not rows:
        return False

    already_present = await Metric.find(Metric.experiment_id == exp.id).count()
    if already_present > 0:
        return False

    csv_content = _metrics_to_csv(rows)
    upload = UploadFile(
        io.BytesIO(csv_content.encode("utf-8")),
        filename=f"{exp.run_name or exp.uuid}.csv",
    )
    job = await create_metric_import_job(exp.uuid, upload, admin)
    await process_metric_import_job(job.uuid)
    return True


async def _consistency_checks(
    dataset_versions: dict[tuple[str, str], DatasetVersion],
    experiments: list[Experiment],
) -> list[str]:
    issues: list[str] = []

    for (dataset_name, version_name), version in dataset_versions.items():
        if version.status != VersionStatus.READY:
            continue
        sources_count = await Source.find(Source.dataset_version_id == version.id).count()
        resources_count = await Resource.find(
            Resource.dataset_version_id == version.id
        ).count()
        if sources_count == 0 and resources_count == 0:
            issues.append(
                "ready DatasetVersion senza sources/resources: "
                f"{dataset_name}:{version_name}"
            )

    for exp in experiments:
        linked_version = await DatasetVersion.get(exp.dataset_version_id)
        if linked_version is None:
            issues.append(f"experiment senza dataset_version valido: {exp.run_name}")

    bad_metrics = await Metric.find(
        {"metric": {"$in": list(FORBIDDEN_DATASET_CHARACTERISTICS_METRICS)}}
    ).to_list()
    if bad_metrics:
        issues.append(
            "trovate dataset characteristics dentro ExperimentMetric "
            f"({len(bad_metrics)} record)"
        )

    return issues


async def seed(mode: str = "minimal", reset: bool = False) -> None:
    client = AsyncMongoClient(
        settings.MONGO_HOST,
        settings.MONGO_PORT,
        username=settings.MONGO_USER,
        password=settings.MONGO_PASSWORD,
    )
    await init_beanie(
        database=client[settings.MONGO_DB],
        document_models=DOCUMENT_MODELS,
    )

    if reset:
        print("reset: deleting seeded entities collections...")
        await Metric.delete_all()
        await MetricImportJob.delete_all()
        await Experiment.delete_all()
        await Resource.delete_all()
        await Source.delete_all()
        await DatasetVersion.delete_all()
        await Dataset.delete_all()
        await MLModel.delete_all()
        print("reset: done")

    admin = await _ensure_admin()

    selected_dataset_keys = ["alibaba_ifashion_v1"]
    selected_experiment_fixtures = MINIMAL_EXPERIMENT_FIXTURES
    if mode == "demo":
        selected_dataset_keys = [
            "alibaba_ifashion_v1",
            "epinions_v1",
            "movielens_100k_v1",
        ]
        selected_experiment_fixtures = DEMO_EXPERIMENT_FIXTURES

    datasets: dict[str, Dataset] = {}
    dataset_versions: dict[tuple[str, str], DatasetVersion] = {}
    models: dict[str, MLModel] = {}
    experiments: list[Experiment] = []

    created_datasets = 0
    created_versions = 0
    created_models = 0
    created_experiments = 0
    imported_metrics_jobs = 0

    print(f"mode: {mode}")
    print("datasets:")
    for key in selected_dataset_keys:
        fixture = DATASET_FIXTURES[key]
        dataset, was_created = await _upsert_dataset(fixture, admin)
        datasets[fixture.name] = dataset
        created_datasets += 1 if was_created else 0
        print(f"  - {fixture.name} ({'created' if was_created else 'existing'})")

        dataset_version, version_created = await _upsert_dataset_version(dataset, fixture)
        dataset_versions[(fixture.name, fixture.version)] = dataset_version
        created_versions += 1 if version_created else 0
        print(
            f"    version {fixture.version} "
            f"({'created' if version_created else 'existing'})"
        )

    print("models:")
    for fixture in MODEL_FIXTURES:
        model, was_created = await _upsert_model(fixture, admin)
        models[fixture.name] = model
        created_models += 1 if was_created else 0
        print(f"  - {fixture.name} ({'created' if was_created else 'existing'})")

    print("experiments:")
    for fixture in selected_experiment_fixtures:
        dataset_version = dataset_versions.get(
            (fixture.dataset_name, fixture.dataset_version)
        )
        model = models.get(fixture.model_name)
        if dataset_version is None or model is None:
            print(
                f"  - {fixture.run_name} (skipped: missing dataset version or model)"
            )
            continue

        exp, exp_created = await _upsert_experiment(
            fixture,
            dataset_version,
            model,
            admin,
        )
        created_experiments += 1 if exp_created else 0
        await _sync_experiment_status(exp, fixture.status)

        metrics_imported = False
        if fixture.status == Status.FINISHED:
            metrics_imported = await _import_metrics_from_csv_if_needed(
                exp,
                fixture.metrics,
                admin,
            )
            if metrics_imported:
                imported_metrics_jobs += 1

        experiments.append(exp)
        print(
            f"  - {fixture.run_name} "
            f"({'created' if exp_created else 'existing'}, "
            f"status={fixture.status.value}, "
            f"metrics_csv={'imported' if metrics_imported else 'skipped'})"
        )

    issues = await _consistency_checks(dataset_versions, experiments)

    print("\nsummary:")
    print(f"  datasets_created: {created_datasets}")
    print(f"  dataset_versions_created: {created_versions}")
    print(f"  models_created: {created_models}")
    print(f"  experiments_created: {created_experiments}")
    print(f"  metric_import_jobs_created: {imported_metrics_jobs}")

    if issues:
        print("consistency_issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("consistency_issues: none")

    await client.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed registry-aware polibench data")
    parser.add_argument(
        "--mode",
        choices=["minimal", "demo"],
        default="minimal",
        help="Seed profile: minimal (default) o demo",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Pulisce le collection principali prima del seed",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(seed(mode=args.mode, reset=args.reset))
