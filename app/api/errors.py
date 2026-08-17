from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.errors import (
    AccessDeniedError,
    AuthenticationError,
    DomainError,
    InvalidOperationError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def domain_error_status(exc: DomainError) -> int:
    if isinstance(exc, ResourceNotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, (ResourceConflictError, InvalidOperationError)):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, AuthenticationError):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(exc, AccessDeniedError):
        return status.HTTP_403_FORBIDDEN
    return status.HTTP_400_BAD_REQUEST


async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=domain_error_status(exc),
        content={"detail": str(exc), "code": exc.code},
    )
