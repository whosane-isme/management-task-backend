from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class ActivityLog(BigIntIdMixin, CreatedAtMixin, Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_logs_task_created", "task_id", "created_at"),)

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    task: Mapped[Task] = relationship(back_populates="activity")
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])
