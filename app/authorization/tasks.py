from dataclasses import dataclass

from sqlalchemy import and_, exists, false, or_, true
from sqlalchemy.sql.elements import ColumnElement

from app.authorization.context import AuthorizationContext
from app.core.permission_codes import PermissionCode
from app.models.enums import TaskVisibility
from app.models.task import Task
from app.models.task_assignment import TaskAssignment


@dataclass(frozen=True, slots=True)
class TaskAccessFacts:
    created_by_id: int
    department_id: int | None
    visibility: TaskVisibility
    assignee_ids: frozenset[int] = frozenset()


def can_view_task(context: AuthorizationContext, task: TaskAccessFacts) -> bool:
    if context.user_id == task.created_by_id or context.user_id in task.assignee_ids:
        return True
    if context.has_permission(PermissionCode.TASKS_VIEW_ALL, department_id=task.department_id):
        return True
    if task.visibility == TaskVisibility.PUBLIC:
        return True
    if task.visibility == TaskVisibility.DEPARTMENT:
        return context.primary_department_id == task.department_id or context.has_permission(
            PermissionCode.TASKS_VIEW_DEPARTMENT,
            department_id=task.department_id,
        )
    if task.visibility == TaskVisibility.PRIVATE:
        return context.has_permission(
            PermissionCode.TASKS_VIEW_PRIVATE_DEPARTMENT,
            department_id=task.department_id,
        )
    return False


def can_manage_task(context: AuthorizationContext, task: TaskAccessFacts) -> bool:
    if context.user_id == task.created_by_id:
        return True
    if context.has_permission(PermissionCode.TASKS_MANAGE_ALL, department_id=task.department_id):
        return True
    return context.has_permission(
        PermissionCode.TASKS_MANAGE_DEPARTMENT,
        department_id=task.department_id,
    )


def can_create_task(
    context: AuthorizationContext,
    *,
    department_id: int | None,
    assignee_ids: frozenset[int],
) -> bool:
    if context.has_permission(PermissionCode.TASKS_CREATE_ANY, department_id=department_id):
        return True
    if department_id is not None and context.has_permission(
        PermissionCode.TASKS_CREATE_DEPARTMENT,
        department_id=department_id,
    ):
        return True
    is_personal_task = not assignee_ids or assignee_ids == {context.user_id}
    return is_personal_task and context.has_permission(
        PermissionCode.TASKS_CREATE_SELF,
        department_id=department_id,
    )


def can_assign_user(
    context: AuthorizationContext,
    *,
    target_user_id: int,
    target_department_id: int | None,
) -> bool:
    if target_user_id == context.user_id:
        return any(
            context.has_permission(code, department_id=target_department_id)
            for code in (
                PermissionCode.TASKS_CREATE_SELF,
                PermissionCode.TASKS_ASSIGN_DEPARTMENT,
                PermissionCode.TASKS_ASSIGN_ANY,
            )
        )
    if context.has_permission(
        PermissionCode.TASKS_ASSIGN_ANY,
        department_id=target_department_id,
    ):
        return True
    return context.has_permission(
        PermissionCode.TASKS_ASSIGN_DEPARTMENT,
        department_id=target_department_id,
    )


def can_manage_task_preferences(
    context: AuthorizationContext,
    *,
    viewer_id: int,
    viewer_department_id: int | None,
) -> bool:
    return viewer_id == context.user_id or context.has_permission(
        PermissionCode.TASK_PREFERENCES_MANAGE_OTHERS,
        department_id=viewer_department_id,
    )


def visible_task_predicate(context: AuthorizationContext) -> ColumnElement[bool]:
    if PermissionCode.TASKS_VIEW_ALL in context.global_permissions:
        return true()

    assignment_exists = exists().where(
        TaskAssignment.task_id == Task.id,
        TaskAssignment.user_id == context.user_id,
    )
    clauses: list[ColumnElement[bool]] = [
        Task.visibility == TaskVisibility.PUBLIC,
        Task.created_by_id == context.user_id,
        assignment_exists,
    ]

    scoped_view_all_ids = context.departments_with(PermissionCode.TASKS_VIEW_ALL)
    if scoped_view_all_ids:
        clauses.append(Task.department_id.in_(scoped_view_all_ids))

    department_visibility_ids = set(context.departments_with(PermissionCode.TASKS_VIEW_DEPARTMENT))
    if context.primary_department_id is not None:
        department_visibility_ids.add(context.primary_department_id)
    if PermissionCode.TASKS_VIEW_DEPARTMENT in context.global_permissions:
        clauses.append(Task.visibility == TaskVisibility.DEPARTMENT)
    elif department_visibility_ids:
        clauses.append(
            and_(
                Task.visibility == TaskVisibility.DEPARTMENT,
                Task.department_id.in_(department_visibility_ids),
            )
        )

    private_department_ids = context.departments_with(PermissionCode.TASKS_VIEW_PRIVATE_DEPARTMENT)
    if PermissionCode.TASKS_VIEW_PRIVATE_DEPARTMENT in context.global_permissions:
        clauses.append(Task.visibility == TaskVisibility.PRIVATE)
    elif private_department_ids:
        clauses.append(
            and_(
                Task.visibility == TaskVisibility.PRIVATE,
                Task.department_id.in_(private_department_ids),
            )
        )

    if not clauses:
        return false()
    return or_(*clauses)
