from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class VersionStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    FAILED = "failed"


class DatasetVersion(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    dataset_id: Annotated[PydanticObjectId, Indexed()]
    version: str
    release_notes: str | None = None

    # Raw source of truth (downloadable as YAML)
    dataset_yaml_raw: str | None = None
    version_yaml_raw: str | None = None
    pipeline_yaml_raw: str | None = None
    characteristics_yaml_raw: str | None = None

    # Parsed/denormalized fields for fast reads
    pipeline_blocks: list[dict[str, Any]] | None = None
    n_users: int | None = None
    n_items: int | None = None
    n_interactions: int | None = None
    density: float | None = None
    gini_user: float | None = None
    gini_item: float | None = None

    status: VersionStatus = VersionStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "dataset_versions"
        indexes = [
            IndexModel([("dataset_id", 1), ("version", 1)], unique=True),
            [("dataset_id", 1), ("created_at", -1)],
        ]
