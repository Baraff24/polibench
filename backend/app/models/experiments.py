from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class Status(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class CodeInfo(BaseModel):
    git_commit: str | None = None
    repo_url: str | None = None
    docker_image: str | None = None


class Artifacts(BaseModel):
    logs_url: str | None = None
    model_path: str | None = None
    predictions_path: str | None = None


class Experiment(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    dataset_id: Annotated[PydanticObjectId, Indexed()]
    model_id: Annotated[PydanticObjectId, Indexed()]
    submitted_by_user_id: Annotated[PydanticObjectId, Indexed()]
    team_id: Annotated[PydanticObjectId | None, Indexed()] = None
    run_name: str | None = None
    status: Status = Status.QUEUED
    training_config: dict[str, Any] | None = None
    seed: int | None = None
    notes: str | None = None
    code: CodeInfo | None = None
    artifacts: Artifacts | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    class Settings:
        name = "experiments"
