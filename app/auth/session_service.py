import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.models.user import User
from app.models.user_session import UserSession


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    record: UserSession
    token: str
    csrf_token: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    record: UserSession
    user: User
    needs_touch: bool


async def create_user_session(
    session: AsyncSession,
    *,
    user_id: int,
    lifetime: timedelta,
    now: datetime | None = None,
) -> IssuedSession:
    issued_at = now or datetime.now(UTC)
    raw_token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    record = UserSession(
        user_id=user_id,
        token_hash=hash_secret(raw_token),
        csrf_token_hash=hash_secret(csrf_token),
        expires_at=issued_at + lifetime,
        last_seen_at=issued_at,
    )
    session.add(record)
    await session.flush()
    return IssuedSession(record=record, token=raw_token, csrf_token=csrf_token)


async def authenticate_user_session(
    session: AsyncSession,
    *,
    raw_token: str,
    idle_timeout: timedelta,
    now: datetime | None = None,
) -> AuthenticatedSession:
    checked_at = now or datetime.now(UTC)
    idle_cutoff = checked_at - idle_timeout
    statement = (
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == hash_secret(raw_token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > checked_at,
            UserSession.last_seen_at > idle_cutoff,
            User.is_active.is_(True),
        )
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise AuthenticationError("Invalid or expired session")

    record, user = row
    needs_touch = record.last_seen_at < checked_at - timedelta(minutes=5)
    if needs_touch:
        record.last_seen_at = checked_at
    return AuthenticatedSession(record=record, user=user, needs_touch=needs_touch)


async def revoke_user_session(
    session: AsyncSession,
    record: UserSession,
    *,
    now: datetime | None = None,
) -> None:
    record.revoked_at = now or datetime.now(UTC)
    await session.flush()
