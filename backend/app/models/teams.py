from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import Field


class Team(Document):
    uuid: Annotated[UUID, Field(default_factory=uuid4), Indexed(unique=True)]
    name: Annotated[str, Indexed(unique=True)]
    description: str | None = None

    owner_user_uuid: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "teams"
