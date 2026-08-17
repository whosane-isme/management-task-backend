from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    department_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("User name cannot be blank")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    avatar_url: str | None
    department_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPage(BaseModel):
    items: list[UserRead]
    total: int
    limit: int
    offset: int


class RoleAssignmentCreate(BaseModel):
    role_id: int = Field(ge=1)
    department_id: int | None = Field(default=None, ge=1)


class RoleAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role_id: int
    department_id: int | None
    assigned_by_id: int | None
    created_at: datetime
