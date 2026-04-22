from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class Resource(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    dataset_version_id: Annotated[PydanticObjectId, Indexed()]
    source_id: Annotated[PydanticObjectId | None, Indexed()] = None
    name: str
    filename: str | None = None
    type: str
    format: str | None = None
    required: bool = True
    about: str | None = None
    schema_definition: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "resources"
