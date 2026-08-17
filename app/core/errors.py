class DomainError(Exception):
    """Base error for expected business-rule failures."""

    code = "domain_error"


class ResourceNotFoundError(DomainError):
    code = "not_found"


class ResourceConflictError(DomainError):
    code = "conflict"


class InvalidOperationError(DomainError):
    code = "invalid_operation"


class AuthenticationError(DomainError):
    code = "unauthenticated"


class AccessDeniedError(DomainError):
    code = "forbidden"
