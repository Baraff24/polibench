from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.metric_import_jobs import ImportStatus


class MetricImportPublic(BaseModel):
    uuid: UUID
    experiment_uuid: UUID
    uploaded_by_user_uuid: UUID | None = None
    status: ImportStatus
    csv_filename: str
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
