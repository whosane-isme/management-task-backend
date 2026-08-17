from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, TimestampMixin
from app.models.enums import HelpRequestStatus, database_enum

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class TaskHelpRequest(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "task_help_requests"
    __table_args__ = (
        CheckConstraint(
            "status != 'accepted' OR accepted_by_id IS NOT NULL",
            name="ck_task_help_requests_accepted_by",
        ),
        Index(
            "uq_task_help_requests_active",
            "task_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'accepted')"),
        ),
        Index("ix_task_help_requests_requested_by_id", "requested_by_id"),
        Index("ix_task_help_requests_accepted_by_id", "accepted_by_id"),
    )

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[HelpRequestStatus] = mapped_column(
        database_enum(HelpRequestStatus, name="help_request_status"),
        nullable=False,
        default=HelpRequestStatus.OPEN,
    )
    accepted_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped[Task] = relationship(back_populates="help_requests")
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    accepted_by: Mapped[User | None] = relationship(foreign_keys=[accepted_by_id])
