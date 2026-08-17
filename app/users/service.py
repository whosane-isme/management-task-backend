from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidOperationError, ResourceConflictError, ResourceNotFoundError
from app.departments.service import get_active_department
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.users.schemas import UserCreate

DEFAULT_EMPLOYEE_ROLE_SLUG = "employee"


async def assign_role(
    session: AsyncSession,
    *,
    user_id: int,
    role_id: int,
    department_id: int | None,
    assigned_by_id: int | None,
) -> UserRoleAssignment:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise ResourceNotFoundError("Active user not found")

    role = await session.get(Role, role_id)
    if role is None or not role.is_active:
        raise ResourceNotFoundError("Active role not found")

    if department_id is not None:
        await get_active_department(session, department_id)

    scope_condition = (
        UserRoleAssignment.department_id.is_(None)
        if department_id is None
        else UserRoleAssignment.department_id == department_id
    )
    existing_id = await session.scalar(
        select(UserRoleAssignment.id).where(
            and_(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.role_id == role_id,
                scope_condition,
            )
        )
    )
    if existing_id is not None:
        raise ResourceConflictError("This role is already assigned in the requested scope")

    assignment = UserRoleAssignment(
        user_id=user_id,
        role_id=role_id,
        department_id=department_id,
        assigned_by_id=assigned_by_id,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def create_user(
    session: AsyncSession,
    data: UserCreate,
    *,
    created_by_id: int | None,
) -> User:
    existing_id = await session.scalar(
        select(User.id).where(func.lower(User.email) == str(data.email).lower())
    )
    if existing_id is not None:
        raise ResourceConflictError("A user with this email already exists")

    if data.department_id is not None:
        await get_active_department(session, data.department_id)

    employee_role_id = await session.scalar(
        select(Role.id).where(Role.slug == DEFAULT_EMPLOYEE_ROLE_SLUG, Role.is_active.is_(True))
    )
    if employee_role_id is None:
        raise ResourceNotFoundError("Default employee role is missing")

    user = User(
        name=data.name,
        email=str(data.email),
        department_id=data.department_id,
    )
    session.add(user)
    await session.flush()
    await assign_role(
        session,
        user_id=user.id,
        role_id=employee_role_id,
        department_id=None,
        assigned_by_id=created_by_id,
    )
    return user


async def deactivate_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise ResourceNotFoundError("Active user not found")

    user.is_active = False
    await session.flush()
    return user


async def deactivate_user_as_actor(
    session: AsyncSession,
    user_id: int,
    *,
    actor_user_id: int,
) -> User:
    if user_id == actor_user_id:
        raise InvalidOperationError("You cannot deactivate your own account")
    return await deactivate_user(session, user_id)


async def list_users(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    include_inactive: bool = False,
) -> tuple[list[User], int]:
    filters = () if include_inactive else (User.is_active.is_(True),)
    total = await session.scalar(select(func.count()).select_from(User).where(*filters))
    result = await session.scalars(
        select(User)
        .where(*filters)
        .order_by(func.lower(User.name), User.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result), total or 0
