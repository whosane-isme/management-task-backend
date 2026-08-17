from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidOperationError, ResourceNotFoundError
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.users.schemas import UserCreate

ORGANIZATION_MANAGER_ROLE_SLUG = "organization-manager"


@dataclass(frozen=True, slots=True)
class BootstrapManagerResult:
    user: User
    created_user: bool
    assigned_role: bool


async def ensure_first_manager(
    session: AsyncSession,
    data: UserCreate,
) -> BootstrapManagerResult:
    """Create the first active organization manager, or safely return the existing one."""
    role = await session.scalar(
        select(Role)
        .where(
            Role.slug == ORGANIZATION_MANAGER_ROLE_SLUG,
            Role.is_active.is_(True),
        )
        .with_for_update()
    )
    if role is None:
        raise ResourceNotFoundError("Organization manager role is missing")

    normalized_email = str(data.email).lower()
    user = await session.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is not None and not user.is_active:
        raise InvalidOperationError("The requested bootstrap user is inactive")

    if user is not None:
        assignment = await session.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == role.id,
                UserRoleAssignment.department_id.is_(None),
            )
        )
        if assignment is not None:
            return BootstrapManagerResult(
                user=user,
                created_user=False,
                assigned_role=False,
            )

    active_manager_id = await session.scalar(
        select(UserRoleAssignment.user_id)
        .join(User, User.id == UserRoleAssignment.user_id)
        .where(
            UserRoleAssignment.role_id == role.id,
            UserRoleAssignment.department_id.is_(None),
            User.is_active.is_(True),
        )
        .limit(1)
    )
    if active_manager_id is not None:
        raise InvalidOperationError(
            "An active organization manager already exists; use the authorized role workflow"
        )

    created_user = user is None
    if user is None:
        user = User(name=data.name, email=normalized_email)
        session.add(user)
        await session.flush()

    session.add(
        UserRoleAssignment(
            user_id=user.id,
            role_id=role.id,
            department_id=None,
            assigned_by_id=None,
        )
    )
    await session.flush()
    return BootstrapManagerResult(
        user=user,
        created_user=created_user,
        assigned_role=True,
    )
