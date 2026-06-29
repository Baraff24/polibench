"""
scripts/seed.py
===============

Seed registry-aware allineato al modello DataRec:
- Dataset catalografico
- DatasetVersion con YAML raw (dataset/version/characteristics)
- Source/Resource derivate dal version YAML (via service reale)
- Pipeline separate da DatasetVersion
- Experiment agganciati a Pipeline
- ExperimentMetric importate via CSV + MetricImportJob async

Uso:
  cd backend
  uv run python scripts/seed.py --mode minimal
  uv run python scripts/seed.py --mode demo
  uv run python scripts/seed.py --mode edge
  uv run python scripts/seed.py --mode demo --reset
"""

import argparse
import asyncio
import io
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

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
from app.models.metric_import_jobs import ImportStatus, MetricImportJob
from app.models.metrics import Direction, Metric, Split
from app.models.ml_models import MLModel
from app.models.pipelines import Pipeline, PipelineStatus
from app.models.resources import Resource
from app.models.sources import Source
from app.models.users import User, UserRole
from app.schemas.dataset_versions import DatasetVersionCreate
from app.schemas.datasets import DatasetCreate
from app.schemas.experiments import ExperimentCreate
from app.schemas.ml_models import MLModelCreate
from app.schemas.pipelines import PipelineCreate
from app.services.dataset_versions import create_dataset_version
from app.services.datasets import create_dataset, create_ml_model
from app.services.experiments import create_experiment
from app.services.metric_imports import (
    create_metric_import_job,
    process_metric_import_job,
)
from app.services.pipelines import create_pipeline_for_version

try:
    import yaml
except ImportError:  # pragma: no cover - backend deps include pyyaml
    yaml = None


class SeedMode(str, Enum):
    MINIMAL = "minimal"
    DEMO = "demo"
    EDGE = "edge"


@dataclass(frozen=True)
class UserFixture:
    key: str
    email: str
    password: str
    role: UserRole
    is_superuser: bool = False
    is_verified: bool = True


@dataclass(frozen=True)
class MetricCsvRow:
    split: Split
    metric: str
    value: float
    direction: Direction
    k: int | None = None


@dataclass(frozen=True)
class DatasetFixture:
    key: str
    name: str
    task: TaskType
    description: str
    visibility: Visibility
    version: str
    owner: str = "admin"
    dataset_yaml_raw: str = ""
    version_yaml_raw: str = ""
    characteristics_yaml_raw: str = ""
    pipeline_yaml_raw: str = ""


@dataclass(frozen=True)
class ModelFixture:
    name: str
    family: str
    owner: str = "admin"
    paper_url: str | None = None
    implementation: str | None = None
    hyperparams: dict[str, Any] | None = None


@dataclass(frozen=True)
class PipelineFixture:
    dataset_key: str
    dataset_version: str
    code: str
    pipeline_yaml_raw: str
    status: PipelineStatus = PipelineStatus.READY


@dataclass(frozen=True)
class ExperimentFixture:
    dataset_key: str
    dataset_version: str
    model_name: str
    run_name: str
    seed: int
    status: Status
    pipeline_code: str = "P001"
    submitted_by: str = "admin"
    training_config: dict[str, Any] | None = None
    metrics: list[MetricCsvRow] = field(default_factory=list)


@dataclass(frozen=True)
class SeedScenario:
    datasets: list[DatasetFixture]
    models: list[ModelFixture]
    pipelines: list[PipelineFixture]
    experiments: list[ExperimentFixture]


SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE_ROOT = SCRIPT_DIR / "fixtures" / "datarec_registry"
DATASET_FIXTURES_DIR = FIXTURE_ROOT / "datasets"
VERSION_FIXTURES_DIR = FIXTURE_ROOT / "versions"
METRICS_FIXTURES_DIR = FIXTURE_ROOT / "metrics"


def _require_yaml() -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML non disponibile")
    return yaml


def _read_fixture(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"Fixture non trovata: {path}")
    return path.read_text(encoding="utf-8").strip()


def _dump_yaml(data: dict[str, Any]) -> str:
    parser = _require_yaml()
    return parser.safe_dump(data, sort_keys=False, allow_unicode=True).strip()


def _pipeline_yaml(steps: list[dict[str, Any]]) -> str:
    return _dump_yaml({"pipeline": steps})


