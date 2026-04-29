from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.dataset_versions import VersionStatus


class DatasetVersionBase(BaseModel):
    version: str
    release_notes: str | None = None
    status: VersionStatus = VersionStatus.DRAFT
    dataset_yaml_raw: str | None = None
    version_yaml_raw: str | None = None
    # Deprecated: pipeline source of truth moved to Pipeline model.
    pipeline_yaml_raw: str | None = None
    characteristics_yaml_raw: str | None = None


class DatasetVersionCreate(DatasetVersionBase):
    pass


class DatasetVersionPublic(BaseModel):
    uuid: UUID
    dataset_uuid: UUID
    version: str
    release_notes: str | None = None
    status: VersionStatus
    n_users: int | None = None
    n_items: int | None = None
    n_interactions: int | None = None
    density: float | None = None
    gini_user: float | None = None
    gini_item: float | None = None
    created_at: datetime


class DatasetVersionSummary(BaseModel):
    uuid: UUID
    dataset_uuid: UUID
    version: str
    status: VersionStatus
    n_users: int | None = None
    n_items: int | None = None
    n_interactions: int | None = None
    density: float | None = None
    created_at: datetime


class SourcePublic(BaseModel):
    uuid: UUID
    dataset_version_uuid: UUID
    name: str
    source_type: str
    archive: str | None = None
    downloadable: bool
    url: str | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None
    filename: str | None = None
    inner_paths: dict[str, Any] | None = None
    created_at: datetime


class ResourcePublic(BaseModel):
    uuid: UUID
    dataset_version_uuid: UUID
    source_uuid: UUID | None = None
    name: str
    filename: str | None = None
    type: str
    format: str | None = None
    required: bool
    about: str | None = None
    schema_definition: dict[str, Any] | None = None
    created_at: datetime


class DatasetVersionYamlPublic(BaseModel):
    dataset_version_uuid: UUID
    kind: str
    content: str


class DatasetVersionCharacteristicsPreview(BaseModel):
    n_users: int | None = None
    n_items: int | None = None
    n_interactions: int | None = None
    density: float | None = None
    gini_user: float | None = None
    gini_item: float | None = None


class DatasetVersionPreviewPublic(BaseModel):
    dataset_uuid: UUID
    requested_version: str
    recognized_dataset_name: str | None = None
    recognized_version: str | None = None
    source_count: int
    resource_count: int
    pipeline_steps_count: int
    characteristics: DatasetVersionCharacteristicsPreview


class SourceWithResourcesPublic(SourcePublic):
    resources: list[ResourcePublic]
