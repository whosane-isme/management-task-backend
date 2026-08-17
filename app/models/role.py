from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, Integer, String, Text, false, text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.role_permission import RolePermission
    from app.models.user_role_assignment import UserRoleAssignment


class Role(BigIntIdMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (Index("uq_roles_name_ci", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    permission_links: Mapped[list[RolePermission]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list[UserRoleAssignment]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    @property
    def permissions(self) -> list[Permission]:
        return [link.permission for link in self.permission_links]