def _registry_dataset_name(payload: dict[str, Any], fallback: str) -> str:
    value = payload.get("dataset_name") or payload.get("name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _registry_dataset_description(payload: dict[str, Any], fallback: str) -> str:
    value = payload.get("description")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _make_dataset_fixture(
    *,
    key: str,
    version: str,
    task: TaskType,
    visibility: Visibility,
    owner: str,
    pipeline_steps: list[dict[str, Any]],
) -> DatasetFixture:
    parser = _require_yaml()

    dataset_yaml_raw = _read_fixture(DATASET_FIXTURES_DIR / f"{key}.yml")
    version_yaml_raw = _read_fixture(VERSION_FIXTURES_DIR / f"{key}_{version}.yml")
    characteristics_yaml_raw = _read_fixture(
        METRICS_FIXTURES_DIR / f"{key}_{version}.yml"
    )

    dataset_payload = parser.safe_load(dataset_yaml_raw)
    if not isinstance(dataset_payload, dict):
        raise RuntimeError(f"Dataset YAML non valido per fixture '{key}'")

    return DatasetFixture(
        key=key,
        name=_registry_dataset_name(dataset_payload, key),
        task=task,
        description=_registry_dataset_description(dataset_payload, f"{key} dataset"),
        visibility=visibility,
        version=version,
        owner=owner,
        dataset_yaml_raw=dataset_yaml_raw,
        version_yaml_raw=version_yaml_raw,
        characteristics_yaml_raw=characteristics_yaml_raw,
        pipeline_yaml_raw=_pipeline_yaml(pipeline_steps),
    )


def _ranking_metrics(quality: str) -> list[MetricCsvRow]:
    levels = {
        "baseline": {
            "ndcg@10": (0.052, 10),
            "recall@20": (0.107, 20),
            "hit@10": (0.131, 10),
        },
        "good": {
            "ndcg@10": (0.118, 10),
            "recall@20": (0.183, 20),
            "hit@10": (0.249, 10),
        },
        "best": {
            "ndcg@10": (0.157, 10),
            "recall@20": (0.236, 20),
            "hit@10": (0.311, 10),
        },
    }
    selected = levels[quality]
    rows: list[MetricCsvRow] = []
    for split in (Split.TEST, Split.VALIDATION):
        factor = 1.0 if split == Split.TEST else 0.94
        for metric_name, (base, k) in selected.items():
            rows.append(
                MetricCsvRow(
                    split=split,
                    metric=metric_name,
                    k=k,
                    value=round(base * factor, 6),
                    direction=Direction.MAX,
                )
            )
    return rows


def _rating_metrics(quality: str) -> list[MetricCsvRow]:
    levels = {
        "baseline": {"rmse": 1.038, "mae": 0.824},
        "good": {"rmse": 0.962, "mae": 0.758},
        "best": {"rmse": 0.913, "mae": 0.717},
    }
    selected = levels[quality]
    rows: list[MetricCsvRow] = []
    for split in (Split.TEST, Split.VALIDATION):
        penalty = 0.0 if split == Split.TEST else 0.02
        rows.append(
            MetricCsvRow(
                split=split,
                metric="rmse",
                value=round(selected["rmse"] + penalty, 6),
                direction=Direction.MIN,
            )
        )
        rows.append(
            MetricCsvRow(
                split=split,
                metric="mae",
                value=round(selected["mae"] + penalty * 0.65, 6),
                direction=Direction.MIN,
            )
        )
    return rows


def _amazon_books_tuning_metrics(ndcg_test: float) -> list[MetricCsvRow]:
    ndcg_validation = round(ndcg_test * 0.95, 6)
    recall_test = round(ndcg_test * 1.75, 6)
    recall_validation = round(ndcg_validation * 1.75, 6)
    hit_test = round(ndcg_test * 2.2, 6)
    hit_validation = round(ndcg_validation * 2.2, 6)
    return [
        MetricCsvRow(
            split=Split.TEST,
            metric="ndcg@10",
            value=round(ndcg_test, 6),
            direction=Direction.MAX,
            k=10,
        ),
        MetricCsvRow(
            split=Split.VALIDATION,
            metric="ndcg@10",
            value=ndcg_validation,
            direction=Direction.MAX,
            k=10,
        ),
        MetricCsvRow(
            split=Split.TEST,
            metric="recall@20",
            value=recall_test,
            direction=Direction.MAX,
            k=20,
        ),
        MetricCsvRow(
            split=Split.VALIDATION,
            metric="recall@20",
            value=recall_validation,
            direction=Direction.MAX,
            k=20,
        ),
        MetricCsvRow(
            split=Split.TEST,
            metric="hit@10",
            value=hit_test,
            direction=Direction.MAX,
            k=10,
        ),
        MetricCsvRow(
            split=Split.VALIDATION,
            metric="hit@10",
            value=hit_validation,
            direction=Direction.MAX,
            k=10,
        ),
    ]


def _ranking_custom_metrics(
    *,
    ndcg_test: float,
    recall_test: float,
    hit_test: float,
) -> list[MetricCsvRow]:
    rows: list[MetricCsvRow] = []
    values = {
        "ndcg@10": (ndcg_test, 10),
        "recall@20": (recall_test, 20),
        "hit@10": (hit_test, 10),
    }
    for split in (Split.TEST, Split.VALIDATION):
        factor = 1.0 if split == Split.TEST else 0.95
        for metric_name, (value, k) in values.items():
            rows.append(
                MetricCsvRow(
                    split=split,
                    metric=metric_name,
                    k=k,
                    value=round(value * factor, 6),
                    direction=Direction.MAX,
                )
            )
    return rows


def _rating_custom_metrics(
    *,
    rmse_test: float,
    mae_test: float,
) -> list[MetricCsvRow]:
    return [
        MetricCsvRow(
            split=Split.TEST,
            metric="rmse",
            value=round(rmse_test, 6),
            direction=Direction.MIN,
        ),
        MetricCsvRow(
            split=Split.VALIDATION,
            metric="rmse",
            value=round(rmse_test + 0.018, 6),
            direction=Direction.MIN,
        ),
        MetricCsvRow(
            split=Split.TEST,
            metric="mae",
            value=round(mae_test, 6),
            direction=Direction.MIN,
        ),
        MetricCsvRow(
            split=Split.VALIDATION,
            metric="mae",
            value=round(mae_test + 0.012, 6),
            direction=Direction.MIN,
        ),
    ]


def _ranking_training_config(
    *,
    embedding_dim: int,
    learning_rate: float,
    batch_size: int,
    epochs: int,
    reg: float,
    seed: int,
) -> dict[str, Any]:
    return {
        "embedding_dim": embedding_dim,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "epochs": epochs,
        "reg": reg,
        "seed": seed,
    }


def _rating_training_config(
    *,
    n_factors: int,
    learning_rate: float,
    reg: float,
    epochs: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "n_factors": n_factors,
        "learning_rate": learning_rate,
        "reg": reg,
        "epochs": epochs,
        "seed": seed,
    }


USER_FIXTURES = [
    UserFixture(
        key="admin",
        email=str(settings.FIRST_SUPERUSER),
        password=settings.FIRST_SUPERUSER_PASSWORD,
        role=UserRole.ADMIN,
        is_superuser=True,
        is_verified=True,
    ),
    UserFixture(
        key="researcher",
        email="researcher@polibench.dev",
        password="researcher123",
        role=UserRole.RESEARCHER,
        is_verified=True,
    ),
    UserFixture(
        key="researcher2",
        email="researcher2@polibench.dev",
        password="researcher2123",
        role=UserRole.RESEARCHER,
        is_verified=True,
    ),
    UserFixture(
        key="viewer",
        email="viewer@polibench.dev",
        password="viewer123",
        role=UserRole.VIEWER,
        is_verified=True,
    ),
]


ALIBABA_V1 = _make_dataset_fixture(
    key="alibaba_ifashion",
    version="v1",
    task=TaskType.RANKING,
    visibility=Visibility.PUBLIC,
    owner="admin",
    pipeline_steps=[
        {
            "name": "ingest",
            "operation": "load_sequence",
            "params": {"resource": "interactions"},
        },
        {
            "name": "normalize",
            "operation": "normalize_ids",
            "params": {"encode_ids": True},
        },
        {
            "name": "split",
            "operation": "leave_one_out",
            "params": {"min_interactions": 5},
        },
    ],
)

EPINIONS_V1 = _make_dataset_fixture(
    key="epinions",
    version="v1",
    task=TaskType.RANKING,
    visibility=Visibility.PRIVATE,
    owner="researcher",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_tsv", "params": {"resource": "trust"}},
        {"name": "deduplicate", "operation": "drop_duplicates", "params": {}},
        {"name": "split", "operation": "temporal_split", "params": {"train_ratio": 0.8}},
    ],
)

