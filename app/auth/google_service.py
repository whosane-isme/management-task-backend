from collections.abc import Collection, Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import GoogleIdentityClaims
from app.core.errors import AccessDeniedError
from app.models.auth_identity import AuthIdentity
from app.models.enums import AuthProvider
from app.models.user import User


def validate_google_identity(
    raw_claims: Mapping[str, Any],
    *,
    allowed_domains: Collection[str],
) -> GoogleIdentityClaims:
    claims = GoogleIdentityClaims.model_validate(raw_claims)
    if not claims.email_verified:
        raise AccessDeniedError("Google email is not verified")
    normalized_domains = {domain.strip().lower() for domain in allowed_domains}
    if normalized_domains and (claims.hd is None or claims.hd.lower() not in normalized_domains):
        raise AccessDeniedError("Google Workspace domain is not allowed")
    return claims


async def find_or_link_google_user(
    session: AsyncSession,
    claims: GoogleIdentityClaims,
) -> User:
    identity = await session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.provider == AuthProvider.GOOGLE,
            AuthIdentity.subject == claims.sub,
        )
    )
    if identity is not None:
        user = await session.get(User, identity.user_id)
        if user is None or not user.is_active:
            raise AccessDeniedError("User is not active")
        identity.provider_email = str(claims.email).lower()
        if claims.picture is not None:
            user.avatar_url = str(claims.picture)
        return user

    user = await session.scalar(
        select(User).where(
            func.lower(User.email) == str(claims.email).lower(),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise AccessDeniedError("User has not been invited")

    existing_google_identity = await session.scalar(
        select(AuthIdentity.id).where(
            AuthIdentity.user_id == user.id,
            AuthIdentity.provider == AuthProvider.GOOGLE,
        )
    )
    if existing_google_identity is not None:
        raise AccessDeniedError("Google identity is already linked")

    identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.GOOGLE,
        subject=claims.sub,
        provider_email=str(claims.email).lower(),
    )
    session.add(identity)
    if claims.picture is not None:
        user.avatar_url = str(claims.picture)
    await session.flush()
    return user
