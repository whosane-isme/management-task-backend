from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/test_db",
        cors_origins=[],
        trusted_hosts=["testserver"],
        oauth_state_secret=SecretStr("test-only-oauth-state-secret"),
        google_client_id=None,
        google_client_secret=None,
        google_redirect_uri=None,
        allowed_google_domains=[],
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
