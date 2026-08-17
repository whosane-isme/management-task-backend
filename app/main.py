from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.auth.oauth import create_oauth_registry
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import create_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        database = create_database(settings.database_url, echo=settings.database_echo)
        application.state.settings = settings
        application.state.database = database
        application.state.oauth = create_oauth_registry(settings)
        yield
        await database.engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.oauth_state_secret.get_secret_value(),
        session_cookie=settings.oauth_state_cookie_name,
        max_age=settings.oauth_state_max_age_seconds,
        same_site="lax",
        https_only=settings.cookie_secure,
    )
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Authorization", "Content-Type", "X-CSRF-Token"],
        )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
