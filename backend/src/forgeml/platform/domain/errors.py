class ForgeMLError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str, *, details: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class AuthenticationFailedError(ForgeMLError):
    status_code = 401
    code = "authentication_failed"


class PermissionDeniedError(ForgeMLError):
    status_code = 403
    code = "permission_denied"


class ResourceNotFoundError(ForgeMLError):
    status_code = 404
    code = "resource_not_found"


class ConflictError(ForgeMLError):
    status_code = 409
    code = "conflict"


class DomainValidationError(ForgeMLError):
    status_code = 422
    code = "validation_failed"
