from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidOperationError
from app.users.bootstrap import ensure_first_manager
from app.users.schemas import UserCreate


def manager_data() -> UserCreate:
    return UserCreate(name="First Manager", email="manager@example.com")


@pytest.mark.asyncio
async def test_bootstrap_creates_first_manager() -> None:
    session = AsyncMock(spec=AsyncSession)
    role = SimpleNamespace(id=1)
    session.scalar.side_effect = [role, None, None]

    result = await ensure_first_manager(session, manager_data())

    assert result.created_user
    assert result.assigned_role
    assert session.add.call_count == 2
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_for_same_manager() -> None:
    session = AsyncMock(spec=AsyncSession)
    role = SimpleNamespace(id=1)
    user = SimpleNamespace(id=7, is_active=True)
    assignment = SimpleNamespace(id=9)
    session.scalar.side_effect = [role, user, assignment]

    result = await ensure_first_manager(session, manager_data())

    assert not result.created_user
    assert not result.assigned_role
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_refuses_second_active_manager() -> None:
    session = AsyncMock(spec=AsyncSession)
    role = SimpleNamespace(id=1)
    session.scalar.side_effect = [role, None, 42]

    with pytest.raises(InvalidOperationError, match="already exists"):
        await ensure_first_manager(session, manager_data())

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_refuses_inactive_target_user() -> None:
    session = AsyncMock(spec=AsyncSession)
    role = SimpleNamespace(id=1)
    inactive_user = SimpleNamespace(id=7, is_active=False)
    session.scalar.side_effect = [role, inactive_user]

    with pytest.raises(InvalidOperationError, match="inactive"):
        await ensure_first_manager(session, manager_data())

    session.add.assert_not_called()
