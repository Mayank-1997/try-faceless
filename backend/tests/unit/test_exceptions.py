"""Unit tests for the exception hierarchy."""

from __future__ import annotations

import pytest

from src.core.exceptions import (
    AgentExecutionError,
    AgentValidationError,
    AIProviderError,
    AIProviderTimeoutError,
    AppError,
    AuthError,
    BusinessRuleViolationError,
    ConfigurationError,
    DatabaseError,
    DomainError,
    EntityNotFoundError,
    EntityAlreadyExistsError,
    InfrastructureError,
    InsufficientCreditsError,
    InvalidCredentialsError,
    InvalidStateTransitionError,
    InvalidTokenError,
    PermissionDeniedError,
    QualityCheckError,
    RenderingError,
    TokenExpiredError,
    ValidationError,
)


class TestAppError:
    """Tests for the root exception class."""

    def test_default_code_and_status(self) -> None:
        err = AppError("something went wrong")
        assert err.code == "APP_ERROR"
        assert err.status_code == 500
        assert err.message == "something went wrong"

    def test_custom_code_and_status(self) -> None:
        err = AppError("custom", code="CUSTOM", status_code=418)
        assert err.code == "CUSTOM"
        assert err.status_code == 418

    def test_str_representation(self) -> None:
        err = AppError("test error", code="TEST")
        assert str(err) == "[TEST] test error"


class TestDomainErrors:
    """Tests for domain-layer exceptions."""

    def test_entity_not_found(self) -> None:
        err = EntityNotFoundError("Project", "abc-123")
        assert err.code == "ENTITY_NOT_FOUND"
        assert err.status_code == 404
        assert "Project" in err.message
        assert "abc-123" in err.message

    def test_entity_already_exists(self) -> None:
        err = EntityAlreadyExistsError("User", "test@example.com")
        assert err.code == "ENTITY_ALREADY_EXISTS"
        assert err.status_code == 409

    def test_business_rule_violation(self) -> None:
        err = BusinessRuleViolationError("max_scenes", "cannot exceed 100 scenes")
        assert err.code == "BUSINESS_RULE_VIOLATION"
        assert err.status_code == 422

    def test_invalid_state_transition(self) -> None:
        err = InvalidStateTransitionError("Project", "draft", "completed")
        assert err.code == "INVALID_STATE_TRANSITION"
        assert err.status_code == 409
        assert "draft" in err.message
        assert "completed" in err.message

    def test_insufficient_credits(self) -> None:
        err = InsufficientCreditsError(required=10.0, available=5.0)
        assert err.code == "INSUFFICIENT_CREDITS"
        assert err.status_code == 402

    def test_agent_execution_error(self) -> None:
        err = AgentExecutionError("research", "API timeout")
        assert err.code == "AGENT_EXECUTION_ERROR"
        assert "research" in err.message

    def test_agent_validation_error(self) -> None:
        err = AgentValidationError("script_writer", "input", "missing topic field")
        assert err.code == "AGENT_VALIDATION_ERROR"
        assert err.status_code == 422

    def test_quality_check_error(self) -> None:
        err = QualityCheckError("research", 0.5, 0.7)
        assert err.code == "QUALITY_CHECK_FAILED"
        assert "0.50" in err.message
        assert "0.70" in err.message


class TestInfrastructureErrors:
    """Tests for infrastructure-layer exceptions."""

    def test_database_error(self) -> None:
        err = DatabaseError("connection refused")
        assert err.code == "DATABASE_ERROR"
        assert err.status_code == 500

    def test_ai_provider_error(self) -> None:
        err = AIProviderError("gemini", "rate limited")
        assert err.code == "AI_PROVIDER_ERROR"
        assert err.status_code == 502
        assert "gemini" in err.message

    def test_ai_provider_timeout_error(self) -> None:
        err = AIProviderTimeoutError("veo", 300)
        assert err.code == "AI_PROVIDER_TIMEOUT"
        assert err.status_code == 504
        assert "300" in err.message


class TestAuthErrors:
    """Tests for authentication/authorization exceptions."""

    def test_invalid_credentials(self) -> None:
        err = InvalidCredentialsError()
        assert err.code == "INVALID_CREDENTIALS"
        assert err.status_code == 401

    def test_token_expired(self) -> None:
        err = TokenExpiredError()
        assert err.code == "TOKEN_EXPIRED"
        assert err.status_code == 401

    def test_invalid_token(self) -> None:
        err = InvalidTokenError("malformed JWT")
        assert err.code == "INVALID_TOKEN"
        assert err.status_code == 401

    def test_permission_denied(self) -> None:
        err = PermissionDeniedError("delete", "project")
        assert err.code == "PERMISSION_DENIED"
        assert err.status_code == 403


class TestValidationError:
    """Tests for application-layer validation exceptions."""

    def test_validation_error(self) -> None:
        err = ValidationError("email", "invalid format")
        assert err.code == "VALIDATION_ERROR"
        assert err.status_code == 422
        assert err.field == "email"


class TestExceptionInheritance:
    """Verify the exception inheritance hierarchy."""

    def test_domain_errors_inherit_domain_error(self) -> None:
        assert issubclass(EntityNotFoundError, DomainError)
        assert issubclass(BusinessRuleViolationError, DomainError)
        assert issubclass(AgentExecutionError, DomainError)

    def test_infrastructure_errors_inherit_infrastructure_error(self) -> None:
        assert issubclass(DatabaseError, InfrastructureError)
        assert issubclass(AIProviderError, InfrastructureError)

    def test_all_inherit_app_error(self) -> None:
        assert issubclass(DomainError, AppError)
        assert issubclass(InfrastructureError, AppError)
        assert issubclass(AuthError, AppError)
        assert issubclass(ValidationError, AppError)

    def test_app_error_inherits_exception(self) -> None:
        assert issubclass(AppError, Exception)
