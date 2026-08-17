from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import (
    HelpRequestStatus,
    TaskPriority,
    TaskStatus,
    TaskVisibility,
)


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and value.utcoffset() is None:
        raise ValueError("Datetime must include a timezone offset")
    return value


class TaskListView(StrEnum):
    FOCUS = "focus"
    ALL = "all"
    HIDDEN = "hidden"
    PINNED = "pinned"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    priority: TaskPriority = TaskPriority.MEDIUM
    visibility: TaskVisibility = TaskVisibility.PRIVATE
    department_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None
    assignee_ids: set[int] = Field(default_factory=set, max_length=100)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Task title cannot be blank")
        return normalized

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    priority: TaskPriority | None = None
    visibility: TaskVisibility | None = None
    department_id: int | None = Field(default=None, ge=1)
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Task title cannot be blank")
        return normalized

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        return _require_timezone(value)

    @model_validator(mode="after")
    def prevent_null_required_fields(self) -> "TaskUpdate":
        for field in ("title", "priority", "visibility"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssignmentCreate(BaseModel):
    user_id: int = Field(ge=1)


class HelpRequestCreate(BaseModel):
    message: str | None = Field(default=None, max_length=2_000)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class TaskPreferenceUpdate(BaseModel):
    viewer_id: int | None = Field(default=None, ge=1)
    is_hidden: bool = False
    is_pinned: bool = False

    @model_validator(mode="after")
    def prevent_conflicting_preferences(self) -> "TaskPreferenceUpdate":
        if self.is_hidden and self.is_pinned:
            raise ValueError("A task cannot be hidden and pinned at the same time")
        return self


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    avatar_url: str | None


class DepartmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TaskAssignmentRead(BaseModel):
    user: UserSummary
    assigned_by_id: int
    created_at: datetime


class HelpRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by_id: int
    message: str | None
    status: HelpRequestStatus
    accepted_by_id: int | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskPreferenceRead(BaseModel):
    viewer_id: int
    task_id: int
    is_hidden: bool
    is_pinned: bool
    updated_by_id: int
    updated_at: datetime | None = None


class TaskRead(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    visibility: TaskVisibility
    created_by_id: int
    creator: UserSummary
    department_id: int | None
    department: DepartmentSummary | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    assignments: list[TaskAssignmentRead]
    help_request: HelpRequestRead | None
    preference: TaskPreferenceRead | None


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
