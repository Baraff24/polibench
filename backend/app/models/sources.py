from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class Source(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    dataset_version_id: Annotated[PydanticObjectId, Indexed()]
    name: str
    source_type: str
    archive: str | None = None
    downloadable: bool = False
    url: str | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None
    filename: str | None = None
    inner_paths: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "sources"