LASTFM_2011 = _make_dataset_fixture(
    key="lastfm",
    version="2011",
    task=TaskType.RANKING,
    visibility=Visibility.PUBLIC,
    owner="researcher",
    pipeline_steps=[
        {
            "name": "ingest",
            "operation": "parse_tabular",
            "params": {"resource": "ratings"},
        },
        {
            "name": "kcore",
            "operation": "filter_min_interactions",
            "params": {"min_user_interactions": 20},
        },
        {"name": "split", "operation": "leave_one_out", "params": {}},
    ],
)

MOVIELENS_100K = _make_dataset_fixture(
    key="movielens",
    version="100k",
    task=TaskType.RATING_PREDICTION,
    visibility=Visibility.PUBLIC,
    owner="researcher",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_tsv", "params": {"resource": "ratings"}},
        {"name": "normalize", "operation": "normalize_ids", "params": {}},
        {
            "name": "split",
            "operation": "random_split",
            "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
        },
    ],
)

MOVIELENS_1M = _make_dataset_fixture(
    key="movielens",
    version="1m",
    task=TaskType.RATING_PREDICTION,
    visibility=Visibility.PUBLIC,
    owner="researcher",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_dat", "params": {"resource": "ratings"}},
        {
            "name": "kcore",
            "operation": "filter_min_interactions",
            "params": {"min_user_interactions": 5, "min_item_interactions": 5},
        },
        {
            "name": "split",
            "operation": "temporal_split",
            "params": {"train_ratio": 0.82, "validation_ratio": 0.08},
        },
    ],
)

MOVIELENS_20M = _make_dataset_fixture(
    key="movielens",
    version="20m",
    task=TaskType.RATING_PREDICTION,
    visibility=Visibility.PUBLIC,
    owner="researcher",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_csv", "params": {"resource": "ratings"}},
        {
            "name": "kcore",
            "operation": "filter_min_interactions",
            "params": {"min_user_interactions": 10, "min_item_interactions": 10},
        },
        {
            "name": "split",
            "operation": "temporal_split",
            "params": {"train_ratio": 0.85, "validation_ratio": 0.05},
        },
    ],
)

AMAZON_BOOKS_2023 = _make_dataset_fixture(
    key="amazon_books",
    version="2023",
    task=TaskType.RANKING,
    visibility=Visibility.PUBLIC,
    owner="researcher2",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_csv", "params": {"resource": "ratings"}},
        {
            "name": "sanitize",
            "operation": "drop_missing_values",
            "params": {"columns": ["user_id", "parent_asin", "rating"]},
        },
        {
            "name": "split",
            "operation": "temporal_split",
            "params": {"train_ratio": 0.82, "validation_ratio": 0.08},
        },
    ],
)

GOWALLA_CHECKINS = _make_dataset_fixture(
    key="gowalla",
    version="checkins",
    task=TaskType.RANKING,
    visibility=Visibility.PUBLIC,
    owner="researcher2",
    pipeline_steps=[
        {"name": "ingest", "operation": "parse_tsv", "params": {"resource": "checkins"}},
        {
            "name": "sessionize",
            "operation": "sessionize",
            "params": {"max_gap_minutes": 60},
        },
        {"name": "split", "operation": "leave_one_out", "params": {}},
    ],
)

GOWALLA_FRIENDSHIPS = _make_dataset_fixture(
    key="gowalla",
    version="friendships",
    task=TaskType.RANKING,
    visibility=Visibility.PUBLIC,
    owner="researcher2",
    pipeline_steps=[
        {
            "name": "ingest",
            "operation": "parse_tsv",
            "params": {"resource": "ratings"},
        },
        {"name": "normalize", "operation": "normalize_ids", "params": {}},
        {
            "name": "split",
            "operation": "random_split",
            "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
        },
    ],
)

DATASET_FIXTURES_MINIMAL = [ALIBABA_V1]

DATASET_FIXTURES_DEMO = [
    ALIBABA_V1,
    EPINIONS_V1,
    LASTFM_2011,
    MOVIELENS_100K,
    MOVIELENS_1M,
    MOVIELENS_20M,
    AMAZON_BOOKS_2023,
    GOWALLA_CHECKINS,
    GOWALLA_FRIENDSHIPS,
]

DATASET_FIXTURES_EDGE = [MOVIELENS_20M, GOWALLA_FRIENDSHIPS]

