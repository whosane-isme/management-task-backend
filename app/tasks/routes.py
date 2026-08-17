from typing import Annotated

from fastapi import APIRouter, Query, status

from app.auth.dependencies import CsrfProtectedPrincipal, CurrentPrincipal
from app.db.session import DatabaseSession
from app.models.enums import TaskPriority, TaskStatus, TaskVisibility
from app.tasks.schemas import (
    HelpRequestCreate,
    TaskAssignmentCreate,
    TaskCreate,
    TaskListView,
    TaskPage,
    TaskPreferenceRead,
    TaskPreferenceUpdate,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.tasks.service import (
    accept_help_request,
    add_assignment,
    cancel_help_request,
    create_help_request,
    create_task,
    get_task,
    list_tasks,
    remove_assignment,
    resolve_help_request,
    transition_task_status,
    update_task,
    update_task_preference,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])
preferences_router = APIRouter(prefix="/task-preferences", tags=["task preferences"])


@router.get("")
async def get_tasks(
    principal: CurrentPrincipal,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    view: TaskListView = TaskListView.FOCUS,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    visibility: TaskVisibility | None = None,
    department_id: Annotated[int | None, Query(ge=1)] = None,
    assignee_id: Annotated[int | None, Query(ge=1)] = None,
    created_by_id: Annotated[int | None, Query(ge=1)] = None,
    query: Annotated[str | None, Query(alias="q", max_length=200)] = None,
) -> TaskPage:
    items, total = await list_tasks(
        session,
        principal,
        limit=limit,
        offset=offset,
        view=view,
        status_filter=status_filter,
        priority=priority,
        visibility=visibility,
        department_id=department_id,
        assignee_id=assignee_id,
        created_by_id=created_by_id,
        query=query,
    )
    return TaskPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_task(
    data: TaskCreate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await create_task(session, data, principal)
    await session.commit()
    return task


@router.get("/{task_id}")
async def get_task_by_id(
    task_id: int,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    return await get_task(session, task_id, principal)


@router.patch("/{task_id}")
async def patch_task(
    task_id: int,
    data: TaskUpdate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await update_task(session, task_id, data, principal)
    await session.commit()
    return task


@router.post("/{task_id}/status")
async def post_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await transition_task_status(session, task_id, data.status, principal)
    await session.commit()
    return task


@router.post("/{task_id}/assignments", status_code=status.HTTP_201_CREATED)
async def post_task_assignment(
    task_id: int,
    data: TaskAssignmentCreate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await add_assignment(session, task_id, data.user_id, principal)
    await session.commit()
    return task


@router.delete("/{task_id}/assignments/{user_id}")
async def delete_task_assignment(
    task_id: int,
    user_id: int,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await remove_assignment(session, task_id, user_id, principal)
    await session.commit()
    return task


@router.post("/{task_id}/help-request", status_code=status.HTTP_201_CREATED)
async def post_help_request(
    task_id: int,
    data: HelpRequestCreate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await create_help_request(session, task_id, data, principal)
    await session.commit()
    return task


@router.delete("/{task_id}/help-request")
async def delete_help_request(
    task_id: int,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await cancel_help_request(session, task_id, principal)
    await session.commit()
    return task


@router.post("/{task_id}/help-request/accept")
async def post_accept_help_request(
    task_id: int,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await accept_help_request(session, task_id, principal)
    await session.commit()
    return task


@router.post("/{task_id}/help-request/resolve")
async def post_resolve_help_request(
    task_id: int,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskRead:
    task = await resolve_help_request(session, task_id, principal)
    await session.commit()
    return task


@preferences_router.put("/{task_id}")
async def put_task_preference(
    task_id: int,
    data: TaskPreferenceUpdate,
    principal: CsrfProtectedPrincipal,
    session: DatabaseSession,
) -> TaskPreferenceRead:
    preference = await update_task_preference(session, task_id, data, principal)
    await session.commit()
    return preference
