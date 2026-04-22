from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class TaskType(str, Enum):
    RANKING = "ranking"
    RATING_PREDICTION = "rating_prediction"
    CTR = "ctr"


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Dataset(Document):
    """
    Entità catalografica del dataset.
    Le informazioni version-specific (version, pipeline, sources/resources,
    characteristics) vivono in DatasetVersion.
    """

    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    name: Annotated[str, Indexed()]
    task: TaskType
    description: str | None = None
    visibility: Visibility = Visibility.PUBLIC
    team_id: Annotated[PydanticObjectId | None, Indexed()] = None
    created_by_user_id: Annotated[PydanticObjectId | None, Indexed()] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "datasets"