MODEL_FIXTURES_MINIMAL = [
    ModelFixture(
        name="LightGCN",
        family="graph-neural-network",
        owner="admin",
        paper_url="https://arxiv.org/abs/2002.02126",
        implementation="https://github.com/gusye1234/LightGCN-PyTorch",
        hyperparams={"embedding_dim": 64, "n_layers": 3, "learning_rate": 0.001},
    )
]

MODEL_FIXTURES_DEMO = [
    *MODEL_FIXTURES_MINIMAL,
    ModelFixture(
        name="BPR-MF",
        family="matrix-factorization",
        owner="researcher",
        paper_url="https://arxiv.org/abs/1205.2618",
        implementation="https://github.com/guoyang9/BPR-pytorch",
        hyperparams={"embedding_dim": 64, "learning_rate": 0.001, "reg": 0.0001},
    ),
    ModelFixture(
        name="SVD",
        family="matrix-factorization",
        owner="researcher",
        paper_url="https://dl.acm.org/doi/10.1145/1401890.1401944",
        implementation="https://surpriselib.com",
        hyperparams={"n_factors": 128, "learning_rate": 0.005, "reg": 0.01},
    ),
    ModelFixture(
        name="UserKNN",
        family="neighborhood",
        owner="researcher2",
        paper_url="https://dl.acm.org/doi/10.1145/371920.372071",
        implementation="https://surpriselib.com",
        hyperparams={"k": 80, "sim": "cosine", "shrinkage": 100},
    ),
    ModelFixture(
        name="PopRank",
        family="baseline",
        owner="admin",
        implementation="https://example.org/models/poprank",
        hyperparams={"strategy": "global_popularity"},
    ),
]

MODEL_FIXTURES_EDGE = [
    *MODEL_FIXTURES_MINIMAL,
    ModelFixture(
        name="RandomBaseline",
        family="baseline",
        owner="admin",
        implementation="https://example.org/models/random-baseline",
        hyperparams={"sampling": "uniform", "seed": 123},
    ),
]

PIPELINE_FIXTURES_MINIMAL: list[PipelineFixture] = []

PIPELINE_FIXTURES_DEMO = [
    PipelineFixture(
        dataset_key="movielens",
        dataset_version="100k",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "ingest",
                    "operation": "parse_tsv",
                    "params": {"resource": "ratings"},
                },
                {
                    "name": "kcore",
                    "operation": "filter_min_interactions",
                    "params": {"min_user_interactions": 10},
                },
                {
                    "name": "split",
                    "operation": "temporal_split",
                    "params": {"train_ratio": 0.82, "validation_ratio": 0.08},
                },
            ]
        ),
    ),
    PipelineFixture(
        dataset_key="movielens",
        dataset_version="1m",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "ingest",
                    "operation": "parse_dat",
                    "params": {"resource": "ratings"},
                },
                {
                    "name": "feature-join",
                    "operation": "join_content",
                    "params": {"resource": "movies"},
                },
                {
                    "name": "split",
                    "operation": "random_split",
                    "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
                },
            ]
        ),
    ),
    PipelineFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "ingest",
                    "operation": "parse_csv",
                    "params": {"resource": "ratings"},
                },
                {
                    "name": "deduplicate",
                    "operation": "drop_duplicates",
                    "params": {"subset": ["user_id", "parent_asin", "timestamp"]},
                },
                {
                    "name": "split",
                    "operation": "leave_one_out",
                    "params": {"min_interactions": 5},
                },
            ]
        ),
    ),
    PipelineFixture(
        dataset_key="lastfm",
        dataset_version="2011",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "ingest",
                    "operation": "parse_tabular",
                    "params": {"resource": "ratings"},
                },
                {
                    "name": "tag-join",
                    "operation": "join_content",
                    "params": {"resource": "tags"},
                },
                {
                    "name": "split",
                    "operation": "temporal_split",
                    "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
                },
            ]
        ),
    ),
]

PIPELINE_FIXTURES_EDGE = [
    PipelineFixture(
        dataset_key="gowalla",
        dataset_version="friendships",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "ingest",
                    "operation": "parse_tsv",
                    "params": {"resource": "ratings"},
                },
                {
                    "name": "split",
                    "operation": "temporal_split",
                    "params": {"train_ratio": 0.85, "validation_ratio": 0.05},
                },
            ]
        ),
    )
]

EXPERIMENT_FIXTURES_MINIMAL = [
    ExperimentFixture(
        dataset_key="alibaba_ifashion",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-minimal-lightgcn-alibaba-v1-finished",
        seed=42,
        status=Status.FINISHED,
        submitted_by="admin",
        training_config=_ranking_training_config(
            embedding_dim=64,
            learning_rate=0.001,
            batch_size=2048,
            epochs=200,
            reg=0.0001,
            seed=42,
        ),
        metrics=_ranking_metrics("good"),
    ),
]

