from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    RANKING = "ranking"
    RATING_PREDICTION = "rating_prediction"
    CTR = "ctr"


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Splits(BaseModel):
    train: int | None = None
    test: int | None = None
    validation: int | None = None


class Dataset(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    name: str
    version: str
    task: TaskType
    description: str | None = None
    visibility: Visibility = Visibility.PUBLIC
    splits: Splits | None = None
    team_id: Annotated[PydanticObjectId | None, Indexed()] = None
    created_by_user_id: Annotated[PydanticObjectId | None, Indexed()] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "datasets"
        # indexes = [
        #   [("name", 1), ("version", 1)],  # unique ideally
        # ]
