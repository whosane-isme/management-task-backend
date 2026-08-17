from __future__ import annotations

import argparse

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.event_loop import run_async
from app.db.session import create_database
from app.users.bootstrap import BootstrapManagerResult, ensure_first_manager
from app.users.schemas import UserCreate


async def bootstrap(data: UserCreate) -> BootstrapManagerResult:
    settings = get_settings()
    database = create_database(settings.database_url, echo=settings.database_echo)
    try:
        async with database.session_factory() as session:
            result = await ensure_first_manager(session, data)
            await session.commit()
            return result
    finally:
        await database.engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the first organization manager before the initial Google login."
    )
    parser.add_argument("--email", required=True, help="Exact email used by the Google account")
    parser.add_argument("--name", required=True, help="Manager display name")
    args = parser.parse_args()

    try:
        data = UserCreate(name=args.name, email=args.email)
    except ValidationError as exc:
        parser.error(str(exc))

    try:
        result = run_async(bootstrap(data))
    except DomainError as exc:
        parser.exit(1, f"Bootstrap refused: {exc}\n")
    except SQLAlchemyError:
        parser.exit(1, "Bootstrap failed: verify the database settings and migrations.\n")

    action = "created" if result.created_user else "found"
    role_action = "assigned" if result.assigned_role else "already assigned"
    print(f"Manager {action}; organization-manager role {role_action}.")


if __name__ == "__main__":
    main()
