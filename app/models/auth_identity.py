from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntIdMixin, CreatedAtMixin
from app.models.enums import AuthProvider, database_enum

if TYPE_CHECKING:
    from app.models.user import User


class AuthIdentity(BigIntIdMixin, CreatedAtMixin, Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_auth_identities_provider_subject"),
        Index("ix_auth_identities_user_id", "user_id"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[AuthProvider] = mapped_column(
        database_enum(AuthProvider, name="auth_provider"),
        nullable=False,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str] = mapped_column(String(320), nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_identities")
