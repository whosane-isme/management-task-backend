from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.auth.routes import router as auth_router
from app.departments.routes import router as departments_router
from app.roles.routes import router as roles_router
from app.tasks.routes import preferences_router
from app.tasks.routes import router as tasks_router
from app.users.routes import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(departments_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(tasks_router)
api_router.include_router(preferences_router)
