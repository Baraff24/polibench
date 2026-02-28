from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class MLModel(Document):
    uuid: Annotated[UUID, Field(default_factory=uuid4), Indexed(unique=True)]
    name: Annotated[str, Indexed(unique=True)]
    family: str | None = None
    paper_url: str | None = None
    implementation: str | None = None
    created_by_user_id: Annotated[PydanticObjectId | None, Indexed()] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "models"