EXPERIMENT_FIXTURES_DEMO = [
    *EXPERIMENT_FIXTURES_MINIMAL,
    ExperimentFixture(
        dataset_key="alibaba_ifashion",
        dataset_version="v1",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-alibaba-v1-finished",
        seed=17,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=64,
            learning_rate=0.001,
            batch_size=1024,
            epochs=150,
            reg=0.0005,
            seed=17,
        ),
        metrics=_ranking_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_key="alibaba_ifashion",
        dataset_version="v1",
        model_name="PopRank",
        run_name="seed-demo-poprank-alibaba-v1-failed",
        seed=18,
        status=Status.FAILED,
        submitted_by="viewer",
        training_config={"strategy": "global_popularity", "seed": 18},
    ),
    ExperimentFixture(
        dataset_key="epinions",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-epinions-v1-finished",
        seed=31,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.0007,
            batch_size=4096,
            epochs=260,
            reg=0.00005,
            seed=31,
        ),
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_key="epinions",
        dataset_version="v1",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-epinions-v1-running",
        seed=32,
        status=Status.RUNNING,
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=96,
            learning_rate=0.0012,
            batch_size=2048,
            epochs=220,
            reg=0.0002,
            seed=32,
        ),
    ),
    ExperimentFixture(
        dataset_key="lastfm",
        dataset_version="2011",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-lastfm-2011-finished",
        seed=41,
        status=Status.FINISHED,
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=64,
            learning_rate=0.001,
            batch_size=512,
            epochs=180,
            reg=0.0003,
            seed=41,
        ),
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_key="lastfm",
        dataset_version="2011",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-lastfm-2011-finished-p2",
        seed=42,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.0008,
            batch_size=1024,
            epochs=240,
            reg=0.0001,
            seed=42,
        ),
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="100k",
        model_name="SVD",
        run_name="seed-demo-svd-ml100k-finished",
        seed=101,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_rating_training_config(
            n_factors=80,
            learning_rate=0.005,
            reg=0.02,
            epochs=50,
            seed=101,
        ),
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="100k",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml100k-finished-p2",
        seed=102,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher2",
        training_config={"k": 80, "sim": "cosine", "shrinkage": 50, "seed": 102},
        metrics=_rating_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="100k",
        model_name="PopRank",
        run_name="seed-demo-poprank-ml100k-queued",
        seed=103,
        status=Status.QUEUED,
        submitted_by="viewer",
        training_config={"strategy": "item_popularity", "seed": 103},
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="1m",
        model_name="SVD",
        run_name="seed-demo-svd-ml1m-finished-p2",
        seed=111,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        training_config=_rating_training_config(
            n_factors=128,
            learning_rate=0.004,
            reg=0.015,
            epochs=60,
            seed=111,
        ),
        metrics=_rating_metrics("best"),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="1m",
        model_name="SVD",
        run_name="seed-demo-bestcfg-svd-ml1m-p1-rmse-best",
        seed=113,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_rating_training_config(
            n_factors=192,
            learning_rate=0.0035,
            reg=0.012,
            epochs=90,
            seed=113,
        ),
        metrics=_rating_custom_metrics(rmse_test=0.889, mae_test=0.706),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="1m",
        model_name="UserKNN",
        run_name="seed-demo-bestcfg-userknn-ml1m-p2-mae-best",
        seed=114,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher2",
        training_config={"k": 140, "sim": "pearson", "shrinkage": 60, "seed": 114},
        metrics=_rating_custom_metrics(rmse_test=0.905, mae_test=0.690),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="1m",
        model_name="SVD",
        run_name="seed-demo-bestcfg-svd-ml1m-p2-regularized",
        seed=115,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="admin",
        training_config=_rating_training_config(
            n_factors=160,
            learning_rate=0.003,
            reg=0.02,
            epochs=80,
            seed=115,
        ),
        metrics=_rating_custom_metrics(rmse_test=0.901, mae_test=0.698),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="1m",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml1m-running",
        seed=112,
        status=Status.RUNNING,
        submitted_by="researcher2",
        training_config={"k": 120, "sim": "pearson", "shrinkage": 80, "seed": 112},
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="20m",
        model_name="SVD",
        run_name="seed-demo-svd-ml20m-finished",
        seed=121,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_rating_training_config(
            n_factors=256,
            learning_rate=0.003,
            reg=0.02,
            epochs=80,
            seed=121,
        ),
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="20m",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml20m-failed",
        seed=122,
        status=Status.FAILED,
        submitted_by="viewer",
        training_config={"k": 160, "sim": "cosine", "shrinkage": 120, "seed": 122},
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-amazon-books-2023-lr1e3-ed64-bs1024",
        seed=201,
        status=Status.FINISHED,
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=64,
            learning_rate=0.001,
            batch_size=1024,
            epochs=180,
            reg=0.0001,
            seed=201,
        ),
        metrics=_amazon_books_tuning_metrics(0.110),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-amazon-books-2023-lr5e4-ed64-bs1024",
        seed=202,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=64,
            learning_rate=0.0005,
            batch_size=1024,
            epochs=180,
            reg=0.0001,
            seed=202,
        ),
        metrics=_amazon_books_tuning_metrics(0.104),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-amazon-books-2023-lr1e3-ed128-bs1024",
        seed=203,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.001,
            batch_size=1024,
            epochs=180,
            reg=0.0001,
            seed=203,
        ),
        metrics=_amazon_books_tuning_metrics(0.118),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-amazon-books-2023-lr1e3-ed128-bs2048",
        seed=204,
        status=Status.FINISHED,
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.001,
            batch_size=2048,
            epochs=180,
            reg=0.0001,
            seed=204,
        ),
        metrics=_amazon_books_tuning_metrics(0.115),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="LightGCN",
        run_name="seed-demo-bestcfg-lightgcn-amazon-books-2023-p2-ndcg-best",
        seed=206,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=192,
            learning_rate=0.0008,
            batch_size=2048,
            epochs=220,
            reg=0.00008,
            seed=206,
        ),
        metrics=_ranking_custom_metrics(
            ndcg_test=0.127,
            recall_test=0.214,
            hit_test=0.286,
        ),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="BPR-MF",
        run_name="seed-demo-bestcfg-bpr-amazon-books-2023-p1-balanced",
        seed=207,
        status=Status.FINISHED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.001,
            batch_size=1024,
            epochs=180,
            reg=0.0003,
            seed=207,
        ),
        metrics=_ranking_custom_metrics(
            ndcg_test=0.121,
            recall_test=0.206,
            hit_test=0.271,
        ),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="BPR-MF",
        run_name="seed-demo-bestcfg-bpr-amazon-books-2023-p2-recall-best",
        seed=208,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=96,
            learning_rate=0.0007,
            batch_size=4096,
            epochs=240,
            reg=0.0002,
            seed=208,
        ),
        metrics=_ranking_custom_metrics(
            ndcg_test=0.114,
            recall_test=0.232,
            hit_test=0.262,
        ),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="PopRank",
        run_name="seed-demo-bestcfg-poprank-amazon-books-2023-finished",
        seed=209,
        status=Status.FINISHED,
        submitted_by="viewer",
        training_config={"strategy": "global_popularity", "seed": 209},
        metrics=_ranking_custom_metrics(
            ndcg_test=0.071,
            recall_test=0.153,
            hit_test=0.181,
        ),
    ),
    ExperimentFixture(
        dataset_key="amazon_books",
        dataset_version="2023",
        model_name="PopRank",
        run_name="seed-demo-poprank-amazon-books-2023-running",
        seed=205,
        status=Status.RUNNING,
        submitted_by="viewer",
        training_config={"strategy": "global_popularity", "seed": 205},
    ),
    ExperimentFixture(
        dataset_key="gowalla",
        dataset_version="checkins",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-gowalla-checkins-finished",
        seed=301,
        status=Status.FINISHED,
        submitted_by="researcher2",
        training_config=_ranking_training_config(
            embedding_dim=128,
            learning_rate=0.0009,
            batch_size=8192,
            epochs=260,
            reg=0.0001,
            seed=301,
        ),
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_key="gowalla",
        dataset_version="checkins",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-gowalla-checkins-finished-p2",
        seed=302,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=96,
            learning_rate=0.001,
            batch_size=4096,
            epochs=220,
            reg=0.0002,
            seed=302,
        ),
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_key="gowalla",
        dataset_version="friendships",
        model_name="PopRank",
        run_name="seed-demo-poprank-gowalla-friendships-finished",
        seed=311,
        status=Status.FINISHED,
        submitted_by="viewer",
        training_config={"strategy": "global_popularity", "seed": 311},
        metrics=_ranking_metrics("baseline"),
    ),
]

