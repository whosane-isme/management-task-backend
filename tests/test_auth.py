from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import RedirectResponse

from app.auth.google_service import validate_google_identity
from app.auth.session_service import create_user_session, hash_secret
from app.core.errors import AccessDeniedError


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        return None


class FakeGoogleClient:
    async def authorize_redirect(
        self,
        _request: object,
        redirect_uri: str,
        **_kwargs: object,
    ) -> RedirectResponse:
        return RedirectResponse(f"https://accounts.example/authorize?redirect_uri={redirect_uri}")


class FakeOAuthRegistry:
    def create_client(self, name: str) -> FakeGoogleClient | None:
        return FakeGoogleClient() if name == "google" else None


def test_google_login_reports_missing_configuration(client: TestClient) -> None:
    response = client.get("/api/v1/auth/google/login")

    assert response.status_code == 503
    assert response.json() == {"detail": "Google authentication is not configured"}


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_google_login_redirects_when_client_is_configured(app: FastAPI) -> None:
    with TestClient(app, follow_redirects=False) as client:
        app.state.oauth = FakeOAuthRegistry()
        response = client.get("/api/v1/auth/google/login")

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.example/authorize")


def test_verified_google_identity_is_accepted() -> None:
    claims = validate_google_identity(
        {
            "sub": "google-subject",
            "email": "EMPLOYEE@EXAMPLE.COM",
            "email_verified": True,
            "hd": "example.com",
        },
        allowed_domains={"example.com"},
    )

    assert str(claims.email) == "EMPLOYEE@example.com"


@pytest.mark.parametrize(
    "claims",
    [
        {
            "sub": "google-subject",
            "email": "employee@example.com",
            "email_verified": False,
            "hd": "example.com",
        },
        {
            "sub": "google-subject",
            "email": "employee@outside.example",
            "email_verified": True,
            "hd": "outside.example",
        },
    ],
)
def test_unverified_or_wrong_domain_google_identity_is_denied(
    claims: dict[str, object],
) -> None:
    with pytest.raises(AccessDeniedError):
        validate_google_identity(claims, allowed_domains={"example.com"})


@pytest.mark.asyncio
async def test_server_session_stores_only_token_hashes() -> None:
    session = FakeSession()
    now = datetime(2026, 8, 17, tzinfo=UTC)

    issued = await create_user_session(
        session,  # type: ignore[arg-type]
        user_id=42,
        lifetime=timedelta(hours=12),
        now=now,
    )

    assert issued.record in session.added
    assert issued.record.token_hash == hash_secret(issued.token)
    assert issued.record.csrf_token_hash == hash_secret(issued.csrf_token)
    assert issued.token not in issued.record.token_hash
    assert issued.csrf_token not in issued.record.csrf_token_hash
    assert issued.record.expires_at == now + timedelta(hours=12)
