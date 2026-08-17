from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.auth.dependencies import Principal
from app.authorization.context import AuthorizationContext, load_authorization_context
from app.authorization.tasks import (
    TaskAccessFacts,
    can_assign_user,
    can_create_task,
    can_manage_task,
    can_manage_task_preferences,
    visible_task_predicate,
)
from app.core.errors import (
    AccessDeniedError,
    InvalidOperationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.permission_codes import PermissionCode
from app.models.activity_log import ActivityLog
from app.models.department import Department
from app.models.enums import HelpRequestStatus, TaskPriority, TaskStatus, TaskVisibility
from app.models.task import Task
from app.models.task_assignment import TaskAssignment
from app.models.task_help_request import TaskHelpRequest
from app.models.task_view_preference import TaskViewPreference
from app.models.user import User
from app.tasks.schemas import (
    DepartmentSummary,
    HelpRequestCreate,
    HelpRequestRead,
    TaskAssignmentRead,
    TaskCreate,
    TaskListView,
    TaskPreferenceRead,
    TaskPreferenceUpdate,
    TaskRead,
    TaskUpdate,
    UserSummary,
)

ACTIVE_HELP_STATUSES = (HelpRequestStatus.OPEN, HelpRequestStatus.ACCEPTED)

ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.TODO: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
    TaskStatus.IN_PROGRESS: frozenset(
        {TaskStatus.TODO, TaskStatus.IN_REVIEW, TaskStatus.DONE, TaskStatus.CANCELLED}
    ),
    TaskStatus.IN_REVIEW: frozenset(
        {TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.CANCELLED}
    ),
    TaskStatus.DONE: frozenset({TaskStatus.IN_PROGRESS}),
    TaskStatus.CANCELLED: frozenset({TaskStatus.TODO}),
}


def _task_load_options(viewer_id: int) -> tuple[Any, ...]:
    return (
        selectinload(Task.creator),
        selectinload(Task.department),
        selectinload(Task.assignments).selectinload(TaskAssignment.assignee),
        selectinload(Task.help_requests),
        selectinload(Task.view_preferences),
        with_loader_criteria(
            TaskHelpRequest,
            TaskHelpRequest.status.in_(ACTIVE_HELP_STATUSES),
            include_aliases=True,
        ),
        with_loader_criteria(
            TaskViewPreference,
            TaskViewPreference.viewer_id == viewer_id,
            include_aliases=True,
        ),
    )


def task_to_read(task: Task, *, viewer_id: int) -> TaskRead:
    active_help_request = next(
        (request for request in task.help_requests if request.status in ACTIVE_HELP_STATUSES),
        None,
    )
    preference = next(
        (item for item in task.view_preferences if item.viewer_id == viewer_id),
        None,
    )
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        visibility=task.visibility,
        created_by_id=task.created_by_id,
        creator=UserSummary.model_validate(task.creator),
        department_id=task.department_id,
        department=(
            DepartmentSummary.model_validate(task.department)
            if task.department is not None
            else None
        ),
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        assignments=[
            TaskAssignmentRead(
                user=UserSummary.model_validate(assignment.assignee),
                assigned_by_id=assignment.assigned_by_id,
                created_at=assignment.created_at,
            )
            for assignment in task.assignments
        ],
        help_request=(
            HelpRequestRead.model_validate(active_help_request)
            if active_help_request is not None
            else None
        ),
        preference=(
            TaskPreferenceRead(
                viewer_id=preference.viewer_id,
                task_id=preference.task_id,
                is_hidden=preference.is_hidden,
                is_pinned=preference.is_pinned,
                updated_by_id=preference.updated_by_id,
                updated_at=preference.updated_at,
            )
            if preference is not None
            else None
        ),
    )


def _task_facts(task: Task) -> TaskAccessFacts:
    return TaskAccessFacts(
        created_by_id=task.created_by_id,
        department_id=task.department_id,
        visibility=task.visibility,
        assignee_ids=frozenset(assignment.user_id for assignment in task.assignments),
    )


