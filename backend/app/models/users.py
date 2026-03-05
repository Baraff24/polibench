from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class User(Document):
    uuid: Annotated[UUID, Indexed(unique=True)] = Field(default_factory=uuid4)
    email: Annotated[EmailStr, Indexed(unique=True)]
    first_name: str | None = None
    last_name: str | None = None
    hashed_password: str | None = None
    provider: str | None = None
    picture: str | None = None
    role: UserRole = UserRole.RESEARCHER
    team_uuid: Annotated[UUID | None, Indexed()] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None

    class Settings:
        name = "users"
