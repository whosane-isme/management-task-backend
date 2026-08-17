from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_database_session


class HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


class UnhealthySession:
    async def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("database credentials must not leak")


def test_liveness_does_not_require_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_succeeds_when_database_responds(app: FastAPI) -> None:
    async def healthy_session() -> AsyncIterator[HealthySession]:
        yield HealthySession()

    app.dependency_overrides[get_database_session] = healthy_session
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_hides_database_error(app: FastAPI) -> None:
    async def unhealthy_session() -> AsyncIterator[UnhealthySession]:
        yield UnhealthySession()

    app.dependency_overrides[get_database_session] = unhealthy_session
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service is not ready"}
    assert "credentials" not in response.text


def test_openapi_contains_versioned_health_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health/live" in response.json()["paths"]
    assert "/api/v1/health/ready" in response.json()["paths"]
