from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.models.department import Department
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    user_id: int
    primary_department_id: int | None
    global_permissions: frozenset[str]
    department_permissions: dict[int, frozenset[str]]

    def has_permission(self, code: str, *, department_id: int | None = None) -> bool:
        if code in self.global_permissions:
            return True
        if department_id is None:
            return False
        return code in self.department_permissions.get(department_id, frozenset())

    def departments_with(self, code: str) -> frozenset[int]:
        return frozenset(
            department_id
            for department_id, permissions in self.department_permissions.items()
            if code in permissions
        )


async def load_authorization_context(
    session: AsyncSession,
    user_id: int,
) -> AuthorizationContext:
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise ResourceNotFoundError("Active user not found")

    statement = (
        select(Permission.code, UserRoleAssignment.department_id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
        .outerjoin(Department, Department.id == UserRoleAssignment.department_id)
        .where(
            UserRoleAssignment.user_id == user_id,
            Role.is_active.is_(True),
            or_(
                UserRoleAssignment.department_id.is_(None),
                Department.is_active.is_(True),
            ),
        )
    )
    rows = (await session.execute(statement)).all()

    global_permissions: set[str] = set()
    scoped_permissions: dict[int, set[str]] = {}
    for permission_code, department_id in rows:
        if department_id is None:
            global_permissions.add(permission_code)
        else:
            scoped_permissions.setdefault(department_id, set()).add(permission_code)

    return AuthorizationContext(
        user_id=user.id,
        primary_department_id=user.department_id,
        global_permissions=frozenset(global_permissions),
        department_permissions={
            department_id: frozenset(permissions)
            for department_id, permissions in scoped_permissions.items()
        },
    )
