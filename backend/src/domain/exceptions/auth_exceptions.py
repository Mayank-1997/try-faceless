"""IAM domain exceptions — authentication, authorization, and identity errors.

These exceptions extend the existing ``AppError`` hierarchy from
``src.core.exceptions``. Exceptions already defined in core (AuthError,
InvalidCredentialsError, TokenExpiredError, PermissionDeniedError) are
imported and re-exported here for convenience. New IAM-specific
exceptions are defined below.
"""

from __future__ import annotations

from src.core.exceptions import (
    AppError,
    AuthError,
    DomainError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
)

# Re-export core exceptions for convenience
__all__ = [
    "AuthError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "PermissionDeniedError",
    # New IAM exceptions
    "TokenInvalidError",
    "TokenRevokedError",
    "TokenError",
    "RefreshTokenError",
    "UserNotActiveError",
    "EmailNotVerifiedError",
    "AuthenticationRequiredError",
    "AuthorizationError",
    "RoleRequiredError",
    "OwnershipRequiredError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "PasswordError",
    "WeakPasswordError",
    "PasswordMismatchError",
    "ApiKeyError",
    "ApiKeyNotFoundError",
    "ApiKeyInvalidError",
    "ApiKeyExpiredError",
    "TokenValidationError",
    "PasswordResetTokenError",
    "EmailVerificationTokenError",
    "SessionError",
    "SessionNotFoundError",
    "RoleNotFoundError",
    "PermissionNotFoundError",
    "SystemRoleCannotBeDeletedError",
]


# ---------------------------------------------------------------------------
# Token errors (extending core AuthError)
# ---------------------------------------------------------------------------
class TokenError(AuthError):
    """Base exception for JWT token errors."""

    code = "TOKEN_ERROR"


class TokenInvalidError(TokenError):
    """Raised when a JWT token is invalid or malformed."""

    code = "TOKEN_INVALID"

    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(detail)


class TokenRevokedError(TokenError):
    """Raised when a token has been revoked."""

    code = "TOKEN_REVOKED"

    def __init__(self, detail: str = "Token has been revoked") -> None:
        super().__init__(detail)


class RefreshTokenError(TokenError):
    """Raised when a refresh token is invalid, expired, or revoked."""

    code = "REFRESH_TOKEN_ERROR"

    def __init__(self, detail: str = "Refresh token is invalid, expired, or revoked") -> None:
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Authorization errors (new — not in core.exceptions)
# ---------------------------------------------------------------------------
class AuthorizationError(DomainError):
    """Base exception for authorization failures."""

    code = "AUTHORIZATION_ERROR"
    status_code = 403


class PermissionDeniedError(AuthorizationError):
    """Raised when a user lacks a required permission.

    This overrides the core ``PermissionDeniedError`` with an IAM-specific
    signature that takes a single permission name.
    """

    code = "PERMISSION_DENIED"

    def __init__(self, permission: str) -> None:
        super().__init__(f"Permission denied: '{permission}' is required")


class RoleRequiredError(AuthorizationError):
    """Raised when a user lacks a required role."""

    code = "ROLE_REQUIRED"

    def __init__(self, role: str) -> None:
        super().__init__(f"Role '{role}' is required to perform this action")


class OwnershipRequiredError(AuthorizationError):
    """Raised when a user tries to access a resource they don't own."""

    code = "OWNERSHIP_REQUIRED"

    def __init__(self, resource_type: str, resource_id: str) -> None:
        super().__init__(
            f"You do not own {resource_type} '{resource_id}'"
        )


# ---------------------------------------------------------------------------
# Authentication errors (new — not in core.exceptions)
# ---------------------------------------------------------------------------
class UserNotActiveError(AuthError):
    """Raised when a non-active user attempts to authenticate."""

    code = "USER_NOT_ACTIVE"

    def __init__(self, status: str) -> None:
        super().__init__(
            f"Account is not active (status: {status}). Please contact an administrator."
        )


class EmailNotVerifiedError(AuthError):
    """Raised when an unverified email attempts to access protected resources."""

    code = "EMAIL_NOT_VERIFIED"
    status_code = 403

    def __init__(self, email: str) -> None:
        super().__init__(f"Email '{email}' has not been verified")


