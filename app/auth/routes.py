import logging
from datetime import timedelta
from typing import Any, Protocol, cast

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, Response, status
from httpx import HTTPError
from joserfc.errors import JoseError
from pydantic import ValidationError
from starlette.responses import RedirectResponse

from app.auth.dependencies import CsrfProtectedPrincipal, CurrentPrincipal
from app.auth.google_service import find_or_link_google_user, validate_google_identity
from app.auth.session_service import create_user_session, revoke_user_session
from app.core.config import Settings
from app.core.errors import AccessDeniedError
from app.db.session import DatabaseSession
from app.users.schemas import CurrentUserRead, UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


class GoogleOAuthClient(Protocol):
    async def authorize_redirect(
        self,
        request: Request,
        redirect_uri: str,
        **kwargs: object,
    ) -> RedirectResponse: ...

    async def authorize_access_token(
        self,
        request: Request,
        **kwargs: object,
    ) -> dict[str, Any]: ...


def get_google_client(request: Request) -> GoogleOAuthClient:
    oauth = cast(OAuth, request.app.state.oauth)
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google authentication is not configured",
        )
    return cast(GoogleOAuthClient, client)


@router.get("/google/login")
async def google_login(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    redirect_uri = settings.google_redirect_uri or str(request.url_for("google_callback"))
    return await get_google_client(request).authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, session: DatabaseSession) -> Response:
    settings: Settings = request.app.state.settings
    try:
        token = await get_google_client(request).authorize_access_token(
            request,
            claims_options={
                "iss": {
                    "essential": True,
                    "values": ["https://accounts.google.com", "accounts.google.com"],
                },
                "aud": {"essential": True, "value": settings.google_client_id},
                "exp": {"essential": True},
                "sub": {"essential": True},
                "email": {"essential": True},
            },
        )
        raw_userinfo = token.get("userinfo")
        if not isinstance(raw_userinfo, dict):
            raise AccessDeniedError("Google ID token did not contain user information")
        claims = validate_google_identity(
            raw_userinfo,
            allowed_domains=settings.allowed_google_domains,
        )
        user = await find_or_link_google_user(session, claims)
        issued = await create_user_session(
            session,
            user_id=user.id,
            lifetime=timedelta(hours=settings.session_ttl_hours),
        )
        await session.commit()
    except AccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Google account is not allowed",
        ) from exc
    except (OAuthError, JoseError, ValidationError, HTTPError) as exc:
        logger.warning("Google authentication failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed",
        ) from exc

    request.session.clear()
    response = RedirectResponse(settings.frontend_auth_success_url, status_code=303)
    max_age = settings.session_ttl_hours * 60 * 60
    response.set_cookie(
        settings.auth_cookie_name,
        issued.token,
        max_age=max_age,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        issued.csrf_token,
        max_age=max_age,
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me", response_model=CurrentUserRead)
async def get_me(principal: CurrentPrincipal) -> Any:
    user_data = UserRead.model_validate(principal.user).model_dump()
    return CurrentUserRead.model_validate(
        {
            **user_data,
            "global_permissions": sorted(principal.authorization.global_permissions),
            "department_permissions": {
                department_id: sorted(permissions)
                for department_id, permissions in sorted(
                    principal.authorization.department_permissions.items()
                )
            },
        }
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> Response:
    settings: Settings = request.app.state.settings
    await revoke_user_session(session, principal.session)
    await session.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    return response
