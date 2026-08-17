from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, TimestampMixin
from app.models.enums import (
    TaskPriority,
    TaskStatus,
    TaskVisibility,
    database_enum,
)

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.department import Department
    from app.models.task_assignment import TaskAssignment
    from app.models.task_comment import TaskComment
    from app.models.task_help_request import TaskHelpRequest
    from app.models.task_view_preference import TaskViewPreference
    from app.models.user import User


class Task(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "visibility != 'department' OR department_id IS NOT NULL",
            name="ck_tasks_department_visibility",
        ),
        Index("ix_tasks_created_by_id", "created_by_id"),
        Index("ix_tasks_department_id", "department_id"),
        Index("ix_tasks_status_due_at", "status", "due_at"),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        database_enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.TODO,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        database_enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
    )
    visibility: Mapped[TaskVisibility] = mapped_column(
        database_enum(TaskVisibility, name="task_visibility"),
        nullable=False,
        default=TaskVisibility.PRIVATE,
    )
    created_by_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="RESTRICT"),
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    creator: Mapped[User] = relationship(
        back_populates="created_tasks",
        foreign_keys=[created_by_id],
    )
    department: Mapped[Department | None] = relationship(back_populates="tasks")
    assignments: Mapped[list[TaskAssignment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list[TaskComment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    activity: Mapped[list[ActivityLog]] = relationship(back_populates="task")
    help_requests: Mapped[list[TaskHelpRequest]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    view_preferences: Mapped[list[TaskViewPreference]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
