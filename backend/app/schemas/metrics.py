from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.metrics import Direction, Split


class MetricCreate(BaseModel):
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction


class MetricsBatchCreate(BaseModel):
    experiment_uuid: UUID
    metrics: list[MetricCreate]


class MetricPublic(BaseModel):
    uuid: UUID
    experiment_uuid: UUID
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    model_uuid: UUID
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    computed_at: datetime


class LeaderboardEntry(BaseModel):
    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    pipeline_code: str | None = None
    split: Split
    metric: str
    k: int | None = None
    value: float
    direction: Direction
    rank: int | None = None


class ExperimentMetrics(BaseModel):
    experiment_uuid: UUID
    metrics_by_split: dict[Split, list[MetricPublic]] = Field(default_factory=dict)


class MultiMetricLeaderboardEntry(BaseModel):
    experiment_uuid: UUID
    model_uuid: UUID
    model_name: str | None = None
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID | None = None
    pipeline_code: str | None = None
    split: Split
    metrics: dict[str, float]
    directions: dict[str, Direction]
    repo_url: str | None = None
    rank: int | None = None
