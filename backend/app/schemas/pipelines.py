from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.pipelines import PipelineStatus


class PipelineBlockPublic(BaseModel):
    name: str
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)


class PipelineBase(BaseModel):
    code: str | None = None
    yaml_raw: str | None = None
    status: PipelineStatus = PipelineStatus.DRAFT


class PipelineCreate(PipelineBase):
    pass


class PipelinePublic(BaseModel):
    uuid: UUID
    dataset_version_uuid: UUID
    code: str
    status: PipelineStatus
    blocks: list[PipelineBlockPublic] = Field(default_factory=list)
    created_at: datetime


class PipelineSummary(BaseModel):
    uuid: UUID
    dataset_version_uuid: UUID
    code: str
    status: PipelineStatus
    steps_count: int
    created_at: datetime


class PipelineYamlPublic(BaseModel):
    pipeline_uuid: UUID
    content: str


class PipelinePreviewPublic(BaseModel):
    dataset_version_uuid: UUID
    requested_code: str | None = None
    recognized_dataset_name: str | None = None
    recognized_version: str | None = None
    pipeline_steps_count: int
