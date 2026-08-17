from collections.abc import Collection

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidOperationError, ResourceConflictError, ResourceNotFoundError
from app.core.permission_codes import PermissionCode
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.roles.schemas import RoleCreate

SYSTEM_ROLE_REQUIRED_PERMISSIONS: dict[str, frozenset[str]] = {
    "organization-manager": frozenset(
        {
            PermissionCode.TASKS_VIEW_ALL,
            PermissionCode.TASKS_MANAGE_ALL,
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
    role = await session.get(Role, role_id)
    if role is None or not role.is_active:
        raise ResourceNotFoundError("Active role not found")

    result = await session.execute(select(Permission).where(Permission.id.in_(permission_ids)))
    permissions = list(result.scalars())
    if {permission.id for permission in permissions} != permission_ids:
        raise ResourceNotFoundError("One or more permissions do not exist")

    validate_role_permission_codes(role.slug, {permission.code for permission in permissions})
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    session.add_all(
        RolePermission(role_id=role.id, permission_id=permission_id)
        for permission_id in permission_ids
    )
    await session.flush()
    return role
