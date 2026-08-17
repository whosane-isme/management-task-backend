import pytest

from app.core.errors import InvalidOperationError
from app.core.permission_codes import PermissionCode
from app.roles.service import validate_role_permission_codes


def test_organization_manager_must_retain_critical_permissions() -> None:
    with pytest.raises(InvalidOperationError, match=PermissionCode.ROLES_MANAGE):
        validate_role_permission_codes(
            "organization-manager",
            {
                PermissionCode.TASKS_VIEW_ALL,
                PermissionCode.TASKS_MANAGE_ALL,
                PermissionCode.USERS_MANAGE,
                PermissionCode.DEPARTMENTS_MANAGE,
            },
        )


def test_custom_role_can_have_any_permission_subset() -> None:
    validate_role_permission_codes("custom-secretary", {PermissionCode.TASKS_VIEW_ALL})


def test_organization_manager_cannot_lose_task_creation() -> None:
    with pytest.raises(InvalidOperationError, match=PermissionCode.TASKS_CREATE_ANY):
        validate_role_permission_codes(
            "organization-manager",
            {
                PermissionCode.TASKS_ASSIGN_ANY,
                PermissionCode.TASKS_VIEW_ALL,
                PermissionCode.TASKS_MANAGE_ALL,
                PermissionCode.TASK_PREFERENCES_MANAGE_OTHERS,
                PermissionCode.USERS_MANAGE,
                PermissionCode.DEPARTMENTS_MANAGE,
                PermissionCode.ROLES_MANAGE,
            },
        )