class AuthenticationRequiredError(AuthError):
    """Raised when no authenticated user is found for a protected resource."""

    code = "AUTHENTICATION_REQUIRED"

    def __init__(self) -> None:
        super().__init__("Authentication is required to access this resource")


# ---------------------------------------------------------------------------
# User management errors
# ---------------------------------------------------------------------------
class UserAlreadyExistsError(DomainError):
    """Raised when attempting to register a duplicate user."""

    code = "USER_ALREADY_EXISTS"
    status_code = 409

    def __init__(self, identifier: str) -> None:
        super().__init__(f"User with identifier '{identifier}' already exists")


class UserNotFoundError(DomainError):
    """Raised when a user cannot be found."""

    code = "USER_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"User '{identifier}' not found")


class PasswordError(DomainError):
    """Base exception for password-related errors."""

    code = "PASSWORD_ERROR"
    status_code = 422


class WeakPasswordError(PasswordError):
    """Raised when a password does not meet strength requirements."""

    code = "WEAK_PASSWORD"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Password does not meet strength requirements: {detail}")


class PasswordMismatchError(PasswordError):
    """Raised when current password doesn't match during change."""

    code = "PASSWORD_MISMATCH"

    def __init__(self) -> None:
        super().__init__("Current password is incorrect")


# ---------------------------------------------------------------------------
# API Key errors
# ---------------------------------------------------------------------------
class ApiKeyError(DomainError):
    """Base exception for API key errors."""

    code = "API_KEY_ERROR"
    status_code = 400


class ApiKeyNotFoundError(ApiKeyError):
    """Raised when an API key cannot be found."""

    code = "API_KEY_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "API key not found") -> None:
        super().__init__(message)


class ApiKeyInvalidError(ApiKeyError):
    """Raised when an API key is invalid or revoked."""

    code = "API_KEY_INVALID"
    status_code = 401

    def __init__(self, message: str = "Invalid or revoked API key") -> None:
        super().__init__(message)


class ApiKeyExpiredError(ApiKeyError):
    """Raised when an API key has expired."""

    code = "API_KEY_EXPIRED"
    status_code = 401

    def __init__(self, message: str = "API key has expired") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Token validation errors (password reset, email verification)
# ---------------------------------------------------------------------------
class TokenValidationError(DomainError):
    """Base exception for token validation errors (reset, verification)."""

    code = "TOKEN_VALIDATION_ERROR"
    status_code = 400


class PasswordResetTokenError(TokenValidationError):
    """Raised when a password reset token is invalid or expired."""

    code = "PASSWORD_RESET_TOKEN_INVALID"

    def __init__(self, detail: str = "Password reset token is invalid or expired") -> None:
        super().__init__(detail)


class EmailVerificationTokenError(TokenValidationError):
    """Raised when an email verification token is invalid or expired."""

    code = "EMAIL_VERIFICATION_TOKEN_INVALID"

    def __init__(self, detail: str = "Email verification token is invalid or expired") -> None:
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Session errors
# ---------------------------------------------------------------------------
class SessionError(DomainError):
    """Base exception for session errors."""

    code = "SESSION_ERROR"
    status_code = 400


class SessionNotFoundError(SessionError):
    """Raised when a session cannot be found."""

    code = "SESSION_NOT_FOUND"
    status_code = 404

    def __init__(self, message: str = "Session not found") -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Role / Permission errors
# ---------------------------------------------------------------------------
class RoleNotFoundError(DomainError):
    """Raised when a role cannot be found."""

    code = "ROLE_NOT_FOUND"
    status_code = 404

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Role '{identifier}' not found")


class PermissionNotFoundError(DomainError):
    """Raised when a permission cannot be found."""

    code = "PERMISSION_NOT_FOUND"
    status_code = 404

    def __init__(self, name: str) -> None:
        super().__init__(f"Permission '{name}' not found")


class SystemRoleCannotBeDeletedError(DomainError):
    """Raised when attempting to delete a system-defined role."""

    code = "SYSTEM_ROLE_CANNOT_BE_DELETED"
    status_code = 403

    def __init__(self, role_name: str) -> None:
        super().__init__(f"System role '{role_name}' cannot be deleted")