def _record_activity(
    session: AsyncSession,
    *,
    task_id: int,
    actor_id: int,
    event_type: str,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        ActivityLog(
            task_id=task_id,
            actor_id=actor_id,
            event_type=event_type,
            details=details or {},
        )
    )


async def _load_task(
    session: AsyncSession,
    task_id: int,
    context: AuthorizationContext,
    *,
    populate_existing: bool = False,
) -> Task:
    statement = (
        select(Task)
        .where(Task.id == task_id, visible_task_predicate(context))
        .options(*_task_load_options(context.user_id))
    )
    if populate_existing:
        statement = statement.execution_options(populate_existing=True)
    task = await session.scalar(statement)
    if task is None:
        raise ResourceNotFoundError("Task not found")
    return task


async def _active_department(session: AsyncSession, department_id: int) -> Department:
    department = await session.scalar(
        select(Department).where(
            Department.id == department_id,
            Department.is_active.is_(True),
        )
    )
    if department is None:
        raise ResourceNotFoundError("Active department not found")
    return department


async def _active_users(session: AsyncSession, user_ids: set[int]) -> dict[int, User]:
    result = await session.scalars(
        select(User).where(User.id.in_(user_ids), User.is_active.is_(True))
    )
    users = {user.id: user for user in result}
    if set(users) != user_ids:
        raise ResourceNotFoundError("One or more active assignees do not exist")
    return users


def _ensure_can_assign(
    context: AuthorizationContext,
    *,
    target: User,
    task_department_id: int | None,
) -> None:
    if not can_assign_user(
        context,
        target_user_id=target.id,
        target_department_id=target.department_id,
    ):
        raise AccessDeniedError("You cannot assign this user")
    crosses_department = (
        task_department_id is not None and target.department_id != task_department_id
    )
    if crosses_department and PermissionCode.TASKS_ASSIGN_ANY not in context.global_permissions:
        raise AccessDeniedError("Cross-department assignment requires organization scope")


async def get_task(session: AsyncSession, task_id: int, principal: Principal) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    return task_to_read(task, viewer_id=principal.user.id)