EXPERIMENT_FIXTURES_EDGE = [
    ExperimentFixture(
        dataset_key="gowalla",
        dataset_version="friendships",
        model_name="RandomBaseline",
        run_name="seed-edge-random-gowalla-friendships-finished",
        seed=401,
        status=Status.FINISHED,
        submitted_by="admin",
        training_config={"sampling": "uniform", "temperature": 1.0, "seed": 401},
        metrics=[
            MetricCsvRow(Split.TEST, "ndcg@10", 0.031, Direction.MAX, k=10),
            MetricCsvRow(Split.TEST, "recall@20", 0.059, Direction.MAX, k=20),
            MetricCsvRow(Split.TEST, "hit@10", 0.081, Direction.MAX, k=10),
        ],
    ),
    ExperimentFixture(
        dataset_key="movielens",
        dataset_version="20m",
        model_name="LightGCN",
        run_name="seed-edge-lightgcn-ml20m-failed",
        seed=402,
        status=Status.FAILED,
        submitted_by="researcher",
        training_config=_ranking_training_config(
            embedding_dim=256,
            learning_rate=0.0005,
            batch_size=16384,
            epochs=300,
            reg=0.00005,
            seed=402,
        ),
    ),
]

SEED_SCENARIOS: dict[SeedMode, SeedScenario] = {
    SeedMode.MINIMAL: SeedScenario(
        datasets=DATASET_FIXTURES_MINIMAL,
        models=MODEL_FIXTURES_MINIMAL,
        pipelines=PIPELINE_FIXTURES_MINIMAL,
        experiments=EXPERIMENT_FIXTURES_MINIMAL,
    ),
    SeedMode.DEMO: SeedScenario(
        datasets=DATASET_FIXTURES_DEMO,
        models=MODEL_FIXTURES_DEMO,
        pipelines=PIPELINE_FIXTURES_DEMO,
        experiments=EXPERIMENT_FIXTURES_DEMO,
    ),
    SeedMode.EDGE: SeedScenario(
        datasets=DATASET_FIXTURES_EDGE,
        models=MODEL_FIXTURES_EDGE,
        pipelines=PIPELINE_FIXTURES_EDGE,
        experiments=EXPERIMENT_FIXTURES_EDGE,
    ),
}

FORBIDDEN_DATASET_CHARACTERISTICS_METRICS = {
    "n_users",
    "n_items",
    "n_interactions",
    "density",
    "gini_user",
    "gini_item",
}


def _select_scenario(mode: str) -> SeedScenario:
    return SEED_SCENARIOS[SeedMode(mode)]


def _metrics_to_csv(rows: list[MetricCsvRow]) -> str:
    lines = ["split,metric,k,value,direction"]
    for row in rows:
        k_value = "" if row.k is None else str(row.k)
        lines.append(
            f"{row.split.value},{row.metric},{k_value},{row.value:.6f},{row.direction.value}"
        )
    return "\n".join(lines) + "\n"


async def _ensure_user(fixture: UserFixture) -> User:
    user = await User.find_one(User.email == fixture.email)
    if user is None:
        user = User(
            email=fixture.email,
            hashed_password=get_hashed_password(fixture.password),
            role=fixture.role,
            is_verified=fixture.is_verified,
            is_superuser=fixture.is_superuser,
        )
        await user.create()
        return user

    changed = False
    if user.role != fixture.role:
        user.role = fixture.role
        changed = True
    if user.is_superuser != fixture.is_superuser:
        user.is_superuser = fixture.is_superuser
        changed = True
    if user.is_verified is not True and fixture.is_verified:
        user.is_verified = True
        changed = True
    if user.hashed_password is None:
        user.hashed_password = get_hashed_password(fixture.password)
        changed = True
    if changed:
        await user.save()
    return user


async def _ensure_seed_users() -> dict[str, User]:
    out: dict[str, User] = {}
    for fixture in USER_FIXTURES:
        user = await _ensure_user(fixture)
        out[fixture.key] = user
    return out


def _require_user(user_map: dict[str, User], key: str) -> User:
    user = user_map.get(key)
    if user is None:
        raise RuntimeError(f"Utente seed '{key}' non trovato")
    return user


