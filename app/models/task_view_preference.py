from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class TaskViewPreference(TimestampMixin, Base):
    __tablename__ = "task_view_preferences"

    viewer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    task_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    updated_by_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    viewer: Mapped[User] = relationship(foreign_keys=[viewer_id])
    task: Mapped[Task] = relationship(back_populates="view_preferences")
    updated_by: Mapped[User] = relationship(foreign_keys=[updated_by_id])
