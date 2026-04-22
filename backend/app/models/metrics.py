from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class Split(str, Enum):
    VALIDATION = "validation"
    TEST = "test"


class Direction(str, Enum):
    MAX = "max"  # higher is better
    MIN = "min"  # lower is better


class ExperimentMetric(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)

    # Link to the run
    experiment_id: Annotated[PydanticObjectId, Indexed()]

    # Denormalized for fast leaderboard queries
    dataset_id: Annotated[PydanticObjectId, Indexed()]
    dataset_version_id: Annotated[PydanticObjectId, Indexed()]
    model_id: Annotated[PydanticObjectId, Indexed()]
    submitted_by_user_id: Annotated[PydanticObjectId | None, Indexed()] = None
    team_id: Annotated[PydanticObjectId | None, Indexed()] = None

    # What metric this is
    split: Split = Split.VALIDATION
    metric: Annotated[str, Indexed()]  # e.g. "ndcg@10", "recall@20", "rmse"
    k: int | None = None  # optional: 10, 20... (useful for @k metrics)

    # The result
    value: float
    direction: Direction = Direction.MAX

    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "metrics"


# Transitional alias to keep compatibility with existing imports.
Metric = ExperimentMetric
