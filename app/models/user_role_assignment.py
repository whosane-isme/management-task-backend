from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.role import Role
    from app.models.user import User


class UserRoleAssignment(BigIntIdMixin, CreatedAtMixin, Base):
    __tablename__ = "user_role_assignments"
    __table_args__ = (
        Index(
            "uq_user_role_assignments_global",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("department_id IS NULL"),
        ),
        Index(
            "uq_user_role_assignments_department",
            "user_id",
            "role_id",
            "department_id",
            unique=True,
            postgresql_where=text("department_id IS NOT NULL"),
        ),
        Index("ix_user_role_assignments_department_id", "department_id"),
        Index("ix_user_role_assignments_assigned_by_id", "assigned_by_id"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="RESTRICT"),
    )
    assigned_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    user: Mapped[User] = relationship(
        back_populates="role_assignments",
        foreign_keys=[user_id],
    )
    role: Mapped[Role] = relationship(back_populates="assignments")
    department: Mapped[Department | None] = relationship(foreign_keys=[department_id])
    assigned_by: Mapped[User | None] = relationship(foreign_keys=[assigned_by_id])