async def list_tasks(
    session: AsyncSession,
    principal: Principal,
    *,
    limit: int,
    offset: int,
    view: TaskListView,
    status_filter: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    visibility: TaskVisibility | None = None,
    department_id: int | None = None,
    assignee_id: int | None = None,
    created_by_id: int | None = None,
    query: str | None = None,
) -> tuple[list[TaskRead], int]:
    user_id = principal.user.id
    preference_join = and_(
        TaskViewPreference.task_id == Task.id,
        TaskViewPreference.viewer_id == user_id,
    )
    assignment_exists = exists().where(
        TaskAssignment.task_id == Task.id,
        TaskAssignment.user_id == user_id,
    )
    filters = [visible_task_predicate(principal.authorization)]

    if view == TaskListView.FOCUS:
        filters.extend(
            [
                or_(
                    TaskViewPreference.viewer_id.is_(None),
                    TaskViewPreference.is_hidden.is_(False),
                ),
                or_(
                    Task.created_by_id == user_id,
                    assignment_exists,
                    TaskViewPreference.is_pinned.is_(True),
                ),
            ]
        )
        if status_filter is None:
            filters.append(Task.status != TaskStatus.CANCELLED)
    elif view == TaskListView.HIDDEN:
        filters.append(TaskViewPreference.is_hidden.is_(True))
    elif view == TaskListView.PINNED:
        filters.append(TaskViewPreference.is_pinned.is_(True))

    if status_filter is not None:
        filters.append(Task.status == status_filter)
    if priority is not None:
        filters.append(Task.priority == priority)
    if visibility is not None:
        filters.append(Task.visibility == visibility)
    if department_id is not None:
        filters.append(Task.department_id == department_id)
    if assignee_id is not None:
        filters.append(
            exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.user_id == assignee_id,
            )
        )
    if created_by_id is not None:
        filters.append(Task.created_by_id == created_by_id)
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(
            or_(
                Task.title.ilike(pattern),
                func.coalesce(Task.description, "").ilike(pattern),
            )
        )

    total = await session.scalar(
        select(func.count())
        .select_from(Task)
        .outerjoin(TaskViewPreference, preference_join)
        .where(*filters)
    )
    result = await session.scalars(
        select(Task)
        .outerjoin(TaskViewPreference, preference_join)
        .where(*filters)
        .options(*_task_load_options(user_id))
        .order_by(
            TaskViewPreference.is_pinned.desc(),
            Task.due_at.asc().nullslast(),
            Task.updated_at.desc(),
            Task.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    tasks = list(result)
    return [task_to_read(task, viewer_id=user_id) for task in tasks], total or 0


async def create_task(session: AsyncSession, data: TaskCreate, principal: Principal) -> TaskRead:
    context = principal.authorization
    department_id = data.department_id or context.primary_department_id
    if data.visibility == TaskVisibility.DEPARTMENT and department_id is None:
        raise InvalidOperationError("Department visibility requires a department")
    if department_id is not None:
        await _active_department(session, department_id)

    assignee_ids = set(data.assignee_ids) or {principal.user.id}
    users = await _active_users(session, assignee_ids)
    if not can_create_task(
        context,
        department_id=department_id,
        assignee_ids=frozenset(assignee_ids),
    ):
        raise AccessDeniedError("You cannot create this task")
    for user in users.values():
        _ensure_can_assign(
            context,
            target=user,
            task_department_id=department_id,
        )

    task = Task(
        title=data.title,
        description=data.description,
        priority=data.priority,
        visibility=data.visibility,
        created_by_id=principal.user.id,
        department_id=department_id,
        due_at=data.due_at,
    )
    session.add(task)
    await session.flush()
    session.add_all(
        TaskAssignment(
            task_id=task.id,
            user_id=user_id,
            assigned_by_id=principal.user.id,
        )
        for user_id in sorted(assignee_ids)
    )
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.created",
        details={
            "assignee_ids": sorted(assignee_ids),
            "visibility": data.visibility.value,
            "department_id": department_id,
        },
    )
    await session.flush()
    created = await _load_task(
        session,
        task.id,
        context,
        populate_existing=True,
    )
    return task_to_read(created, viewer_id=principal.user.id)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


async def update_task(
    session: AsyncSession,
    task_id: int,
    data: TaskUpdate,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    if not can_manage_task(principal.authorization, _task_facts(task)):
        raise AccessDeniedError("You cannot modify this task")
    if not data.model_fields_set:
        return task_to_read(task, viewer_id=principal.user.id)

    proposed_department_id = (
        data.department_id if "department_id" in data.model_fields_set else task.department_id
    )
    proposed_visibility = (
        data.visibility if "visibility" in data.model_fields_set else task.visibility
    )
    if proposed_visibility == TaskVisibility.DEPARTMENT and proposed_department_id is None:
        raise InvalidOperationError("Department visibility requires a department")
    if proposed_department_id is not None:
        await _active_department(session, proposed_department_id)

    if proposed_department_id != task.department_id:
        assignee_ids = frozenset(item.user_id for item in task.assignments)
        if not can_create_task(
            principal.authorization,
            department_id=proposed_department_id,
            assignee_ids=assignee_ids,
        ):
            raise AccessDeniedError("You cannot move this task to that department")
        users = await _active_users(session, set(assignee_ids))
        for user in users.values():
            _ensure_can_assign(
                principal.authorization,
                target=user,
                task_department_id=proposed_department_id,
            )

    changes: dict[str, dict[str, Any]] = {}
    for field in ("title", "description", "priority", "visibility", "department_id", "due_at"):
        if field not in data.model_fields_set:
            continue
        new_value = getattr(data, field)
        old_value = getattr(task, field)
        if old_value != new_value:
            changes[field] = {
                "from": _json_value(old_value),
                "to": _json_value(new_value),
            }
            setattr(task, field, new_value)

    if changes:
        _record_activity(
            session,
            task_id=task.id,
            actor_id=principal.user.id,
            event_type="task.updated",
            details={"changes": changes},
        )
        await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def transition_task_status(
    session: AsyncSession,
    task_id: int,
    new_status: TaskStatus,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    facts = _task_facts(task)
    is_assignee = principal.user.id in facts.assignee_ids
    can_manage = can_manage_task(principal.authorization, facts)
    if not is_assignee and not can_manage:
        raise AccessDeniedError("You cannot change this task status")
    is_manager_only_transition = new_status == TaskStatus.CANCELLED or task.status in {
        TaskStatus.DONE,
        TaskStatus.CANCELLED,
    }
    if is_manager_only_transition and not can_manage:
        raise AccessDeniedError("Only the task owner or manager can cancel or reopen it")
    if new_status == task.status:
        return task_to_read(task, viewer_id=principal.user.id)
    if new_status not in ALLOWED_STATUS_TRANSITIONS[task.status]:
        raise InvalidOperationError(
            f"Cannot transition task from {task.status.value} to {new_status.value}"
        )

    old_status = task.status
    task.status = new_status
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.status_changed",
        details={"from": old_status.value, "to": new_status.value},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def add_assignment(
    session: AsyncSession,
    task_id: int,
    user_id: int,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    if not can_manage_task(principal.authorization, _task_facts(task)):
        raise AccessDeniedError("You cannot assign this task")
    if any(item.user_id == user_id for item in task.assignments):
        raise ResourceConflictError("User is already assigned to this task")
    target = (await _active_users(session, {user_id}))[user_id]
    _ensure_can_assign(
        principal.authorization,
        target=target,
        task_department_id=task.department_id,
    )

    assignment = TaskAssignment(
        task_id=task.id,
        user_id=user_id,
        assigned_by_id=principal.user.id,
    )
    try:
        async with session.begin_nested():
            session.add(assignment)
            await session.flush()
    except IntegrityError as exc:
        raise ResourceConflictError("User is already assigned to this task") from exc
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.assigned",
        details={"user_id": user_id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def remove_assignment(
    session: AsyncSession,
    task_id: int,
    user_id: int,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    if not can_manage_task(principal.authorization, _task_facts(task)):
        raise AccessDeniedError("You cannot unassign this task")
    assignment = next((item for item in task.assignments if item.user_id == user_id), None)
    if assignment is None:
        raise ResourceNotFoundError("Task assignment not found")

    await session.delete(assignment)
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.unassigned",
        details={"user_id": user_id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def _get_active_help_request(
    session: AsyncSession,
    task_id: int,
    *,
    for_update: bool = False,
) -> TaskHelpRequest:
    statement = select(TaskHelpRequest).where(
        TaskHelpRequest.task_id == task_id,
        TaskHelpRequest.status.in_(ACTIVE_HELP_STATUSES),
    )
    if for_update:
        statement = statement.with_for_update()
    request = await session.scalar(statement)
    if request is None:
        raise ResourceNotFoundError("Active help request not found")
    return request


async def create_help_request(
    session: AsyncSession,
    task_id: int,
    data: HelpRequestCreate,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    facts = _task_facts(task)
    if (
        principal.user.id not in facts.assignee_ids
        and principal.user.id != facts.created_by_id
        and not can_manage_task(principal.authorization, facts)
    ):
        raise AccessDeniedError("Only task participants can request help")
    existing_id = await session.scalar(
        select(TaskHelpRequest.id).where(
            TaskHelpRequest.task_id == task.id,
            TaskHelpRequest.status.in_(ACTIVE_HELP_STATUSES),
        )
    )
    if existing_id is not None:
        raise ResourceConflictError("Task already has an active help request")

    request = TaskHelpRequest(
        task_id=task.id,
        requested_by_id=principal.user.id,
        message=data.message,
        status=HelpRequestStatus.OPEN,
    )
    try:
        async with session.begin_nested():
            session.add(request)
            await session.flush()
    except IntegrityError as exc:
        raise ResourceConflictError("Task already has an active help request") from exc
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.help_requested",
        details={"help_request_id": request.id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def cancel_help_request(
    session: AsyncSession,
    task_id: int,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    request = await _get_active_help_request(session, task.id, for_update=True)
    if request.requested_by_id != principal.user.id and not can_manage_task(
        principal.authorization, _task_facts(task)
    ):
        raise AccessDeniedError("You cannot cancel this help request")
    request.status = HelpRequestStatus.CANCELLED
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.help_cancelled",
        details={"help_request_id": request.id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def accept_help_request(
    session: AsyncSession,
    task_id: int,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    request = await _get_active_help_request(session, task.id, for_update=True)
    if request.status != HelpRequestStatus.OPEN:
        raise InvalidOperationError("Help request has already been accepted")
    if request.requested_by_id == principal.user.id:
        raise InvalidOperationError("Requester cannot accept their own help request")

    request.status = HelpRequestStatus.ACCEPTED
    request.accepted_by_id = principal.user.id
    if all(item.user_id != principal.user.id for item in task.assignments):
        session.add(
            TaskAssignment(
                task_id=task.id,
                user_id=principal.user.id,
                assigned_by_id=principal.user.id,
            )
        )
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.help_accepted",
        details={"help_request_id": request.id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def resolve_help_request(
    session: AsyncSession,
    task_id: int,
    principal: Principal,
) -> TaskRead:
    task = await _load_task(session, task_id, principal.authorization)
    request = await _get_active_help_request(session, task.id, for_update=True)
    allowed_actor_ids = {request.requested_by_id, request.accepted_by_id}
    if principal.user.id not in allowed_actor_ids and not can_manage_task(
        principal.authorization, _task_facts(task)
    ):
        raise AccessDeniedError("You cannot resolve this help request")
    request.status = HelpRequestStatus.RESOLVED
    request.resolved_at = datetime.now(UTC)
    _record_activity(
        session,
        task_id=task.id,
        actor_id=principal.user.id,
        event_type="task.help_resolved",
        details={"help_request_id": request.id},
    )
    await session.flush()
    updated = await _load_task(
        session,
        task.id,
        principal.authorization,
        populate_existing=True,
    )
    return task_to_read(updated, viewer_id=principal.user.id)


async def update_task_preference(
    session: AsyncSession,
    task_id: int,
    data: TaskPreferenceUpdate,
    principal: Principal,
) -> TaskPreferenceRead:
    viewer_id = data.viewer_id or principal.user.id
    viewer = await session.scalar(
        select(User).where(User.id == viewer_id, User.is_active.is_(True))
    )
    if viewer is None:
        raise ResourceNotFoundError("Active preference viewer not found")
    if not can_manage_task_preferences(
        principal.authorization,
        viewer_id=viewer.id,
        viewer_department_id=viewer.department_id,
    ):
        raise AccessDeniedError("You cannot organize this user's task view")

    viewer_context = (
        principal.authorization
        if viewer_id == principal.user.id
        else await load_authorization_context(session, viewer_id)
    )
    await _load_task(session, task_id, viewer_context)

    preference = await session.get(TaskViewPreference, (viewer_id, task_id))
    if not data.is_hidden and not data.is_pinned:
        if preference is not None:
            await session.delete(preference)
        _record_activity(
            session,
            task_id=task_id,
            actor_id=principal.user.id,
            event_type="task.preference_cleared",
            details={"viewer_id": viewer_id},
        )
        await session.flush()
        return TaskPreferenceRead(
            viewer_id=viewer_id,
            task_id=task_id,
            is_hidden=False,
            is_pinned=False,
            updated_by_id=principal.user.id,
        )

    if preference is None:
        preference = TaskViewPreference(
            viewer_id=viewer_id,
            task_id=task_id,
            updated_by_id=principal.user.id,
        )
        session.add(preference)
    preference.is_hidden = data.is_hidden
    preference.is_pinned = data.is_pinned
    preference.updated_by_id = principal.user.id
    _record_activity(
        session,
        task_id=task_id,
        actor_id=principal.user.id,
        event_type="task.preference_updated",
        details={
            "viewer_id": viewer_id,
            "is_hidden": data.is_hidden,
            "is_pinned": data.is_pinned,
        },
    )
    await session.flush()
    await session.refresh(preference)
    return TaskPreferenceRead(
        viewer_id=preference.viewer_id,
        task_id=preference.task_id,
        is_hidden=preference.is_hidden,
        is_pinned=preference.is_pinned,
        updated_by_id=preference.updated_by_id,
        updated_at=preference.updated_at,
    )
