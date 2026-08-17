import hmac
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.auth.session_service import authenticate_user_session, hash_secret
from app.authorization.context import AuthorizationContext, load_authorization_context
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.db.session import DatabaseSession
from app.models.user import User
from app.models.user_session import UserSession


@dataclass(frozen=True, slots=True)
class Principal:
    user: User
    session: UserSession
    authorization: AuthorizationContext


async def get_current_principal(
    request: Request,
    database_session: DatabaseSession,
) -> Principal:
    settings: Settings = request.app.state.settings
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        authenticated = await authenticate_user_session(
            database_session,
            raw_token=raw_token,
            idle_timeout=timedelta(minutes=settings.session_idle_minutes),
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from exc

    if authenticated.needs_touch:
        await database_session.commit()
    authorization = await load_authorization_context(database_session, authenticated.user.id)
    return Principal(
        user=authenticated.user,
        session=authenticated.record,
        authorization=authorization,
    )


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def require_csrf(request: Request, principal: CurrentPrincipal) -> Principal:
    settings: Settings = request.app.state.settings
    header_token = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    tokens_match = (
        header_token is not None
        and cookie_token is not None
        and hmac.compare_digest(header_token, cookie_token)
        and hmac.compare_digest(hash_secret(header_token), principal.session.csrf_token_hash)
    )
    if not tokens_match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
    return principal


CsrfProtectedPrincipal = Annotated[Principal, Depends(require_csrf)]
