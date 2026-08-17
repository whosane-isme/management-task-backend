import pytest
from pydantic import ValidationError

from app.departments.schemas import DepartmentCreate
from app.roles.schemas import RoleCreate
from app.users.schemas import UserCreate


def test_user_input_is_normalized() -> None:
    user = UserCreate(
        name="  Ali   Hassan  ",
        email="ALI.HASSAN@EXAMPLE.COM",
        department_id=2,
    )

    assert user.name == "Ali Hassan"
    assert user.email == "ali.hassan@example.com"


def test_department_name_is_normalized() -> None:
    department = DepartmentCreate(name="  Human   Resources ")

    assert department.name == "Human Resources"


def test_role_slug_is_normalized() -> None:
    role = RoleCreate(name="Technical Lead", slug="  TECHNICAL-LEAD ")

    assert role.slug == "technical-lead"


def test_invalid_role_slug_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Role slug"):
        RoleCreate(name="Technical Lead", slug="technical lead!")