async def _upsert_dataset(fixture: DatasetFixture, owner: User) -> tuple[Dataset, bool]:
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
        owner,
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
            f"DatasetVersion appena creata non trovata: {fixture.key} {fixture.version}"
        )
    return created, True


async def _upsert_model(fixture: ModelFixture, owner: User) -> tuple[MLModel, bool]:
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
        owner,
    )
    created = await MLModel.find_one(MLModel.uuid == public.uuid)
    if created is None:
        raise RuntimeError(f"MLModel appena creato non trovato: {fixture.name}")
    return created, True


async def _upsert_pipeline(
    fixture: PipelineFixture,
    dataset_version: DatasetVersion,
) -> tuple[Pipeline, bool]:
    existing = await Pipeline.find_one(
        {"dataset_version_id": dataset_version.id, "code": fixture.code}
    )
    if existing is not None:
        return existing, False

    public = await create_pipeline_for_version(
        dataset_version.uuid,
        PipelineCreate(
            code=fixture.code,
            yaml_raw=fixture.pipeline_yaml_raw,
            status=fixture.status,
        ),
    )
    created = await Pipeline.find_one(Pipeline.uuid == public.uuid)
    if created is None:
        raise RuntimeError(f"Pipeline appena creata non trovata: {fixture.code}")
    return created, True


async def _upsert_experiment(
    fixture: ExperimentFixture,
    pipeline: Pipeline,
    dataset_version: DatasetVersion,
    model: MLModel,
    submitter: User,
) -> tuple[Experiment, bool]:
    existing = await Experiment.find_one(Experiment.run_name == fixture.run_name)
    if existing is not None:
        changed = False
        if existing.pipeline_id is None:
            existing.pipeline_id = pipeline.id
            changed = True
        if existing.dataset_id is None:
            existing.dataset_id = dataset_version.dataset_id
            changed = True
        if existing.training_config is None and fixture.training_config is not None:
            existing.training_config = fixture.training_config
            changed = True
        if changed:
            await existing.save()
        return existing, False

    public = await create_experiment(
        ExperimentCreate(
            pipeline_uuid=pipeline.uuid,
            model_uuid=model.uuid,
            run_name=fixture.run_name,
            seed=fixture.seed,
            training_config=fixture.training_config or model.hyperparams,
            notes="Seeded via scripts/seed.py (demo metrics are synthetic CSV rows)",
        ),
        submitter,
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
    submitter: User,
) -> bool:
    if not rows:
        return False

    already_present = await Metric.find(Metric.experiment_id == exp.id).count()
    if already_present > 0:
        return False

    upload = UploadFile(
        io.BytesIO(_metrics_to_csv(rows).encode("utf-8")),
        filename=f"{exp.run_name or exp.uuid}.csv",
    )
    job = await create_metric_import_job(exp.uuid, upload, submitter)
    await process_metric_import_job(job.uuid)
    return True


async def _consistency_checks(
    dataset_versions: dict[tuple[str, str], DatasetVersion],
    pipelines: dict[tuple[str, str, str], Pipeline],
    experiments: list[Experiment],
) -> list[str]:
    issues: list[str] = []

    for (dataset_key, version_name), version in dataset_versions.items():
        if version.status != VersionStatus.READY:
            continue
        if await Dataset.get(version.dataset_id) is None:
            issues.append(
                f"dataset mancante per DatasetVersion {dataset_key}:{version_name}"
            )

        sources_count = await Source.find(Source.dataset_version_id == version.id).count()
        resources_count = await Resource.find(
            Resource.dataset_version_id == version.id
        ).count()
        if sources_count == 0 and resources_count == 0:
            issues.append(
                "ready DatasetVersion senza sources/resources: "
                f"{dataset_key}:{version_name}"
            )

    for exp in experiments:
        if await DatasetVersion.get(exp.dataset_version_id) is None:
            issues.append(f"experiment senza dataset_version valido: {exp.run_name}")
        if exp.pipeline_id is None:
            issues.append(f"experiment senza pipeline valida: {exp.run_name}")
            continue
        pipeline = await Pipeline.get(exp.pipeline_id)
        if pipeline is None:
            issues.append(f"experiment con pipeline non trovata: {exp.run_name}")
            continue
        if pipeline.dataset_version_id != exp.dataset_version_id:
            issues.append(
                "experiment con pipeline non coerente rispetto alla dataset_version: "
                f"{exp.run_name}"
            )

    for (dataset_key, version_name, pipeline_code), pipeline in pipelines.items():
        if await DatasetVersion.get(pipeline.dataset_version_id) is None:
            issues.append(
                "pipeline senza dataset_version valida: "
                f"{dataset_key}:{version_name}:{pipeline_code}"
            )

    bad_metrics = await Metric.find(
        {"metric": {"$in": list(FORBIDDEN_DATASET_CHARACTERISTICS_METRICS)}}
    ).to_list()
    if bad_metrics:
        issues.append(
            "trovate dataset characteristics dentro ExperimentMetric "
            f"({len(bad_metrics)} record)"
        )

    return issues


