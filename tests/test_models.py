from sqlalchemy import CheckConstraint, UniqueConstraint

import app.models  # noqa: F401
from app.db.base import Base


def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "activity_logs",
        "auth_identities",
        "departments",
        "permissions",
        "role_permissions",
        "roles",
        "task_assignments",
        "task_comments",
        "task_help_requests",
        "task_view_preferences",
        "tasks",
        "user_role_assignments",
        "users",
    }


def test_activity_log_has_required_foreign_keys() -> None:
    table = Base.metadata.tables["activity_logs"]
    targets = {foreign_key.target_fullname for foreign_key in table.foreign_keys}

    assert targets == {"tasks.id", "users.id"}


def test_identity_and_assignment_uniqueness_are_enforced() -> None:
    identity_constraints = Base.metadata.tables["auth_identities"].constraints
    assignment_constraints = Base.metadata.tables["task_assignments"].constraints

    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_auth_identities_provider_subject"
        for item in identity_constraints
    )
    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_task_assignments_task_user"
        for item in assignment_constraints
    )


def test_department_visibility_requires_department() -> None:
    constraints = Base.metadata.tables["tasks"].constraints

    assert any(
        isinstance(item, CheckConstraint) and item.name == "ck_tasks_department_visibility"
        for item in constraints
    )


def test_roles_use_permissions_instead_of_user_role_column() -> None:
    assert "role" not in Base.metadata.tables["users"].columns
    assert {"roles", "permissions", "role_permissions", "user_role_assignments"}.issubset(
        Base.metadata.tables
    )


def test_task_preferences_cannot_grant_access_fields() -> None:
    columns = set(Base.metadata.tables["task_view_preferences"].columns.keys())

    assert columns == {
        "viewer_id",
        "task_id",
        "is_hidden",
        "is_pinned",
        "updated_by_id",
        "created_at",
        "updated_at",
    }
