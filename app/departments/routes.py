from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.pagination import PaginationParams
from app.auth.dependencies import Principal, require_csrf_permissions, require_permissions
from app.core.permission_codes import PermissionCode
from app.db.session import DatabaseSession
from app.departments.schemas import DepartmentCreate, DepartmentPage, DepartmentRead
from app.departments.service import create_department, list_departments

router = APIRouter(prefix="/departments", tags=["departments"])

CanReadDepartments = Annotated[
    Principal,
    Depends(require_permissions(PermissionCode.DEPARTMENTS_MANAGE)),
]
CanWriteDepartments = Annotated[
    Principal,
    Depends(require_csrf_permissions(PermissionCode.DEPARTMENTS_MANAGE)),
]


@router.get("")
async def get_departments(
    _principal: CanReadDepartments,
    session: DatabaseSession,
    pagination: PaginationParams,
    include_inactive: Annotated[bool, Query()] = False,
) -> DepartmentPage:
    items, total = await list_departments(
        session,
        limit=pagination.limit,
        offset=pagination.offset,
        include_inactive=include_inactive,
    )
    return DepartmentPage(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_department(
    data: DepartmentCreate,
    _principal: CanWriteDepartments,
    session: DatabaseSession,
) -> DepartmentRead:
    department = await create_department(session, data)
    await session.commit()
    return DepartmentRead.model_validate(department)
