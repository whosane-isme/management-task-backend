import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.authorization.context import AuthorizationContext
from app.authorization.tasks import (
    TaskAccessFacts,
    can_assign_user,
    can_create_task,
    can_manage_task,
    can_manage_task_preferences,
    can_view_task,
    visible_task_predicate,
)
from app.core.permission_codes import PermissionCode
from app.models.enums import TaskVisibility
from app.models.task import Task


def context(
    *,
    user_id: int = 10,
    primary_department_id: int | None = 2,
    global_permissions: frozenset[str] = frozenset(),
    department_permissions: dict[int, frozenset[str]] | None = None,
) -> AuthorizationContext:
    return AuthorizationContext(
        user_id=user_id,
        primary_department_id=primary_department_id,
        global_permissions=global_permissions,
        department_permissions=department_permissions or {},
    )


@pytest.mark.parametrize("visibility", list(TaskVisibility))
def test_creator_and_assignee_can_view_every_visibility(visibility: TaskVisibility) -> None:
    creator_task = TaskAccessFacts(
        created_by_id=10,
        department_id=2,
        visibility=visibility,
    )
    assigned_task = TaskAccessFacts(
        created_by_id=99,
        department_id=2,
        visibility=visibility,
        assignee_ids=frozenset({10}),
    )

    assert can_view_task(context(), creator_task)
    assert can_view_task(context(), assigned_task)


def test_department_member_cannot_see_unrelated_private_task() -> None:
    task = TaskAccessFacts(
        created_by_id=99,
        department_id=2,
        visibility=TaskVisibility.PRIVATE,
    )

    assert not can_view_task(context(), task)


def test_department_manager_private_permission_is_scoped() -> None:
    manager = context(
        department_permissions={2: frozenset({PermissionCode.TASKS_VIEW_PRIVATE_DEPARTMENT})}
    )
    own_department_task = TaskAccessFacts(
        created_by_id=99,
        department_id=2,
        visibility=TaskVisibility.PRIVATE,
    )
    other_department_task = TaskAccessFacts(
        created_by_id=99,
        department_id=3,
        visibility=TaskVisibility.PRIVATE,
    )

    assert can_view_task(manager, own_department_task)
    assert not can_view_task(manager, other_department_task)


def test_organization_manager_can_view_and_manage_every_task() -> None:
    manager = context(
        global_permissions=frozenset(
            {PermissionCode.TASKS_VIEW_ALL, PermissionCode.TASKS_MANAGE_ALL}
        )
    )
    task = TaskAccessFacts(
        created_by_id=99,
        department_id=3,
        visibility=TaskVisibility.PRIVATE,
    )

    assert can_view_task(manager, task)
    assert can_manage_task(manager, task)


def test_employee_can_create_personal_task_but_not_team_task() -> None:
    employee = context(global_permissions=frozenset({PermissionCode.TASKS_CREATE_SELF}))

    assert can_create_task(employee, department_id=2, assignee_ids=frozenset({10}))
    assert not can_create_task(employee, department_id=2, assignee_ids=frozenset({10, 11}))
    assert can_assign_user(
        employee,
        target_user_id=10,
        target_department_id=2,
    )
    assert not can_assign_user(
        employee,
        target_user_id=11,
        target_department_id=2,
    )


def test_department_create_and_assign_permissions_do_not_escape_scope() -> None:
    manager = context(
        department_permissions={
            2: frozenset(
                {
                    PermissionCode.TASKS_CREATE_DEPARTMENT,
                    PermissionCode.TASKS_ASSIGN_DEPARTMENT,
                }
            )
        }
    )

    assert can_create_task(manager, department_id=2, assignee_ids=frozenset({11}))
    assert not can_create_task(manager, department_id=3, assignee_ids=frozenset({11}))
    assert can_assign_user(manager, target_user_id=11, target_department_id=2)
    assert not can_assign_user(manager, target_user_id=11, target_department_id=3)


def test_broad_assign_permission_allows_assigning_oneself() -> None:
    manager = context(global_permissions=frozenset({PermissionCode.TASKS_ASSIGN_ANY}))

    assert can_assign_user(manager, target_user_id=10, target_department_id=2)


def test_executive_assistant_can_organize_another_users_view() -> None:
    assistant = context(
        global_permissions=frozenset({PermissionCode.TASK_PREFERENCES_MANAGE_OTHERS})
    )

    assert can_manage_task_preferences(
        assistant,
        viewer_id=20,
        viewer_department_id=3,
    )


def test_regular_employee_cannot_organize_another_users_view() -> None:
    assert not can_manage_task_preferences(
        context(),
        viewer_id=20,
        viewer_department_id=2,
    )


def test_visible_task_predicate_contains_relationship_and_scope_checks() -> None:
    predicate = visible_task_predicate(context())
    statement = select(Task.id).where(predicate)
    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "EXISTS" in compiled
    assert "task_assignments.user_id = 10" in compiled
    assert "tasks.created_by_id = 10" in compiled
    assert "tasks.department_id IN (2)" in compiled


def test_view_all_compiles_to_unrestricted_authorized_predicate() -> None:
    manager = context(global_permissions=frozenset({PermissionCode.TASKS_VIEW_ALL}))
    statement = select(Task.id).where(visible_task_predicate(manager))
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "WHERE true" in compiled


def test_department_scoped_view_all_is_included_in_list_predicate() -> None:
    manager = context(
        department_permissions={
            2: frozenset({PermissionCode.TASKS_VIEW_ALL}),
        }
    )
    statement = select(Task.id).where(visible_task_predicate(manager))
    compiled = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "tasks.department_id IN (2)" in compiled
