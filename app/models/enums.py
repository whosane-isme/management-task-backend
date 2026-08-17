from enum import StrEnum

from sqlalchemy import Enum as SqlEnum


class AuthProvider(StrEnum):
    GOOGLE = "google"
    GITHUB = "github"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskVisibility(StrEnum):
    PUBLIC = "public"
    DEPARTMENT = "department"
    PRIVATE = "private"


class HelpRequestStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


def database_enum(enum_class: type[StrEnum], *, name: str) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
