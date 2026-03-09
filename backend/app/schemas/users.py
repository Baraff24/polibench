from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """
    Shared User properties. Visible by anyone.
    """

    first_name: str | None = None
    last_name: str | None = None
    picture: str | None = None


class PrivateUserBase(UserBase):
    """
    Shared User properties. Visible only by admins and self.
    """

    email: EmailStr | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    is_superuser: bool | None = None
    provider: str | None = None


class UserUpdate(UserBase):
    """
    User properties to receive via API on update.
    """

    password: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class User(PrivateUserBase):
    """
    User properties returned by API.
    uuid è l'unico identificatore esposto: niente _id MongoDB.
    """

    uuid: UUID
