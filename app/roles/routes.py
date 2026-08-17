from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.pagination import PaginationParams
from app.auth.dependencies import Principal, require_csrf_permissions, require_permissions
from app.core.permission_codes import PermissionCode
from app.db.session import DatabaseSession
from app.roles.schemas import (
    PermissionRead,
    RoleCreate,
    RolePage,
    RolePermissionReplace,
    RoleRead,
)
from app.roles.service import create_role, list_permissions, list_roles, replace_role_permissions

router = APIRouter(prefix="/roles", tags=["roles"])

CanReadRoles = Annotated[
    Principal,
    Depends(require_permissions(PermissionCode.ROLES_MANAGE)),
]
CanWriteRoles = Annotated[
    Principal,
    Depends(require_csrf_permissions(PermissionCode.ROLES_MANAGE)),
]


@router.get("")
async def get_roles(
    _principal: CanReadRoles,
    session: DatabaseSession,
    pagination: PaginationParams,
    include_inactive: Annotated[bool, Query()] = False,
) -> RolePage:
    items, total = await list_roles(
        session,
        limit=pagination.limit,
        offset=pagination.offset,
        include_inactive=include_inactive,
    )
    return RolePage(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/permissions")
async def get_permissions(
    _principal: CanReadRoles,
    session: DatabaseSession,
) -> list[PermissionRead]:
    permissions = await list_permissions(session)
    return [PermissionRead.model_validate(item) for item in permissions]


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_role(
    data: RoleCreate,
    _principal: CanWriteRoles,
    session: DatabaseSession,
) -> RoleRead:
    role = await create_role(session, data)
    await session.commit()
    return RoleRead.model_validate(role)


@router.put("/{role_id}/permissions")
async def put_role_permissions(
    role_id: int,
    data: RolePermissionReplace,
    _principal: CanWriteRoles,
    session: DatabaseSession,
) -> RoleRead:
    role = await replace_role_permissions(session, role_id, data.permission_ids)
    await session.commit()
    return RoleRead.model_validate(role)
