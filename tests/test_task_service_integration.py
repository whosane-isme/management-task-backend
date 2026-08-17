import os
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.dependencies import Principal
from app.authorization.context import AuthorizationContext
from app.core.errors import AccessDeniedError, InvalidOperationError, ResourceNotFoundError
from app.core.permission_codes import PermissionCode
from app.models.department import Department
from app.models.enums import TaskStatus, TaskVisibility
from app.models.permission import Permission
from app.models.user import User
from app.roles.schemas import RoleCreate, RoleRead
from app.roles.service import create_role, replace_role_permissions
from app.tasks.schemas import HelpRequestCreate, TaskCreate, TaskListView, TaskPreferenceUpdate
from app.tasks.service import (
    accept_help_request,
    add_assignment,
    create_help_request,
    create_task,
    get_task,
    list_tasks,
    resolve_help_request,
    transition_task_status,
    update_task_preference,
)

TEST_DATABASE_URL = os.getenv("MANAGEMENT_TASK_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="MANAGEMENT_TASK_TEST_DATABASE_URL is not configured",
    ),
]


@pytest_asyncio.fixture
async def database_session() -> AsyncSession:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
        )
        async with session_factory() as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


def principal(
    user: User,
    *,
    global_permissions: frozenset[str] = frozenset(),
    department_permissions: dict[int, frozenset[str]] | None = None,
) -> Principal:
    return Principal(
        user=user,
        session=SimpleNamespace(),
        authorization=AuthorizationContext(
            user_id=user.id,
            primary_department_id=user.department_id,
            global_permissions=global_permissions,
            department_permissions=department_permissions or {},
        ),
    )


async def seed_people(
    session: AsyncSession,
) -> tuple[Department, User, User, User]:
    department = Department(name="Integration Engineering")
    session.add(department)
    await session.flush()
    manager = User(
        name="Integration Manager",
        email="integration-manager@example.com",
        department_id=department.id,
    )
    employee = User(
        name="Integration Employee",
        email="integration-employee@example.com",
        department_id=department.id,
    )
    outsider = User(
        name="Integration Outsider",
        email="integration-outsider@example.com",
        department_id=department.id,
    )
    session.add_all([manager, employee, outsider])
    await session.flush()
    return department, manager, employee, outsider


def manager_permissions() -> frozenset[str]:
    return frozenset(
        {
            PermissionCode.TASKS_CREATE_ANY,
            PermissionCode.TASKS_ASSIGN_ANY,
            PermissionCode.TASKS_VIEW_ALL,
            PermissionCode.TASKS_MANAGE_ALL,
        }
    )


@pytest.mark.asyncio
async def test_private_task_visibility_and_status_workflow(
    database_session: AsyncSession,
) -> None:
    department, manager, employee, outsider = await seed_people(database_session)
    manager_principal = principal(manager, global_permissions=manager_permissions())
    employee_principal = principal(employee)
    outsider_principal = principal(outsider)

    created = await create_task(
        database_session,
        TaskCreate(
            title="Private infrastructure task",
            visibility=TaskVisibility.PRIVATE,
            department_id=department.id,
            assignee_ids={employee.id},
        ),
        manager_principal,
    )
    database_session.expunge_all()

    assigned_view = await get_task(database_session, created.id, employee_principal)
    assert assigned_view.id == created.id
    with pytest.raises(ResourceNotFoundError):
        await get_task(database_session, created.id, outsider_principal)

    database_session.expunge_all()
    with pytest.raises(AccessDeniedError):
        await transition_task_status(
            database_session,
            created.id,
            TaskStatus.CANCELLED,
            employee_principal,
        )

    outsider_items, outsider_total = await list_tasks(
        database_session,
        outsider_principal,
        limit=50,
        offset=0,
        view=TaskListView.ALL,
    )
    assert outsider_items == []
    assert outsider_total == 0

    for new_status in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW, TaskStatus.DONE):
        database_session.expunge_all()
        updated = await transition_task_status(
            database_session,
            created.id,
            new_status,
            employee_principal,
        )
        assert updated.status == new_status

    database_session.expunge_all()
    with pytest.raises(InvalidOperationError):
        await transition_task_status(
            database_session,
            created.id,
            TaskStatus.TODO,
            manager_principal,
        )


