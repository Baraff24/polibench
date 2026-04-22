from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.experiments import Artifacts, CodeInfo, Status


class ExperimentBase(BaseModel):
    # Main path in the new domain
    dataset_version_uuid: UUID | None = None
    # Transitional compatibility path
    dataset_uuid: UUID | None = None

    model_uuid: UUID
    team_uuid: UUID | None = None
    run_name: str | None = None
    seed: int | None = None
    notes: str | None = None
    training_config: dict[str, Any] | None = None
    code: CodeInfo | None = None


class ExperimentCreate(ExperimentBase):
    pass


class ExperimentPublic(BaseModel):
    uuid: UUID
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    model_uuid: UUID
    team_uuid: UUID | None = None
    submitted_by_user_uuid: UUID | None = None
    run_name: str | None = None
    status: Status
    artifacts: Artifacts | None = None
    training_config: dict[str, Any] | None = None
    seed: int | None = None
    notes: str | None = None
    code: CodeInfo | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ExperimentSummary(BaseModel):
    uuid: UUID
    dataset_uuid: UUID
    dataset_version_uuid: UUID
    model_uuid: UUID
    run_name: str | None = None
    status: Status
    created_at: datetime
