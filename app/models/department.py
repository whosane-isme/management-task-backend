from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Department(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (Index("uq_departments_name_ci", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    users: Mapped[list[User]] = relationship(back_populates="department")
    tasks: Mapped[list[Task]] = relationship(back_populates="department")
