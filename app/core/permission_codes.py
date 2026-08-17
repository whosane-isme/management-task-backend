from enum import StrEnum


class PermissionCode(StrEnum):
    TASKS_CREATE_SELF = "tasks.create_self"
    TASKS_CREATE_DEPARTMENT = "tasks.create_department"
    TASKS_CREATE_ANY = "tasks.create_any"
    TASKS_ASSIGN_DEPARTMENT = "tasks.assign_department"
    TASKS_ASSIGN_ANY = "tasks.assign_any"
    TASKS_VIEW_DEPARTMENT = "tasks.view_department"
    TASKS_VIEW_PRIVATE_DEPARTMENT = "tasks.view_private_department"
    TASKS_VIEW_ALL = "tasks.view_all"
    TASKS_MANAGE_DEPARTMENT = "tasks.manage_department"
    TASKS_MANAGE_ALL = "tasks.manage_all"
    TASK_PREFERENCES_MANAGE_OTHERS = "task_preferences.manage_others"
    USERS_MANAGE = "users.manage"
    DEPARTMENTS_MANAGE = "departments.manage"
    ROLES_MANAGE = "roles.manage"
