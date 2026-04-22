from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.datasets import TaskType, Visibility


class DatasetBase(BaseModel):
    name: str
    task: TaskType
    description: str | None = None
    visibility: Visibility = Visibility.PUBLIC
    team_uuid: UUID | None = None


class DatasetCreate(DatasetBase):
    pass


class DatasetPublic(DatasetBase):
    uuid: UUID
    created_by_user_uuid: UUID | None = None
    created_at: datetime
    versions_count: int = 0
    latest_version: str | None = None


class DatasetSummary(BaseModel):
    uuid: UUID
    name: str
    task: TaskType
    visibility: Visibility
    versions_count: int = 0
    latest_version: str | None = None
