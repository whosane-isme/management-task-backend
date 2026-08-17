"""Create the initial task management schema.

Revision ID: 20260817_0001
Revises:
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260817_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

auth_provider = sa.Enum(
    "google",
    "github",
    name="auth_provider",
    native_enum=False,
    create_constraint=True,
)
task_status = sa.Enum(
    "todo",
    "in_progress",
    "done",
    "cancelled",
    name="task_status",
    native_enum=False,
    create_constraint=True,
)
task_priority = sa.Enum(
    "low",
    "medium",
    "high",
    "urgent",
    name="task_priority",
    native_enum=False,
    create_constraint=True,
)
task_visibility = sa.Enum(
    "public",
    "department",
    "private",
    name="task_visibility",
    native_enum=False,
    create_constraint=True,
)
help_request_status = sa.Enum(
    "open",
    "accepted",
    "resolved",
    "cancelled",
    name="help_request_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_departments_name_ci",
        "departments",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("uq_roles_name_ci", "roles", [sa.text("lower(name)")], unique=True)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    permission_rows = [
        (1, "tasks.create_self", "Create a task assigned to oneself"),
        (2, "tasks.create_department", "Create tasks inside an assigned department"),
        (3, "tasks.create_any", "Create tasks anywhere in the organization"),
        (4, "tasks.assign_department", "Assign tasks inside an assigned department"),
        (5, "tasks.assign_any", "Assign tasks anywhere in the organization"),
        (6, "tasks.view_department", "View non-private department tasks"),
        (7, "tasks.view_private_department", "View private tasks in an assigned department"),
        (8, "tasks.view_all", "View every task in the organization"),
        (9, "tasks.manage_department", "Manage tasks in an assigned department"),
        (10, "tasks.manage_all", "Manage every task in the organization"),
        (11, "task_preferences.manage_others", "Organize another user's task view"),
        (12, "users.manage", "Manage users"),
        (13, "departments.manage", "Manage departments"),
        (14, "roles.manage", "Manage roles and permissions"),
    ]
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", sa.BigInteger()),
            sa.column("code", sa.String()),
            sa.column("description", sa.String()),
        ),
        [
            {"id": row_id, "code": code, "description": description}
            for row_id, code, description in permission_rows
        ],
    )
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("id", sa.BigInteger()),
            sa.column("name", sa.String()),
            sa.column("slug", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("display_order", sa.Integer()),
            sa.column("is_system", sa.Boolean()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {
                "id": 1,
                "name": "Organization Manager",
                "slug": "organization-manager",
                "description": "Full organization management and audit access",
                "display_order": 10,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": 2,
                "name": "Department Manager",
                "slug": "department-manager",
                "description": "Department-scoped task management",
                "display_order": 20,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": 3,
                "name": "Executive Assistant",
                "slug": "executive-assistant",
                "description": "Cross-team follow-up and task view organization",
                "display_order": 30,
                "is_system": True,
                "is_active": True,
            },
            {
                "id": 4,
                "name": "Employee",
                "slug": "employee",
                "description": "Creates and works on personal tasks",
                "display_order": 40,
                "is_system": True,
                "is_active": True,
            },
        ],
    )
    role_permission_rows = (
        [(1, permission_id) for permission_id in range(1, 15)]
        + [(2, permission_id) for permission_id in (1, 2, 4, 6, 7, 9)]
        + [(3, permission_id) for permission_id in (1, 5, 8, 11)]
        + [(4, 1)]
    )
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.BigInteger()),
            sa.column("permission_id", sa.BigInteger()),
        ),
        [
            {"role_id": role_id, "permission_id": permission_id}
            for role_id, permission_id in role_permission_rows
        ],
    )
    op.execute(
        "SELECT setval(pg_get_serial_sequence('permissions', 'id'), "
        "(SELECT MAX(id) FROM permissions))"
    )
    op.execute("SELECT setval(pg_get_serial_sequence('roles', 'id'), (SELECT MAX(id) FROM roles))")

    op.create_table(
        "users",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.create_index("uq_users_email_ci", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "user_role_assignments",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_by_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_role_assignments_assigned_by_id",
        "user_role_assignments",
        ["assigned_by_id"],
    )
    op.create_index(
        "ix_user_role_assignments_department_id",
        "user_role_assignments",
        ["department_id"],
    )
    op.create_index(
        "uq_user_role_assignments_global",
        "user_role_assignments",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where=sa.text("department_id IS NULL"),
    )
    op.create_index(
        "uq_user_role_assignments_department",
        "user_role_assignments",
        ["user_id", "role_id", "department_id"],
        unique=True,
        postgresql_where=sa.text("department_id IS NOT NULL"),
    )

    op.create_table(
        "auth_identities",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", auth_provider, nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=320), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "subject",
            name="uq_auth_identities_provider_subject",
        ),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, nullable=False),
        sa.Column("priority", task_priority, nullable=False),
        sa.Column("visibility", task_visibility, nullable=False),
        sa.Column("created_by_id", sa.BigInteger(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "visibility != 'department' OR department_id IS NOT NULL",
            name="ck_tasks_department_visibility",
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_created_by_id", "tasks", ["created_by_id"])
    op.create_index("ix_tasks_department_id", "tasks", ["department_id"])
    op.create_index("ix_tasks_status_due_at", "tasks", ["status", "due_at"])

    op.create_table(
        "task_view_preferences",
        sa.Column("viewer_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["viewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("viewer_id", "task_id"),
    )

    op.create_table(
        "task_help_requests",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("requested_by_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", help_request_status, nullable=False),
        sa.Column("accepted_by_id", sa.BigInteger(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status != 'accepted' OR accepted_by_id IS NOT NULL",
            name="ck_task_help_requests_accepted_by",
        ),
        sa.ForeignKeyConstraint(["accepted_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_help_requests_accepted_by_id",
        "task_help_requests",
        ["accepted_by_id"],
    )
    op.create_index(
        "ix_task_help_requests_requested_by_id",
        "task_help_requests",
        ["requested_by_id"],
    )
    op.create_index(
        "uq_task_help_requests_active",
        "task_help_requests",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'accepted')"),
    )

    op.create_table(
        "task_assignments",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_by_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignments_task_user"),
    )
    op.create_index(
        "ix_task_assignments_assigned_by_id",
        "task_assignments",
        ["assigned_by_id"],
    )
    op.create_index("ix_task_assignments_user_id", "task_assignments", ["user_id"])

    op.create_table(
        "task_comments",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_comments_task_created",
        "task_comments",
        ["task_id", "created_at"],
    )

    op.create_table(
        "activity_logs",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_activity_logs_task_created",
        "activity_logs",
        ["task_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_activity_logs_task_created", table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index("ix_task_comments_task_created", table_name="task_comments")
    op.drop_table("task_comments")
    op.drop_index("ix_task_assignments_user_id", table_name="task_assignments")
    op.drop_index("ix_task_assignments_assigned_by_id", table_name="task_assignments")
    op.drop_table("task_assignments")
    op.drop_index("uq_task_help_requests_active", table_name="task_help_requests")
    op.drop_index("ix_task_help_requests_requested_by_id", table_name="task_help_requests")
    op.drop_index("ix_task_help_requests_accepted_by_id", table_name="task_help_requests")
    op.drop_table("task_help_requests")
    op.drop_table("task_view_preferences")
    op.drop_index("ix_tasks_status_due_at", table_name="tasks")
    op.drop_index("ix_tasks_department_id", table_name="tasks")
    op.drop_index("ix_tasks_created_by_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_index(
        "uq_user_role_assignments_department",
        table_name="user_role_assignments",
    )
    op.drop_index("uq_user_role_assignments_global", table_name="user_role_assignments")
    op.drop_index(
        "ix_user_role_assignments_department_id",
        table_name="user_role_assignments",
    )
    op.drop_index(
        "ix_user_role_assignments_assigned_by_id",
        table_name="user_role_assignments",
    )
    op.drop_table("user_role_assignments")
    op.drop_index("uq_users_email_ci", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_index("uq_roles_name_ci", table_name="roles")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_index("uq_departments_name_ci", table_name="departments")
    op.drop_table("departments")
