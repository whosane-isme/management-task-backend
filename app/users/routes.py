from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.pagination import PaginationParams
from app.auth.dependencies import Principal, require_csrf_permissions, require_permissions
from app.core.permission_codes import PermissionCode
from app.db.session import DatabaseSession
from app.users.schemas import (
    RoleAssignmentCreate,
    RoleAssignmentRead,
    UserCreate,
    UserPage,
    UserRead,
)
from app.users.service import (
    assign_role,
    create_user,
    deactivate_user_as_actor,
    list_users,
)

router = APIRouter(prefix="/users", tags=["users"])

CanReadUsers = Annotated[
    Principal,
    Depends(require_permissions(PermissionCode.USERS_MANAGE)),
]
CanWriteUsers = Annotated[
    Principal,
    Depends(require_csrf_permissions(PermissionCode.USERS_MANAGE)),
]
CanAssignRoles = Annotated[
    Principal,
    Depends(
        require_csrf_permissions(
            PermissionCode.USERS_MANAGE,
            PermissionCode.ROLES_MANAGE,
        )
    ),
]


@router.get("")
async def get_users(
    _principal: CanReadUsers,
    session: DatabaseSession,
    pagination: PaginationParams,
    include_inactive: Annotated[bool, Query()] = False,
) -> UserPage:
    items, total = await list_users(
        session,
        limit=pagination.limit,
        offset=pagination.offset,
        include_inactive=include_inactive,
    )
    return UserPage(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_user(
    data: UserCreate,
    principal: CanWriteUsers,
    session: DatabaseSession,
) -> UserRead:
    user = await create_user(session, data, created_by_id=principal.user.id)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/{user_id}/deactivate")
async def post_deactivate_user(
    user_id: int,
    principal: CanWriteUsers,
    session: DatabaseSession,
) -> UserRead:
    user = await deactivate_user_as_actor(
        session,
        user_id,
        actor_user_id=principal.user.id,
    )
    await session.commit()
    return UserRead.model_validate(user)


@router.post(
    "/{user_id}/role-assignments",
    status_code=status.HTTP_201_CREATED,
)
async def post_role_assignment(
    user_id: int,
    data: RoleAssignmentCreate,
    principal: CanAssignRoles,
    session: DatabaseSession,
) -> RoleAssignmentRead:
    assignment = await assign_role(
        session,
        user_id=user_id,
        role_id=data.role_id,
        department_id=data.department_id,
        assigned_by_id=principal.user.id,
    )
    await session.commit()
    return RoleAssignmentRead.model_validate(assignment)
