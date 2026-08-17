"""Align task workflow and view-preference constraints.

Revision ID: 20260818_0003
Revises: 20260817_0002
Create Date: 2026-08-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260818_0003"
down_revision: str | None = "20260817_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("task_status", "tasks", type_="check")
    op.create_check_constraint(
        "task_status",
        "tasks",
        "status IN ('todo', 'in_progress', 'in_review', 'done', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_task_view_preferences_not_hidden_and_pinned",
        "task_view_preferences",
        "NOT (is_hidden AND is_pinned)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_task_view_preferences_not_hidden_and_pinned",
        "task_view_preferences",
        type_="check",
    )
    op.execute("UPDATE tasks SET status = 'in_progress' WHERE status = 'in_review'")
    op.drop_constraint("task_status", "tasks", type_="check")
    op.create_check_constraint(
        "task_status",
        "tasks",
        "status IN ('todo', 'in_progress', 'done', 'cancelled')",
    )