@pytest.mark.asyncio
async def test_personal_task_help_request_and_assignment_permissions(
    database_session: AsyncSession,
) -> None:
    department, manager, employee, outsider = await seed_people(database_session)
    employee_principal = principal(
        employee,
        global_permissions=frozenset({PermissionCode.TASKS_CREATE_SELF}),
    )
    manager_principal = principal(manager, global_permissions=manager_permissions())

    created = await create_task(
        database_session,
        TaskCreate(title="Need assistance", visibility=TaskVisibility.PRIVATE),
        employee_principal,
    )
    assert created.department_id == department.id
    assert [assignment.user.id for assignment in created.assignments] == [employee.id]

    database_session.expunge_all()
    with pytest.raises(AccessDeniedError):
        await add_assignment(
            database_session,
            created.id,
            outsider.id,
            employee_principal,
        )

    database_session.expunge_all()
    requested = await create_help_request(
        database_session,
        created.id,
        HelpRequestCreate(message="أحتاج شخصًا لمراجعة النتيجة"),
        employee_principal,
    )
    assert requested.help_request is not None
    assert requested.help_request.status.value == "open"

    database_session.expunge_all()
    accepted = await accept_help_request(database_session, created.id, manager_principal)
    assert accepted.help_request is not None
    assert accepted.help_request.accepted_by_id == manager.id
    assert manager.id in {assignment.user.id for assignment in accepted.assignments}

    database_session.expunge_all()
    resolved = await resolve_help_request(database_session, created.id, manager_principal)
    assert resolved.help_request is None


@pytest.mark.asyncio
async def test_hidden_and_pinned_views_are_personal_filters(
    database_session: AsyncSession,
) -> None:
    _department, _manager, employee, _outsider = await seed_people(database_session)
    employee_principal = principal(
        employee,
        global_permissions=frozenset({PermissionCode.TASKS_CREATE_SELF}),
    )
    created = await create_task(
        database_session,
        TaskCreate(title="Focus preference task"),
        employee_principal,
    )

    database_session.expunge_all()
    await update_task_preference(
        database_session,
        created.id,
        TaskPreferenceUpdate(is_hidden=True),
        employee_principal,
    )
    database_session.expunge_all()
    focus_items, focus_total = await list_tasks(
        database_session,
        employee_principal,
        limit=50,
        offset=0,
        view=TaskListView.FOCUS,
    )
    hidden_items, hidden_total = await list_tasks(
        database_session,
        employee_principal,
        limit=50,
        offset=0,
        view=TaskListView.HIDDEN,
    )
    assert focus_items == []
    assert focus_total == 0
    assert [item.id for item in hidden_items] == [created.id]
    assert hidden_total == 1

    database_session.expunge_all()
    await update_task_preference(
        database_session,
        created.id,
        TaskPreferenceUpdate(is_pinned=True),
        employee_principal,
    )
    database_session.expunge_all()
    pinned_items, pinned_total = await list_tasks(
        database_session,
        employee_principal,
        limit=50,
        offset=0,
        view=TaskListView.PINNED,
    )
    assert [item.id for item in pinned_items] == [created.id]
    assert pinned_total == 1


@pytest.mark.asyncio
async def test_custom_role_returns_its_effective_permissions(
    database_session: AsyncSession,
) -> None:
    permission_rows = list(
        await database_session.scalars(
            select(Permission).where(
                Permission.code.in_(
                    {
                        PermissionCode.TASKS_VIEW_DEPARTMENT,
                        PermissionCode.TASKS_MANAGE_DEPARTMENT,
                    }
                )
            )
        )
    )
    role = await create_role(
        database_session,
        RoleCreate(
            name="Integration Technical Reviewer",
            slug="integration-technical-reviewer",
        ),
    )
    role = await replace_role_permissions(
        database_session,
        role.id,
        {permission.id for permission in permission_rows},
    )

    response = RoleRead.model_validate(role)

    assert {permission.code for permission in response.permissions} == {
        PermissionCode.TASKS_VIEW_DEPARTMENT,
        PermissionCode.TASKS_MANAGE_DEPARTMENT,
    }
