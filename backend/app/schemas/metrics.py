from datetime import datetime
from typing import Any
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
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    training_config: dict[str, Any] | None = None
    status: str | None = None
    run_name: str | None = None
    seed: int | None = None
    created_at: datetime | None = None
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
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    training_config: dict[str, Any] | None = None
    status: str | None = None
    run_name: str | None = None
    seed: int | None = None
    created_at: datetime | None = None
    split: Split
    metrics: dict[str, float]
    directions: dict[str, Direction]
    repo_url: str | None = None
    rank: int | None = None


class LeaderboardQuery(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID | None = None
    pipeline_uuid: UUID | None = None
    split: Split
    metrics: list[str] = Field(default_factory=list)
    sort_by: str | None = None
    top_n: int = 20
    model_uuids: list[UUID] | None = None
    author_uuids: list[UUID] | None = None
    hyperparam_filters: dict[str, Any] | None = None


class BestConfigurationQuery(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID
    split: Split
    target_metric: str
    direction: Direction
    group_by_hyperparams: list[str] = Field(default_factory=list)
    model_uuids: list[UUID] | None = None
    author_uuids: list[UUID] | None = None
    hyperparam_filters: dict[str, Any] | None = None


class BestConfigurationGroup(BaseModel):
    model_uuid: UUID
    model_name: str | None = None
    submitted_by_user_uuid: UUID | None = None
    submitted_by_display_name: str | None = None
    submitted_by_email: str | None = None
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    best_value: float
    mean_value: float
    count: int
    std: float | None = None
    best_experiment_uuid: UUID | None = None
    best_run_name: str | None = None
    best_training_config: dict[str, Any] | None = None


class BestConfigurationResponse(BaseModel):
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    pipeline_uuid: UUID
    split: Split
    target_metric: str
    direction: Direction
    group_by_hyperparams: list[str] = Field(default_factory=list)
    best_group: BestConfigurationGroup | None = None
    groups: list[BestConfigurationGroup] = Field(default_factory=list)
