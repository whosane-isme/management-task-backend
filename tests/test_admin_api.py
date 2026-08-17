import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.departments.routes as department_routes
import app.users.routes as user_routes
from app.auth.dependencies import Principal, get_current_principal
from app.auth.session_service import hash_secret
from app.authorization.context import AuthorizationContext
from app.core.errors import ResourceConflictError
from app.core.permission_codes import PermissionCode
from app.db.session import get_database_session
from app.models.department import Department
from app.models.user import User

CSRF_TOKEN = secrets.token_urlsafe(24)


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


def principal_with(*permissions: str) -> Principal:
    now = datetime.now(UTC)
    user = User(
        id=1,
        name="Manager",
        email="manager@example.com",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session = SimpleNamespace(csrf_token_hash=hash_secret(CSRF_TOKEN))
    authorization = AuthorizationContext(
        user_id=1,
        primary_department_id=None,
        global_permissions=frozenset(permissions),
        department_permissions={},
    )
    return Principal(user=user, session=session, authorization=authorization)


def install_dependencies(
    app: FastAPI,
    principal: Principal,
    fake_session: FakeSession,
) -> None:
    async def current_principal() -> Principal:
        return principal

    async def database_session() -> AsyncIterator[FakeSession]:
        yield fake_session

    app.dependency_overrides[get_current_principal] = current_principal
    app.dependency_overrides[get_database_session] = database_session


def enable_csrf(client: TestClient, app: FastAPI) -> dict[str, str]:
    client.cookies.set(app.state.settings.csrf_cookie_name, CSRF_TOKEN)
    return {"X-CSRF-Token": CSRF_TOKEN}


def user_record(user_id: int = 2) -> User:
    now = datetime.now(UTC)
    return User(
        id=user_id,
        name="Test Employee",
        email="employee@example.com",
        avatar_url=None,
        department_id=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def department_record() -> Department:
    now = datetime.now(UTC)
    return Department(
        id=3,
        name="Engineering",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_admin_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_me_exposes_effective_permission_codes(
    app: FastAPI,
    client: TestClient,
) -> None:
    install_dependencies(
        app,
        principal_with(PermissionCode.TASKS_CREATE_SELF, PermissionCode.USERS_MANAGE),
        FakeSession(),
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["global_permissions"] == [
        PermissionCode.TASKS_CREATE_SELF,
        PermissionCode.USERS_MANAGE,
    ]
    assert response.json()["department_permissions"] == {}


def test_user_list_requires_global_permission(app: FastAPI, client: TestClient) -> None:
    install_dependencies(app, principal_with(), FakeSession())

    response = client.get("/api/v1/users")

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_user_list_is_paginated(
    app: FastAPI,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    install_dependencies(app, principal_with(PermissionCode.USERS_MANAGE), fake_session)
    received: dict[str, object] = {}

    async def fake_list_users(
        _session: object,
        *,
        limit: int,
        offset: int,
        include_inactive: bool,
    ) -> tuple[list[User], int]:
        received.update(limit=limit, offset=offset, include_inactive=include_inactive)
        return [user_record()], 7

    monkeypatch.setattr(user_routes, "list_users", fake_list_users)

    response = client.get("/api/v1/users?limit=10&offset=5&include_inactive=true")

    assert response.status_code == 200
    assert response.json()["total"] == 7
    assert response.json()["items"][0]["email"] == "employee@example.com"
    assert received == {"limit": 10, "offset": 5, "include_inactive": True}


def test_pagination_rejects_excessive_limit(
    app: FastAPI,
    client: TestClient,
) -> None:
    install_dependencies(app, principal_with(PermissionCode.USERS_MANAGE), FakeSession())

    response = client.get("/api/v1/users?limit=101")

    assert response.status_code == 422


def test_admin_writes_require_csrf(
    app: FastAPI,
    client: TestClient,
) -> None:
    install_dependencies(
        app,
        principal_with(PermissionCode.DEPARTMENTS_MANAGE),
        FakeSession(),
    )

    response = client.post("/api/v1/departments", json={"name": "Engineering"})

    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF validation failed"}


def test_department_can_be_created_by_authorized_manager(
    app: FastAPI,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = FakeSession()
    install_dependencies(
        app,
        principal_with(PermissionCode.DEPARTMENTS_MANAGE),
        fake_session,
    )

    async def fake_create_department(_session: object, _data: object) -> Department:
        return department_record()

    monkeypatch.setattr(department_routes, "create_department", fake_create_department)

    response = client.post(
        "/api/v1/departments",
        json={"name": "Engineering"},
        headers=enable_csrf(client, app),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Engineering"
    assert fake_session.commit_count == 1


def test_domain_conflict_becomes_http_409(
    app: FastAPI,
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_dependencies(app, principal_with(PermissionCode.USERS_MANAGE), FakeSession())

    async def conflicting_create_user(
        _session: object,
        _data: object,
        *,
        created_by_id: int,
    ) -> User:
        del created_by_id
        raise ResourceConflictError("A user with this email already exists")

    monkeypatch.setattr(user_routes, "create_user", conflicting_create_user)

    response = client.post(
        "/api/v1/users",
        json={"name": "Duplicate", "email": "duplicate@example.com"},
        headers=enable_csrf(client, app),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A user with this email already exists",
        "code": "conflict",
    }


def test_assigning_roles_requires_role_management_permission(
    app: FastAPI,
    client: TestClient,
) -> None:
    install_dependencies(app, principal_with(PermissionCode.USERS_MANAGE), FakeSession())

    response = client.post(
        "/api/v1/users/2/role-assignments",
        json={"role_id": 1},
        headers=enable_csrf(client, app),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permissions"}


def test_deactivation_rejects_current_user(
    app: FastAPI,
    client: TestClient,
) -> None:
    install_dependencies(app, principal_with(PermissionCode.USERS_MANAGE), FakeSession())

    response = client.post(
        "/api/v1/users/1/deactivate",
        headers=enable_csrf(client, app),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_operation"
