from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class PipelineStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    PROCESSING = "processing"
    FAILED = "failed"


class Pipeline(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    dataset_version_id: Annotated[PydanticObjectId, Indexed()]
    code: str  # Non-semantic identifier, e.g. "P001"
    yaml_raw: str | None = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    status: PipelineStatus = PipelineStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "pipelines"
        indexes = [
            IndexModel([("dataset_version_id", 1), ("code", 1)], unique=True),
            [("dataset_version_id", 1), ("created_at", -1)],
        ]
