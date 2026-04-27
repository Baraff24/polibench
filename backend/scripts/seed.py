"""
scripts/seed.py
===============

Seed registry-aware allineato al modello DataRec:
- Dataset catalografico
- DatasetVersion con YAML raw (dataset/version/characteristics/pipeline)
- Source/Resource derivate dal version YAML (via service reale)
- Experiment agganciati a DatasetVersion
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
    dataset_name: str
    dataset_version: str
    code: str
    pipeline_yaml_raw: str
    status: PipelineStatus = PipelineStatus.READY


@dataclass(frozen=True)
class ExperimentFixture:
    dataset_name: str
    dataset_version: str
    model_name: str
    run_name: str
    seed: int
    status: Status
    pipeline_code: str = "P001"
    submitted_by: str = "admin"
    metrics: list[MetricCsvRow] = field(default_factory=list)


@dataclass(frozen=True)
class SeedScenario:
    datasets: list[DatasetFixture]
    models: list[ModelFixture]
    pipelines: list[PipelineFixture]
    experiments: list[ExperimentFixture]


def _dump_yaml(data: dict[str, Any]) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML non disponibile: impossibile generare fixture YAML")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()


def _dataset_yaml(
    name: str,
    versions: list[str],
    latest_version: str,
    description: str,
    citation: str,
) -> str:
    return _dump_yaml(
        {
            "name": name,
            "versions": versions,
            "latest_version": latest_version,
            "source": "DataRecHub",
            "description": description,
            "citation": citation,
        }
    )


def _version_yaml(
    dataset_name: str,
    version: str,
    sources: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> str:
    return _dump_yaml(
        {
            "dataset_name": dataset_name,
            "version": version,
            "sources": sources,
            "resources": resources,
        }
    )


def _characteristics_yaml(
    dataset_name: str,
    version: str,
    n_users: int,
    n_items: int,
    n_interactions: int,
    density: float,
    gini_user: float,
    gini_item: float,
) -> str:
    return _dump_yaml(
        {
            "dataset_name": dataset_name,
            "version": version,
            "characteristics": {
                "n_users": n_users,
                "n_items": n_items,
                "n_interactions": n_interactions,
                "density": density,
                "gini_user": gini_user,
                "gini_item": gini_item,
            },
        }
    )


def _pipeline_yaml(steps: list[dict[str, Any]]) -> str:
    return _dump_yaml({"pipeline": steps})


def _ranking_metrics(quality: str) -> list[MetricCsvRow]:
    levels = {
        "baseline": {
            "recall@10": 0.080,
            "ndcg@10": 0.050,
            "map@10": 0.039,
            "hitrate@10": 0.120,
        },
        "good": {
            "recall@10": 0.160,
            "ndcg@10": 0.110,
            "map@10": 0.091,
            "hitrate@10": 0.220,
        },
        "best": {
            "recall@10": 0.210,
            "ndcg@10": 0.151,
            "map@10": 0.131,
            "hitrate@10": 0.291,
        },
    }
    selected = levels[quality]
    rows: list[MetricCsvRow] = []
    for split in (Split.TEST, Split.VALIDATION):
        factor = 1.0 if split == Split.TEST else 0.93
        for metric_name, base in selected.items():
            rows.append(
                MetricCsvRow(
                    split=split,
                    metric=metric_name,
                    k=10,
                    value=round(base * factor, 6),
                    direction=Direction.MAX,
                )
            )
    return rows


def _rating_metrics(quality: str) -> list[MetricCsvRow]:
    levels = {
        "baseline": {"rmse": 1.020, "mae": 0.810},
        "good": {"rmse": 0.940, "mae": 0.745},
        "best": {"rmse": 0.902, "mae": 0.705},
    }
    selected = levels[quality]
    rows: list[MetricCsvRow] = []
    for split in (Split.TEST, Split.VALIDATION):
        penalty = 0.0 if split == Split.TEST else 0.018
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
                value=round(selected["mae"] + penalty * 0.7, 6),
                direction=Direction.MIN,
            )
        )
    return rows


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
        key="viewer",
        email="viewer@polibench.dev",
        password="viewer123",
        role=UserRole.VIEWER,
        is_verified=True,
    ),
]

MOVIELENS_VERSIONS = ["v1", "v2", "v3"]
ALIBABA_VERSIONS = ["v1", "v2"]
EPINIONS_VERSIONS = ["v1", "v2"]
AMAZON_BOOKS_VERSIONS = ["2023", "2024"]
LASTFM_VERSIONS = ["2011", "2014"]

ALIBABA_V1 = DatasetFixture(
    name="Alibaba-iFashion",
    task=TaskType.RANKING,
    description="Fashion recommendation benchmark with implicit feedback.",
    visibility=Visibility.PUBLIC,
    version="v1",
    owner="admin",
    dataset_yaml_raw=_dataset_yaml(
        name="Alibaba-iFashion",
        versions=ALIBABA_VERSIONS,
        latest_version="v2",
        description="Fashion recommendation benchmark.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Alibaba-iFashion",
        version="v1",
        sources=[
            {
                "name": "raw-archive",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/alibaba_ifashion_v1.zip",
                "filename": "alibaba_ifashion_v1.zip",
                "checksum": "sha256:abc123",
                "checksum_algorithm": "sha256",
            }
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "raw-archive",
                "type": "interactions",
                "format": "csv",
                "required": True,
            },
            {
                "name": "items",
                "source_name": "raw-archive",
                "type": "item_features",
                "format": "csv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Alibaba-iFashion",
        version="v1",
        n_users=62010,
        n_items=35402,
        n_interactions=781453,
        density=0.000356,
        gini_user=0.612,
        gini_item=0.701,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {
                "name": "ingest",
                "operation": "load_csv",
                "params": {"file": "interactions.csv"},
            },
            {
                "name": "normalize",
                "operation": "normalize_ids",
                "params": {"user_col": "user_id", "item_col": "item_id"},
            },
            {
                "name": "split",
                "operation": "leave_one_out",
                "params": {"min_interactions": 5},
            },
        ]
    ),
)

ALIBABA_V2 = DatasetFixture(
    name="Alibaba-iFashion",
    task=TaskType.RANKING,
    description="Fashion recommendation benchmark with implicit feedback.",
    visibility=Visibility.PUBLIC,
    version="v2",
    owner="admin",
    dataset_yaml_raw=_dataset_yaml(
        name="Alibaba-iFashion",
        versions=ALIBABA_VERSIONS,
        latest_version="v2",
        description="Fashion recommendation benchmark.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Alibaba-iFashion",
        version="v2",
        sources=[
            {
                "name": "raw-archive-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/alibaba_ifashion_v2.zip",
                "filename": "alibaba_ifashion_v2.zip",
                "checksum": "sha256:abc124",
                "checksum_algorithm": "sha256",
            },
            {
                "name": "metadata-sidecar-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/alibaba_ifashion_v2_sidecar.zip",
                "filename": "alibaba_ifashion_v2_sidecar.zip",
            },
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "raw-archive-v2",
                "type": "interactions",
                "format": "csv",
                "required": True,
            },
            {
                "name": "items",
                "source_name": "metadata-sidecar-v2",
                "type": "item_features",
                "format": "csv",
                "required": False,
            },
            {
                "name": "category_graph",
                "source_name": "metadata-sidecar-v2",
                "type": "graph",
                "format": "csv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Alibaba-iFashion",
        version="v2",
        n_users=70245,
        n_items=41510,
        n_interactions=912340,
        density=0.000312,
        gini_user=0.598,
        gini_item=0.688,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {
                "name": "ingest",
                "operation": "load_csv",
                "params": {"file": "interactions.csv"},
            },
            {
                "name": "deduplicate",
                "operation": "drop_duplicates",
                "params": {"subset": ["user_id", "item_id", "timestamp"]},
            },
            {
                "name": "kcore",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 5, "min_item_interactions": 5},
            },
            {
                "name": "feature-join",
                "operation": "join_item_features",
                "params": {"resource": "items"},
            },
            {
                "name": "split",
                "operation": "leave_one_out",
                "params": {"min_interactions": 5},
            },
        ]
    ),
)

EPINIONS_V1_PRIVATE = DatasetFixture(
    name="Epinions",
    task=TaskType.RANKING,
    description="Trust-aware recommendation benchmark from Epinions.",
    visibility=Visibility.PRIVATE,
    version="v1",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="Epinions",
        versions=EPINIONS_VERSIONS,
        latest_version="v2",
        description="Epinions trust/review benchmark.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Epinions",
        version="v1",
        sources=[
            {
                "name": "epinions-main",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/epinions_v1.tar.gz",
                "filename": "epinions_v1.tar.gz",
            }
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "epinions-main",
                "type": "interactions",
                "format": "tsv",
                "required": True,
            },
            {
                "name": "trust_network",
                "source_name": "epinions-main",
                "type": "graph",
                "format": "tsv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Epinions",
        version="v1",
        n_users=40163,
        n_items=139738,
        n_interactions=664824,
        density=0.000118,
        gini_user=0.674,
        gini_item=0.752,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "parse", "operation": "parse_tsv", "params": {"delimiter": "\\t"}},
            {"name": "clean", "operation": "drop_duplicates", "params": {}},
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.8},
            },
        ]
    ),
)

EPINIONS_V2_PRIVATE = DatasetFixture(
    name="Epinions",
    task=TaskType.RANKING,
    description="Trust-aware recommendation benchmark from Epinions.",
    visibility=Visibility.PRIVATE,
    version="v2",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="Epinions",
        versions=EPINIONS_VERSIONS,
        latest_version="v2",
        description="Epinions trust/review benchmark.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Epinions",
        version="v2",
        sources=[
            {
                "name": "epinions-main-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/epinions_v2.tar.gz",
                "filename": "epinions_v2.tar.gz",
                "checksum": "sha256:epinions-v2",
                "checksum_algorithm": "sha256",
            },
            {
                "name": "epinions-trust-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/epinions_trust_v2.tsv.gz",
                "filename": "epinions_trust_v2.tsv.gz",
            },
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "epinions-main-v2",
                "type": "interactions",
                "format": "tsv",
                "required": True,
            },
            {
                "name": "trust_network",
                "source_name": "epinions-trust-v2",
                "type": "graph",
                "format": "tsv",
                "required": False,
            },
            {
                "name": "review_metadata",
                "source_name": "epinions-main-v2",
                "type": "item_features",
                "format": "tsv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Epinions",
        version="v2",
        n_users=42890,
        n_items=150342,
        n_interactions=744512,
        density=0.000115,
        gini_user=0.661,
        gini_item=0.739,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "parse", "operation": "parse_tsv", "params": {"delimiter": "\\t"}},
            {
                "name": "kcore",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 3},
            },
            {
                "name": "trust-link",
                "operation": "join_graph_features",
                "params": {"resource": "trust_network"},
            },
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.82},
            },
        ]
    ),
)

MOVIELENS_100K_V1 = DatasetFixture(
    name="MovieLens-100K",
    task=TaskType.RATING_PREDICTION,
    description="Classic explicit-feedback benchmark for rating prediction.",
    visibility=Visibility.PUBLIC,
    version="v1",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="MovieLens-100K",
        versions=MOVIELENS_VERSIONS,
        latest_version="v3",
        description="MovieLens 100K multi-version benchmark.",
        citation="GroupLens Research",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="MovieLens-100K",
        version="v1",
        sources=[
            {
                "name": "ml100k-main-v1",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/movielens_100k_v1.zip",
                "filename": "movielens_100k_v1.zip",
            }
        ],
        resources=[
            {
                "name": "ratings",
                "source_name": "ml100k-main-v1",
                "type": "interactions",
                "format": "csv",
                "required": True,
            }
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="MovieLens-100K",
        version="v1",
        n_users=943,
        n_items=1682,
        n_interactions=100000,
        density=0.063046,
        gini_user=0.321,
        gini_item=0.417,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "load", "operation": "load_csv", "params": {"file": "ratings.csv"}},
            {
                "name": "split",
                "operation": "random_split",
                "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
            },
        ]
    ),
)

MOVIELENS_100K_V2 = DatasetFixture(
    name="MovieLens-100K",
    task=TaskType.RATING_PREDICTION,
    description="Classic explicit-feedback benchmark for rating prediction.",
    visibility=Visibility.PUBLIC,
    version="v2",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="MovieLens-100K",
        versions=MOVIELENS_VERSIONS,
        latest_version="v3",
        description="MovieLens 100K multi-version benchmark.",
        citation="GroupLens Research",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="MovieLens-100K",
        version="v2",
        sources=[
            {
                "name": "ml100k-main-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/movielens_100k_v2.zip",
                "filename": "movielens_100k_v2.zip",
                "checksum": "sha256:ml100k-v2",
                "checksum_algorithm": "sha256",
            },
            {
                "name": "ml100k-docs-v2",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/movielens_100k_v2_readme.txt",
                "filename": "movielens_100k_v2_readme.txt",
            },
        ],
        resources=[
            {
                "name": "ratings",
                "source_name": "ml100k-main-v2",
                "type": "interactions",
                "format": "csv",
                "required": True,
            },
            {
                "name": "item_metadata",
                "source_name": "ml100k-main-v2",
                "type": "item_features",
                "format": "csv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="MovieLens-100K",
        version="v2",
        n_users=980,
        n_items=1720,
        n_interactions=108500,
        density=0.06437,
        gini_user=0.338,
        gini_item=0.431,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "load", "operation": "load_csv", "params": {"file": "ratings.csv"}},
            {
                "name": "filter",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 5},
            },
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
            },
        ]
    ),
)

MOVIELENS_100K_V3 = DatasetFixture(
    name="MovieLens-100K",
    task=TaskType.RATING_PREDICTION,
    description="Classic explicit-feedback benchmark for rating prediction.",
    visibility=Visibility.PUBLIC,
    version="v3",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="MovieLens-100K",
        versions=MOVIELENS_VERSIONS,
        latest_version="v3",
        description="MovieLens 100K multi-version benchmark.",
        citation="GroupLens Research",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="MovieLens-100K",
        version="v3",
        sources=[
            {
                "name": "ml100k-main-v3",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/movielens_100k_v3.zip",
                "filename": "movielens_100k_v3.zip",
            },
            {
                "name": "ml100k-sidecar-v3",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/movielens_100k_v3_sidecar.zip",
                "filename": "movielens_100k_v3_sidecar.zip",
            },
        ],
        resources=[
            {
                "name": "ratings",
                "source_name": "ml100k-main-v3",
                "type": "interactions",
                "format": "csv",
                "required": True,
            },
            {
                "name": "item_metadata",
                "source_name": "ml100k-main-v3",
                "type": "item_features",
                "format": "csv",
                "required": False,
            },
            {
                "name": "genre_graph",
                "source_name": "ml100k-sidecar-v3",
                "type": "graph",
                "format": "csv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="MovieLens-100K",
        version="v3",
        n_users=1015,
        n_items=1764,
        n_interactions=113200,
        density=0.06318,
        gini_user=0.341,
        gini_item=0.439,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "load", "operation": "load_csv", "params": {"file": "ratings.csv"}},
            {
                "name": "filter",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 5, "min_item_interactions": 10},
            },
            {"name": "normalize", "operation": "normalize_ids", "params": {}},
            {
                "name": "feature-join",
                "operation": "join_item_features",
                "params": {"resource": "item_metadata"},
            },
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.82, "validation_ratio": 0.08},
            },
        ]
    ),
)

AMAZON_BOOKS_V2023 = DatasetFixture(
    name="Amazon-Books",
    task=TaskType.RATING_PREDICTION,
    description="Amazon Books benchmark for explicit-feedback recommendation.",
    visibility=Visibility.PUBLIC,
    version="2023",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="Amazon-Books",
        versions=AMAZON_BOOKS_VERSIONS,
        latest_version="2024",
        description="Amazon Books benchmark with yearly snapshots.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Amazon-Books",
        version="2023",
        sources=[
            {
                "name": "amazon-books-2023",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/amazon_books_2023.parquet",
                "filename": "amazon_books_2023.parquet",
                "checksum": "sha256:amazon-books-2023",
                "checksum_algorithm": "sha256",
            }
        ],
        resources=[
            {
                "name": "ratings",
                "source_name": "amazon-books-2023",
                "type": "interactions",
                "format": "parquet",
                "required": True,
            },
            {
                "name": "item_metadata",
                "source_name": "amazon-books-2023",
                "type": "item_features",
                "format": "jsonl",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Amazon-Books",
        version="2023",
        n_users=892345,
        n_items=515210,
        n_interactions=2987450,
        density=0.000006,
        gini_user=0.743,
        gini_item=0.812,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {
                "name": "load",
                "operation": "load_parquet",
                "params": {"file": "ratings.parquet"},
            },
            {
                "name": "clean",
                "operation": "drop_missing_values",
                "params": {"columns": ["user_id", "item_id", "rating"]},
            },
            {
                "name": "split",
                "operation": "random_split",
                "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
            },
        ]
    ),
)

AMAZON_BOOKS_V2024 = DatasetFixture(
    name="Amazon-Books",
    task=TaskType.RATING_PREDICTION,
    description="Amazon Books benchmark for explicit-feedback recommendation.",
    visibility=Visibility.PUBLIC,
    version="2024",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="Amazon-Books",
        versions=AMAZON_BOOKS_VERSIONS,
        latest_version="2024",
        description="Amazon Books benchmark with yearly snapshots.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Amazon-Books",
        version="2024",
        sources=[
            {
                "name": "amazon-books-2024",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/amazon_books_2024.parquet",
                "filename": "amazon_books_2024.parquet",
                "checksum": "sha256:amazon-books-2024",
                "checksum_algorithm": "sha256",
            },
            {
                "name": "amazon-books-sidecar-2024",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/amazon_books_2024_sidecar.zip",
                "filename": "amazon_books_2024_sidecar.zip",
            },
        ],
        resources=[
            {
                "name": "ratings",
                "source_name": "amazon-books-2024",
                "type": "interactions",
                "format": "parquet",
                "required": True,
            },
            {
                "name": "item_metadata",
                "source_name": "amazon-books-sidecar-2024",
                "type": "item_features",
                "format": "jsonl",
                "required": False,
            },
            {
                "name": "category_tree",
                "source_name": "amazon-books-sidecar-2024",
                "type": "graph",
                "format": "json",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Amazon-Books",
        version="2024",
        n_users=941120,
        n_items=548990,
        n_interactions=3278900,
        density=0.000006,
        gini_user=0.731,
        gini_item=0.798,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {
                "name": "load",
                "operation": "load_parquet",
                "params": {"file": "ratings.parquet"},
            },
            {
                "name": "kcore",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 5, "min_item_interactions": 5},
            },
            {
                "name": "normalize",
                "operation": "normalize_ids",
                "params": {"user_col": "user_id", "item_col": "item_id"},
            },
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.82, "validation_ratio": 0.08},
            },
        ]
    ),
)

LASTFM_2011 = DatasetFixture(
    name="LastFM",
    task=TaskType.RANKING,
    description="Music recommendation benchmark with implicit feedback.",
    visibility=Visibility.PUBLIC,
    version="2011",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="LastFM",
        versions=LASTFM_VERSIONS,
        latest_version="2014",
        description="LastFM benchmark with multiple curated snapshots.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="LastFM",
        version="2011",
        sources=[
            {
                "name": "lastfm-2011-main",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/lastfm_2011.tar.gz",
                "filename": "lastfm_2011.tar.gz",
            }
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "lastfm-2011-main",
                "type": "interactions",
                "format": "tsv",
                "required": True,
            },
            {
                "name": "social_graph",
                "source_name": "lastfm-2011-main",
                "type": "graph",
                "format": "tsv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="LastFM",
        version="2011",
        n_users=1892,
        n_items=17632,
        n_interactions=92834,
        density=0.002781,
        gini_user=0.584,
        gini_item=0.643,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "load", "operation": "parse_tsv", "params": {"delimiter": "\\t"}},
            {
                "name": "filter",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 20},
            },
            {"name": "split", "operation": "leave_one_out", "params": {}},
        ]
    ),
)

LASTFM_2014 = DatasetFixture(
    name="LastFM",
    task=TaskType.RANKING,
    description="Music recommendation benchmark with implicit feedback.",
    visibility=Visibility.PUBLIC,
    version="2014",
    owner="researcher",
    dataset_yaml_raw=_dataset_yaml(
        name="LastFM",
        versions=LASTFM_VERSIONS,
        latest_version="2014",
        description="LastFM benchmark with multiple curated snapshots.",
        citation="DataRecHub examples",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="LastFM",
        version="2014",
        sources=[
            {
                "name": "lastfm-2014-main",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/lastfm_2014.tar.gz",
                "filename": "lastfm_2014.tar.gz",
                "checksum": "sha256:lastfm-2014-main",
                "checksum_algorithm": "sha256",
            },
            {
                "name": "lastfm-2014-tags",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/lastfm_2014_tags.tsv.gz",
                "filename": "lastfm_2014_tags.tsv.gz",
            },
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "lastfm-2014-main",
                "type": "interactions",
                "format": "tsv",
                "required": True,
            },
            {
                "name": "social_graph",
                "source_name": "lastfm-2014-main",
                "type": "graph",
                "format": "tsv",
                "required": False,
            },
            {
                "name": "tags",
                "source_name": "lastfm-2014-tags",
                "type": "item_features",
                "format": "tsv",
                "required": False,
            },
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="LastFM",
        version="2014",
        n_users=2485,
        n_items=20944,
        n_interactions=131806,
        density=0.00253,
        gini_user=0.567,
        gini_item=0.618,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {"name": "load", "operation": "parse_tsv", "params": {"delimiter": "\\t"}},
            {
                "name": "kcore",
                "operation": "filter_min_interactions",
                "params": {"min_user_interactions": 15, "min_item_interactions": 20},
            },
            {
                "name": "feature-join",
                "operation": "join_item_features",
                "params": {"resource": "tags"},
            },
            {
                "name": "split",
                "operation": "temporal_split",
                "params": {"train_ratio": 0.8, "validation_ratio": 0.1},
            },
        ]
    ),
)

EDGE_TINY_RANKING_V1 = DatasetFixture(
    name="Tiny-Edge-Ranking",
    task=TaskType.RANKING,
    description="Dataset ridotto per edge cases validi.",
    visibility=Visibility.PRIVATE,
    version="v1",
    owner="admin",
    dataset_yaml_raw=_dataset_yaml(
        name="Tiny-Edge-Ranking",
        versions=["v1"],
        latest_version="v1",
        description="Edge dataset with small valid registry.",
        citation="Internal demo fixture",
    ),
    version_yaml_raw=_version_yaml(
        dataset_name="Tiny-Edge-Ranking",
        version="v1",
        sources=[
            {
                "name": "tiny-source",
                "source_type": "url",
                "downloadable": True,
                "url": "https://example.org/datasets/tiny_edge_ranking_v1.csv",
                "filename": "tiny_edge_ranking_v1.csv",
            }
        ],
        resources=[
            {
                "name": "interactions",
                "source_name": "tiny-source",
                "type": "interactions",
                "format": "csv",
                "required": True,
            }
        ],
    ),
    characteristics_yaml_raw=_characteristics_yaml(
        dataset_name="Tiny-Edge-Ranking",
        version="v1",
        n_users=120,
        n_items=64,
        n_interactions=850,
        density=0.110677,
        gini_user=0.411,
        gini_item=0.454,
    ),
    pipeline_yaml_raw=_pipeline_yaml(
        [
            {
                "name": "load",
                "operation": "load_csv",
                "params": {"file": "interactions.csv"},
            },
            {"name": "split", "operation": "leave_one_out", "params": {}},
            {"name": "post-check", "operation": "validate_schema", "params": {}},
        ]
    ),
)

DATASET_FIXTURES_MINIMAL = [ALIBABA_V1]
DATASET_FIXTURES_DEMO = [
    ALIBABA_V1,
    ALIBABA_V2,
    EPINIONS_V1_PRIVATE,
    EPINIONS_V2_PRIVATE,
    MOVIELENS_100K_V1,
    MOVIELENS_100K_V2,
    MOVIELENS_100K_V3,
    AMAZON_BOOKS_V2023,
    AMAZON_BOOKS_V2024,
    LASTFM_2011,
    LASTFM_2014,
]
DATASET_FIXTURES_EDGE = [EDGE_TINY_RANKING_V1, MOVIELENS_100K_V3]

MODEL_FIXTURES_MINIMAL = [
    ModelFixture(
        name="LightGCN",
        family="graph-neural-network",
        owner="admin",
        paper_url="https://arxiv.org/abs/2002.02126",
        implementation="https://github.com/gusye1234/LightGCN-PyTorch",
        hyperparams={"n_layers": 3, "embedding_dim": 64, "lr": 0.001},
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
        hyperparams={"embedding_dim": 64, "lr": 0.001, "reg": 0.0001},
    ),
    ModelFixture(
        name="SVD",
        family="matrix-factorization",
        owner="researcher",
        paper_url="https://dl.acm.org/doi/10.1145/1401890.1401944",
        implementation="https://surpriselib.com",
        hyperparams={"n_factors": 100, "n_epochs": 20, "lr_all": 0.005},
    ),
    ModelFixture(
        name="UserKNN",
        family="neighborhood",
        owner="researcher",
        paper_url="https://dl.acm.org/doi/10.1145/371920.372071",
        implementation="https://surpriselib.com",
        hyperparams={"k": 40, "sim_options": {"name": "cosine", "user_based": True}},
    ),
    ModelFixture(
        name="ItemKNN",
        family="neighborhood",
        owner="researcher",
        paper_url="https://dl.acm.org/doi/10.1145/371920.372071",
        implementation="https://surpriselib.com",
        hyperparams={"k": 50, "sim_options": {"name": "pearson", "user_based": False}},
    ),
    ModelFixture(
        name="NeuMF",
        family="neural-cf",
        owner="researcher",
        paper_url="https://arxiv.org/abs/1708.05031",
        implementation="https://github.com/hexiangnan/neural_collaborative_filtering",
        hyperparams={"embedding_dim": 64, "mlp_layers": [128, 64, 32], "lr": 0.0005},
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
        hyperparams={"seed": 123, "sampling": "uniform"},
    ),
]

PIPELINE_FIXTURES_MINIMAL: list[PipelineFixture] = []

PIPELINE_FIXTURES_DEMO = [
    PipelineFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v2",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "load",
                    "operation": "load_csv",
                    "params": {"file": "events.csv"},
                },
                {
                    "name": "sessionize",
                    "operation": "build_sessions",
                    "params": {"max_gap_minutes": 30},
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
        dataset_name="MovieLens-100K",
        dataset_version="v2",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "load",
                    "operation": "load_csv",
                    "params": {"file": "ratings.csv"},
                },
                {
                    "name": "filter",
                    "operation": "filter_min_interactions",
                    "params": {"min_user_interactions": 10},
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
        dataset_name="Amazon-Books",
        dataset_version="2024",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "load",
                    "operation": "load_parquet",
                    "params": {"file": "ratings.parquet"},
                },
                {
                    "name": "deduplicate",
                    "operation": "drop_duplicates",
                    "params": {"subset": ["user_id", "item_id", "timestamp"]},
                },
                {
                    "name": "split",
                    "operation": "temporal_split",
                    "params": {"train_ratio": 0.84, "validation_ratio": 0.06},
                },
            ]
        ),
    ),
    PipelineFixture(
        dataset_name="LastFM",
        dataset_version="2014",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "load",
                    "operation": "parse_tsv",
                    "params": {"delimiter": "\\t"},
                },
                {
                    "name": "graph-features",
                    "operation": "join_graph_features",
                    "params": {"resource": "social_graph"},
                },
                {"name": "split", "operation": "leave_one_out", "params": {}},
            ]
        ),
    ),
]

PIPELINE_FIXTURES_EDGE = [
    PipelineFixture(
        dataset_name="Tiny-Edge-Ranking",
        dataset_version="v1",
        code="P002",
        pipeline_yaml_raw=_pipeline_yaml(
            [
                {
                    "name": "load",
                    "operation": "load_csv",
                    "params": {"file": "small.csv"},
                },
                {
                    "name": "split",
                    "operation": "random_split",
                    "params": {"train_ratio": 0.7},
                },
            ]
        ),
    )
]

EXPERIMENT_FIXTURES_MINIMAL = [
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-minimal-lightgcn-alibaba-v1-finished",
        seed=42,
        status=Status.FINISHED,
        submitted_by="admin",
        metrics=_ranking_metrics("good"),
    ),
]

EXPERIMENT_FIXTURES_DEMO = [
    *EXPERIMENT_FIXTURES_MINIMAL,
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v1",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-alibaba-v1-finished",
        seed=9,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v1",
        model_name="PopRank",
        run_name="seed-demo-poprank-alibaba-v1-queued",
        seed=21,
        status=Status.QUEUED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v2",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-alibaba-v2-finished",
        seed=22,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v2",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-alibaba-v2-finished",
        seed=23,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="Alibaba-iFashion",
        dataset_version="v2",
        model_name="NeuMF",
        run_name="seed-demo-neumf-alibaba-v2-running",
        seed=24,
        status=Status.RUNNING,
        pipeline_code="P002",
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v1",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-epinions-v1-finished",
        seed=31,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-epinions-v1-running",
        seed=32,
        status=Status.RUNNING,
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v1",
        model_name="PopRank",
        run_name="seed-demo-poprank-epinions-v1-failed",
        seed=33,
        status=Status.FAILED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v2",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-epinions-v2-finished",
        seed=34,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v2",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-epinions-v2-finished",
        seed=35,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="Epinions",
        dataset_version="v2",
        model_name="PopRank",
        run_name="seed-demo-poprank-epinions-v2-queued",
        seed=36,
        status=Status.QUEUED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v1",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml100k-v1-finished",
        seed=101,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v1",
        model_name="SVD",
        run_name="seed-demo-svd-ml100k-v1-finished",
        seed=102,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v1",
        model_name="ItemKNN",
        run_name="seed-demo-itemknn-ml100k-v1-failed",
        seed=103,
        status=Status.FAILED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v2",
        model_name="SVD",
        run_name="seed-demo-svd-ml100k-v2-finished",
        seed=104,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        metrics=_rating_metrics("best"),
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v2",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml100k-v2-finished",
        seed=105,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v2",
        model_name="ItemKNN",
        run_name="seed-demo-itemknn-ml100k-v2-running",
        seed=106,
        status=Status.RUNNING,
        pipeline_code="P002",
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v3",
        model_name="ItemKNN",
        run_name="seed-demo-itemknn-ml100k-v3-finished",
        seed=107,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v3",
        model_name="SVD",
        run_name="seed-demo-svd-ml100k-v3-running",
        seed=108,
        status=Status.RUNNING,
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v3",
        model_name="UserKNN",
        run_name="seed-demo-userknn-ml100k-v3-failed",
        seed=109,
        status=Status.FAILED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2023",
        model_name="SVD",
        run_name="seed-demo-svd-amazon-books-2023-finished",
        seed=201,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2023",
        model_name="UserKNN",
        run_name="seed-demo-userknn-amazon-books-2023-finished",
        seed=202,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2023",
        model_name="ItemKNN",
        run_name="seed-demo-itemknn-amazon-books-2023-queued",
        seed=203,
        status=Status.QUEUED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2024",
        model_name="SVD",
        run_name="seed-demo-svd-amazon-books-2024-finished",
        seed=204,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        metrics=_rating_metrics("best"),
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2024",
        model_name="ItemKNN",
        run_name="seed-demo-itemknn-amazon-books-2024-finished",
        seed=205,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_rating_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="Amazon-Books",
        dataset_version="2024",
        model_name="UserKNN",
        run_name="seed-demo-userknn-amazon-books-2024-running",
        seed=206,
        status=Status.RUNNING,
        pipeline_code="P002",
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2011",
        model_name="BPR-MF",
        run_name="seed-demo-bpr-lastfm-2011-finished",
        seed=301,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("baseline"),
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2011",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-lastfm-2011-finished",
        seed=302,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2011",
        model_name="PopRank",
        run_name="seed-demo-poprank-lastfm-2011-failed",
        seed=303,
        status=Status.FAILED,
        submitted_by="viewer",
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2014",
        model_name="LightGCN",
        run_name="seed-demo-lightgcn-lastfm-2014-finished",
        seed=304,
        status=Status.FINISHED,
        pipeline_code="P002",
        submitted_by="researcher",
        metrics=_ranking_metrics("best"),
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2014",
        model_name="NeuMF",
        run_name="seed-demo-neumf-lastfm-2014-finished",
        seed=305,
        status=Status.FINISHED,
        submitted_by="researcher",
        metrics=_ranking_metrics("good"),
    ),
    ExperimentFixture(
        dataset_name="LastFM",
        dataset_version="2014",
        model_name="PopRank",
        run_name="seed-demo-poprank-lastfm-2014-running",
        seed=306,
        status=Status.RUNNING,
        pipeline_code="P002",
        submitted_by="viewer",
    ),
]

EXPERIMENT_FIXTURES_EDGE = [
    ExperimentFixture(
        dataset_name="Tiny-Edge-Ranking",
        dataset_version="v1",
        model_name="RandomBaseline",
        run_name="seed-edge-random-tiny-v1-finished",
        seed=131,
        status=Status.FINISHED,
        submitted_by="admin",
        metrics=[
            MetricCsvRow(Split.TEST, "ndcg@10", 0.033, Direction.MAX, k=10),
            MetricCsvRow(Split.TEST, "recall@10", 0.055, Direction.MAX, k=10),
        ],
    ),
    ExperimentFixture(
        dataset_name="Tiny-Edge-Ranking",
        dataset_version="v1",
        model_name="LightGCN",
        run_name="seed-edge-lightgcn-tiny-v1-failed",
        seed=132,
        status=Status.FAILED,
        submitted_by="researcher",
    ),
    ExperimentFixture(
        dataset_name="MovieLens-100K",
        dataset_version="v3",
        model_name="RandomBaseline",
        run_name="seed-edge-random-ml100k-v3-queued",
        seed=133,
        status=Status.QUEUED,
        submitted_by="viewer",
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
            f"DatasetVersion appena creata non trovata: {fixture.name} {fixture.version}"
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
        if changed:
            await existing.save()
        return existing, False

    public = await create_experiment(
        ExperimentCreate(
            pipeline_uuid=pipeline.uuid,
            model_uuid=model.uuid,
            run_name=fixture.run_name,
            seed=fixture.seed,
            training_config=model.hyperparams,
            notes="Seeded via scripts/seed.py",
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

    for (dataset_name, version_name), version in dataset_versions.items():
        if version.status != VersionStatus.READY:
            continue
        if await Dataset.get(version.dataset_id) is None:
            issues.append(
                "dataset mancante per DatasetVersion "
                f"{dataset_name}:{version_name}"
            )

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

    for (dataset_name, version_name, pipeline_code), pipeline in pipelines.items():
        if await DatasetVersion.get(pipeline.dataset_version_id) is None:
            issues.append(
                "pipeline senza dataset_version valida: "
                f"{dataset_name}:{version_name}:{pipeline_code}"
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
        datasets[fixture.name] = dataset
        created_datasets += 1 if was_created else 0
        print(
            f"  - {fixture.name} ({fixture.version}) "
            f"[{fixture.visibility.value}] owner={fixture.owner} "
            f"({'created' if was_created else 'existing'})"
        )

        dataset_version, version_created = await _upsert_dataset_version(dataset, fixture)
        dataset_versions[(fixture.name, fixture.version)] = dataset_version
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
            pipelines[(fixture.name, fixture.version, existing_pipeline.code)] = (
                existing_pipeline
            )

        has_pipeline_for_version = any(
            key[0] == fixture.name and key[1] == fixture.version for key in pipelines
        )
        if not has_pipeline_for_version and fixture.pipeline_yaml_raw.strip():
            base_pipeline_fixture = PipelineFixture(
                dataset_name=fixture.name,
                dataset_version=fixture.version,
                code="P001",
                pipeline_yaml_raw=fixture.pipeline_yaml_raw,
                status=PipelineStatus.READY,
            )
            base_pipeline, base_pipeline_created = await _upsert_pipeline(
                base_pipeline_fixture,
                dataset_version,
            )
            pipelines[(fixture.name, fixture.version, base_pipeline.code)] = base_pipeline
            created_pipelines += 1 if base_pipeline_created else 0

    print("pipelines:")
    for fixture in scenario.pipelines:
        dataset_version = dataset_versions.get(
            (fixture.dataset_name, fixture.dataset_version)
        )
        if dataset_version is None:
            print(
                f"  - {fixture.code} ({fixture.dataset_name}:{fixture.dataset_version}) "
                "(skipped: missing dataset version)"
            )
            continue

        pipeline, was_created = await _upsert_pipeline(fixture, dataset_version)
        pipelines[(fixture.dataset_name, fixture.dataset_version, fixture.code)] = (
            pipeline
        )
        created_pipelines += 1 if was_created else 0
        print(
            f"  - {fixture.code} ({fixture.dataset_name}:{fixture.dataset_version}) "
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
            (fixture.dataset_name, fixture.dataset_version)
        )
        pipeline = pipelines.get(
            (fixture.dataset_name, fixture.dataset_version, fixture.pipeline_code)
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
            f"pipeline={fixture.pipeline_code} "
            f"submitter={fixture.submitted_by} "
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
