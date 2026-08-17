from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceConflictError, ResourceNotFoundError
from app.departments.schemas import DepartmentCreate
from app.models.department import Department


async def create_department(session: AsyncSession, data: DepartmentCreate) -> Department:
    existing_id = await session.scalar(
        select(Department.id).where(func.lower(Department.name) == data.name.lower())
    )
    if existing_id is not None:
        raise ResourceConflictError("A department with this name already exists")

    department = Department(name=data.name)
    session.add(department)
    await session.flush()
    return department


async def get_active_department(session: AsyncSession, department_id: int) -> Department:
    department = await session.get(Department, department_id)
    if department is None or not department.is_active:
        raise ResourceNotFoundError("Active department not found")
    return department
