from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class ImportStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MetricImportJob(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    experiment_id: Annotated[PydanticObjectId, Indexed()]
    uploaded_by_user_id: Annotated[PydanticObjectId, Indexed()]
    status: ImportStatus = ImportStatus.UPLOADED
    csv_filename: str
    csv_storage_path: str
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Settings:
        name = "metric_import_jobs"
