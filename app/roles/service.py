from collections.abc import Collection

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import InvalidOperationError, ResourceConflictError, ResourceNotFoundError
from app.core.permission_codes import PermissionCode
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.roles.schemas import RoleCreate

SYSTEM_ROLE_REQUIRED_PERMISSIONS: dict[str, frozenset[str]] = {
    "organization-manager": frozenset(
        {
            PermissionCode.TASKS_CREATE_ANY,
            PermissionCode.TASKS_ASSIGN_ANY,
            PermissionCode.TASKS_VIEW_ALL,
            PermissionCode.TASKS_MANAGE_ALL,
            PermissionCode.TASK_PREFERENCES_MANAGE_OTHERS,
            PermissionCode.USERS_MANAGE,
            PermissionCode.DEPARTMENTS_MANAGE,
            PermissionCode.ROLES_MANAGE,
        }
    )
}


def validate_role_permission_codes(role_slug: str, permission_codes: Collection[str]) -> None:
    required = SYSTEM_ROLE_REQUIRED_PERMISSIONS.get(role_slug, frozenset())
    missing = required.difference(permission_codes)
    if missing:
        missing_codes = ", ".join(sorted(missing))
        raise InvalidOperationError(
            f"System role '{role_slug}' must retain permissions: {missing_codes}"
        )


async def create_role(session: AsyncSession, data: RoleCreate) -> Role:
    existing_id = await session.scalar(
        select(Role.id).where(
            (func.lower(Role.name) == data.name.lower()) | (Role.slug == data.slug)
        )
    )
    if existing_id is not None:
        raise ResourceConflictError("A role with this name or slug already exists")

    role = Role(
        name=data.name,
        slug=data.slug,
        description=data.description,
        display_order=data.display_order,
        is_system=False,
    )
    session.add(role)
    await session.flush()
    return role


async def replace_role_permissions(
    session: AsyncSession,
    role_id: int,
    permission_ids: set[int],
) -> Role:
    role = await session.scalar(
        select(Role)
        .where(Role.id == role_id)
        .options(selectinload(Role.permission_links).selectinload(RolePermission.permission))
    )
    if role is None or not role.is_active:
        raise ResourceNotFoundError("Active role not found")

    result = await session.execute(select(Permission).where(Permission.id.in_(permission_ids)))
    permissions = list(result.scalars())
    if {permission.id for permission in permissions} != permission_ids:
        raise ResourceNotFoundError("One or more permissions do not exist")

    validate_role_permission_codes(role.slug, {permission.code for permission in permissions})
    role.permission_links = [RolePermission(permission=permission) for permission in permissions]
    await session.flush()
    return role


async def list_roles(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    include_inactive: bool = False,
) -> tuple[list[Role], int]:
    filters = () if include_inactive else (Role.is_active.is_(True),)
    total = await session.scalar(select(func.count()).select_from(Role).where(*filters))
    result = await session.scalars(
        select(Role)
        .where(*filters)
        .options(selectinload(Role.permission_links).selectinload(RolePermission.permission))
        .order_by(Role.display_order, func.lower(Role.name), Role.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result), total or 0


async def list_permissions(session: AsyncSession) -> list[Permission]:
    result = await session.scalars(select(Permission).order_by(Permission.code))
    return list(result)
