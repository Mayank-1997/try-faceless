"""Tests for IAM domain exceptions."""

from __future__ import annotations

import pytest

from src.core.exceptions import AppError
from src.domain.exceptions.auth_exceptions import (
    ApiKeyExpiredError,
    ApiKeyInvalidError,
    ApiKeyNotFoundError,
    AuthError,
    AuthenticationRequiredError,
    AuthorizationError,
    EmailNotVerifiedError,
    EmailVerificationTokenError,
    InvalidCredentialsError,
    OwnershipRequiredError,
    PasswordError,
    PasswordMismatchError,
    PasswordResetTokenError,
    PermissionDeniedError,
    RefreshTokenError,
    RoleNotFoundError,
    RoleRequiredError,
    SessionNotFoundError,
    SystemRoleCannotBeDeletedError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserNotActiveError,
    WeakPasswordError,
)


class TestAuthExceptions:
    def test_auth_error_inherits_app_error(self):
        exc = AuthError("test")
        assert isinstance(exc, AppError)
        assert exc.code == "AUTH_ERROR"
        assert exc.status_code == 401

    def test_invalid_credentials(self):
        exc = InvalidCredentialsError()
        assert exc.code == "INVALID_CREDENTIALS"
        assert exc.status_code == 401

    def test_user_not_active(self):
        exc = UserNotActiveError("locked")
        assert "locked" in str(exc)
        assert exc.status_code == 401

    def test_email_not_verified(self):
        exc = EmailNotVerifiedError("test@test.com")
        assert exc.code == "EMAIL_NOT_VERIFIED"
        assert exc.status_code == 403

    def test_token_expired(self):
        exc = TokenExpiredError()
        assert exc.code == "TOKEN_EXPIRED"

    def test_token_invalid(self):
        exc = TokenInvalidError("bad token")
        assert exc.code == "TOKEN_INVALID"

    def test_token_revoked(self):
        exc = TokenRevokedError()
        assert exc.code == "TOKEN_REVOKED"

    def test_authentication_required(self):
        exc = AuthenticationRequiredError()
        assert exc.code == "AUTHENTICATION_REQUIRED"


class TestAuthorizationExceptions:
    def test_permission_denied(self):
        exc = PermissionDeniedError("project.create")
        assert exc.code == "PERMISSION_DENIED"
        assert exc.status_code == 403
        assert "project.create" in str(exc)

    def test_role_required(self):
        exc = RoleRequiredError("admin")
        assert exc.code == "ROLE_REQUIRED"
        assert "admin" in str(exc)

    def test_ownership_required(self):
        exc = OwnershipRequiredError("project", "abc-123")
        assert exc.code == "OWNERSHIP_REQUIRED"
        assert "project" in str(exc)


class TestUserExceptions:
    def test_user_already_exists(self):
        exc = UserAlreadyExistsError("test@test.com")
        assert exc.code == "USER_ALREADY_EXISTS"
        assert exc.status_code == 409

    def test_user_not_found(self):
        exc = UserNotFoundError("abc")
        assert exc.code == "USER_NOT_FOUND"
        assert exc.status_code == 404


class TestPasswordExceptions:
    def test_weak_password(self):
        exc = WeakPasswordError("too short")
        assert exc.code == "WEAK_PASSWORD"

    def test_password_mismatch(self):
        exc = PasswordMismatchError()
        assert exc.code == "PASSWORD_MISMATCH"


class TestApiKeyExceptions:
    def test_api_key_not_found(self):
        exc = ApiKeyNotFoundError("API key not found")
        assert exc.status_code == 404

    def test_api_key_invalid(self):
        exc = ApiKeyInvalidError("Invalid API key")
        assert exc.status_code == 401

    def test_api_key_expired(self):
        exc = ApiKeyExpiredError("API key has expired")
        assert exc.status_code == 401


class TestTokenValidationExceptions:
    def test_password_reset_token_error(self):
        exc = PasswordResetTokenError()
        assert exc.code == "PASSWORD_RESET_TOKEN_INVALID"

    def test_email_verification_token_error(self):
        exc = EmailVerificationTokenError()
        assert exc.code == "EMAIL_VERIFICATION_TOKEN_INVALID"


class TestRoleExceptions:
    def test_role_not_found(self):
        exc = RoleNotFoundError("admin")
        assert exc.status_code == 404

    def test_system_role_cannot_be_deleted(self):
        exc = SystemRoleCannotBeDeletedError("super_admin")
        assert exc.status_code == 403
        assert "super_admin" in str(exc)