async def seed(mode: str = SeedMode.MINIMAL.value, reset: bool = False) -> None:
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
        await Pipeline.delete_all()
        await Resource.delete_all()
        await Source.delete_all()
        await DatasetVersion.delete_all()
        await Dataset.delete_all()
        await MLModel.delete_all()
        print("reset: done")

    scenario = _select_scenario(mode)
    user_map = await _ensure_seed_users()

    datasets: dict[str, Dataset] = {}
    dataset_versions: dict[tuple[str, str], DatasetVersion] = {}
    pipelines: dict[tuple[str, str, str], Pipeline] = {}
    models: dict[str, MLModel] = {}
    experiments: list[Experiment] = []

    created_datasets = 0
    created_versions = 0
    created_models = 0
    created_pipelines = 0
    created_experiments = 0
    created_sources = 0
    created_resources = 0
    imported_metrics_jobs = 0

    print(f"mode: {mode}")
    print("datasets:")
    for fixture in scenario.datasets:
        owner = _require_user(user_map, fixture.owner)
        dataset, was_created = await _upsert_dataset(fixture, owner)
        datasets[fixture.key] = dataset
        created_datasets += 1 if was_created else 0
        print(
            f"  - {fixture.name} ({fixture.version}) "
            f"[{fixture.visibility.value}] owner={fixture.owner} "
            f"({'created' if was_created else 'existing'})"
        )

        dataset_version, version_created = await _upsert_dataset_version(dataset, fixture)
        dataset_versions[(fixture.key, fixture.version)] = dataset_version
        created_versions += 1 if version_created else 0
        if version_created:
            created_sources += await Source.find(
                Source.dataset_version_id == dataset_version.id
            ).count()
            created_resources += await Resource.find(
                Resource.dataset_version_id == dataset_version.id
            ).count()
        print(
            f"    version {fixture.version} "
            f"({'created' if version_created else 'existing'})"
        )

        existing_pipelines = await Pipeline.find(
            Pipeline.dataset_version_id == dataset_version.id
        ).to_list()
        for existing_pipeline in existing_pipelines:
            pipelines[(fixture.key, fixture.version, existing_pipeline.code)] = (
                existing_pipeline
            )

        has_pipeline_for_version = any(
            key[0] == fixture.key and key[1] == fixture.version for key in pipelines
        )
        if not has_pipeline_for_version and fixture.pipeline_yaml_raw.strip():
            base_pipeline_fixture = PipelineFixture(
                dataset_key=fixture.key,
                dataset_version=fixture.version,
                code="P001",
                pipeline_yaml_raw=fixture.pipeline_yaml_raw,
                status=PipelineStatus.READY,
            )
            base_pipeline, base_pipeline_created = await _upsert_pipeline(
                base_pipeline_fixture,
                dataset_version,
            )
            pipelines[(fixture.key, fixture.version, base_pipeline.code)] = base_pipeline
            created_pipelines += 1 if base_pipeline_created else 0

    print("pipelines:")
    for fixture in scenario.pipelines:
        dataset_version = dataset_versions.get(
            (fixture.dataset_key, fixture.dataset_version)
        )
        if dataset_version is None:
            print(
                f"  - {fixture.code} ({fixture.dataset_key}:{fixture.dataset_version}) "
                "(skipped: missing dataset version)"
            )
            continue

        pipeline, was_created = await _upsert_pipeline(fixture, dataset_version)
        pipelines[(fixture.dataset_key, fixture.dataset_version, fixture.code)] = pipeline
        created_pipelines += 1 if was_created else 0
        print(
            f"  - {fixture.code} ({fixture.dataset_key}:{fixture.dataset_version}) "
            f"({'created' if was_created else 'existing'})"
        )

    print("models:")
    for fixture in scenario.models:
        owner = _require_user(user_map, fixture.owner)
        model, was_created = await _upsert_model(fixture, owner)
        models[fixture.name] = model
        created_models += 1 if was_created else 0
        print(
            f"  - {fixture.name} family={fixture.family} owner={fixture.owner} "
            f"({'created' if was_created else 'existing'})"
        )

    print("experiments:")
    for fixture in scenario.experiments:
        dataset_version = dataset_versions.get(
            (fixture.dataset_key, fixture.dataset_version)
        )
        pipeline = pipelines.get(
            (fixture.dataset_key, fixture.dataset_version, fixture.pipeline_code)
        )
        model = models.get(fixture.model_name)
        if dataset_version is None or pipeline is None or model is None:
            print(
                f"  - {fixture.run_name} "
                "(skipped: missing dataset version, pipeline or model)"
            )
            continue

        submitter = _require_user(user_map, fixture.submitted_by)
        exp, exp_created = await _upsert_experiment(
            fixture,
            pipeline,
            dataset_version,
            model,
            submitter,
        )
        created_experiments += 1 if exp_created else 0
        await _sync_experiment_status(exp, fixture.status)

        metrics_imported = False
        if fixture.status == Status.FINISHED:
            metrics_imported = await _import_metrics_from_csv_if_needed(
                exp,
                fixture.metrics,
                submitter,
            )
            if metrics_imported:
                imported_metrics_jobs += 1

        experiments.append(exp)
        print(
            f"  - {fixture.run_name} status={fixture.status.value} "
            f"pipeline={fixture.pipeline_code} submitter={fixture.submitted_by} "
            f"({'created' if exp_created else 'existing'}, "
            f"metrics_csv={'imported' if metrics_imported else 'skipped'})"
        )

    issues = await _consistency_checks(dataset_versions, pipelines, experiments)

    status_counts = Counter(e.status.value for e in experiments)
    total_sources = await Source.find_all().count()
    total_resources = await Resource.find_all().count()
    total_pipelines = await Pipeline.find_all().count()
    completed_jobs = await MetricImportJob.find(
        MetricImportJob.status == ImportStatus.COMPLETED
    ).count()

    print("\nsummary:")
    print(f"  datasets_created: {created_datasets}")
    print(f"  dataset_versions_created: {created_versions}")
    print(f"  sources_created: {created_sources}")
    print(f"  resources_created: {created_resources}")
    print(f"  models_created: {created_models}")
    print(f"  pipelines_created: {created_pipelines}")
    print(f"  experiments_created: {created_experiments}")
    print(f"  experiments_by_status: {dict(status_counts)}")
    print(f"  metric_import_jobs_created: {imported_metrics_jobs}")
    print(f"  metric_import_jobs_completed_total: {completed_jobs}")
    print(f"  sources_total: {total_sources}")
    print(f"  resources_total: {total_resources}")
    print(f"  pipelines_total: {total_pipelines}")

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
        choices=[mode.value for mode in SeedMode],
        default=SeedMode.MINIMAL.value,
        help="Seed profile: minimal, demo, edge",
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
