"""Domain exception hierarchy — business-rule violations and infrastructure errors.

Design principles:
- ``DomainError`` is the base for all business-logic exceptions.
- ``InfrastructureError`` is the base for all infrastructure-level failures.
- Each exception carries a machine-readable ``code`` for API error mapping.
- Messages are human-readable and context-rich.
"""

from __future__ import annotations


class AppError(Exception):
    """Root exception for the entire application.

    All custom exceptions inherit from this class so that middleware can
    catch a single type and map it to a structured HTTP response.
    """

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ---------------------------------------------------------------------------
# Domain Errors (business logic)
# ---------------------------------------------------------------------------
class DomainError(AppError):
    """Base exception for domain-rule violations."""

    code = "DOMAIN_ERROR"
    status_code = 400


class EntityNotFoundError(DomainError):
    """Raised when a domain entity cannot be located."""

    code = "ENTITY_NOT_FOUND"
    status_code = 404

    def __init__(self, entity_name: str, entity_id: str | object | None = None) -> None:
        if entity_id is not None:
            super().__init__(f"{entity_name} with id '{entity_id}' not found")
        else:
            super().__init__(entity_name)


class EntityAlreadyExistsError(DomainError):
    """Raised when attempting to create a duplicate entity."""

    code = "ENTITY_ALREADY_EXISTS"
    status_code = 409

    def __init__(self, entity_name: str, identifier: str) -> None:
        super().__init__(f"{entity_name} with identifier '{identifier}' already exists")


class BusinessRuleViolationError(DomainError):
    """Raised when a business invariant is violated."""

    code = "BUSINESS_RULE_VIOLATION"
    status_code = 422

    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"Business rule '{rule}' violated: {detail}")


class InvalidStateTransitionError(DomainError):
    """Raised when an entity transitions to an invalid state."""

    code = "INVALID_STATE_TRANSITION"
    status_code = 409

    def __init__(self, entity: str, current_state: str, attempted_state: str) -> None:
        super().__init__(
            f"Cannot transition {entity} from '{current_state}' to '{attempted_state}'"
        )


class InsufficientCreditsError(DomainError):
    """Raised when a user lacks credits for an operation."""

    code = "INSUFFICIENT_CREDITS"
    status_code = 402

    def __init__(self, required: float, available: float) -> None:
        super().__init__(
            f"Insufficient credits: required {required}, available {available}"
        )


class WorkflowError(DomainError):
    """Base exception for workflow-related failures."""

    code = "WORKFLOW_ERROR"
    status_code = 500


class AgentExecutionError(DomainError):
    """Raised when an AI agent fails to execute successfully."""

    code = "AGENT_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, agent: str, detail: str) -> None:
        super().__init__(f"Agent '{agent}' execution failed: {detail}")


class AgentValidationError(DomainError):
    """Raised when agent input or output validation fails."""

    code = "AGENT_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, agent: str, validation_type: str, detail: str) -> None:
        super().__init__(f"Agent '{agent}' {validation_type} validation failed: {detail}")


class QualityCheckError(DomainError):
    """Raised when generated content fails quality thresholds."""

    code = "QUALITY_CHECK_FAILED"
    status_code = 422

    def __init__(self, agent: str, score: float, threshold: float) -> None:
        super().__init__(
            f"Agent '{agent}' quality score {score:.2f} below threshold {threshold:.2f}"
        )


class AssetDecisionError(DomainError):
    """Raised when the Asset Decision Agent cannot determine a valid strategy."""

    code = "ASSET_DECISION_ERROR"
    status_code = 422


class RenderingError(DomainError):
    """Raised when video rendering fails."""

    code = "RENDERING_ERROR"
    status_code = 500


class PublishingError(DomainError):
    """Raised when YouTube publishing fails."""

    code = "PUBLISHING_ERROR"
    status_code = 502


# ---------------------------------------------------------------------------
# Infrastructure Errors
# ---------------------------------------------------------------------------
class InfrastructureError(AppError):
    """Base exception for infrastructure-level failures."""

    code = "INFRASTRUCTURE_ERROR"
    status_code = 500


class DatabaseError(InfrastructureError):
    """Raised for database connection or query failures."""

    code = "DATABASE_ERROR"


class CacheError(InfrastructureError):
    """Raised for Redis/cache failures."""

    code = "CACHE_ERROR"


class TaskQueueError(InfrastructureError):
    """Raised for Celery/task queue failures."""

    code = "TASK_QUEUE_ERROR"


class AIProviderError(InfrastructureError):
    """Raised when an AI provider returns an error or unexpected response."""

    code = "AI_PROVIDER_ERROR"
    status_code = 502

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(f"AI provider '{provider}' error: {detail}")


class AIProviderTimeoutError(InfrastructureError):
    """Raised when an AI provider request times out."""

    code = "AI_PROVIDER_TIMEOUT"
    status_code = 504

    def __init__(self, provider: str, timeout_seconds: int) -> None:
        super().__init__(f"AI provider '{provider}' timed out after {timeout_seconds}s")


class StorageError(InfrastructureError):
    """Raised for file/storage backend failures."""

    code = "STORAGE_ERROR"


# ---------------------------------------------------------------------------
# Authentication / Authorization Errors
# ---------------------------------------------------------------------------
class AuthError(AppError):
    """Base exception for authentication failures."""

    code = "AUTH_ERROR"
    status_code = 401


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""

    code = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class TokenExpiredError(AuthError):
    """Raised when a JWT token has expired."""

    code = "TOKEN_EXPIRED"

    def __init__(self) -> None:
        super().__init__("Authentication token has expired")


class InvalidTokenError(AuthError):
    """Raised when a JWT token is malformed or invalid."""

    code = "INVALID_TOKEN"

    def __init__(self, detail: str = "Invalid authentication token") -> None:
        super().__init__(detail)


class PermissionDeniedError(AppError):
    """Raised when a user lacks permission for an action."""

    code = "PERMISSION_DENIED"
    status_code = 403

    def __init__(self, action: str, resource: str) -> None:
        super().__init__(f"Permission denied: cannot {action} on {resource}")


# ---------------------------------------------------------------------------
# Validation Errors
# ---------------------------------------------------------------------------
class ValidationError(AppError):
    """Raised when input validation fails at the application layer."""

    code = "VALIDATION_ERROR"
    status_code = 422

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(f"Validation error for field '{field}': {detail}")
        self.field = field


class ConfigurationError(AppError):
    """Raised when required configuration is missing or invalid."""

    code = "CONFIGURATION_ERROR"
    status_code = 500


# ---------------------------------------------------------------------------
# AI Gateway Errors
# ---------------------------------------------------------------------------
class GatewayError(AppError):
    """Base exception for gateway-layer failures.

    Gateways sit between agents and providers — they handle provider
    selection, fallback, retries, and response validation.  This
    exception is raised when the gateway itself fails (not the
    underlying provider, which raises ``ProviderException``).
    """

    code = "GATEWAY_ERROR"
    status_code = 502


class LLMGatewayError(GatewayError):
    """Raised when the LLM Gateway encounters an unrecoverable error."""

    code = "LLM_GATEWAY_ERROR"


class ImageGatewayError(GatewayError):
    """Raised when the Image Gateway encounters an unrecoverable error."""

    code = "IMAGE_GATEWAY_ERROR"


class VideoGatewayError(GatewayError):
    """Raised when the Video Gateway encounters an unrecoverable error."""

    code = "VIDEO_GATEWAY_ERROR"


class VoiceGatewayError(GatewayError):
    """Raised when the Voice Gateway encounters an unrecoverable error."""

    code = "VOICE_GATEWAY_ERROR"


class AllProvidersFailedError(GatewayError):
    """Raised when all configured providers for a gateway have failed."""

    code = "ALL_PROVIDERS_FAILED"
    status_code = 503

    def __init__(self, gateway: str, providers: list[str]) -> None:
        super().__init__(
            f"All providers failed for gateway '{gateway}': {', '.join(providers)}"
        )


# ---------------------------------------------------------------------------
# Provider Errors (distinct from AIProviderError — these are raised by
# provider implementations, not the infrastructure layer)
# ---------------------------------------------------------------------------
class ProviderException(InfrastructureError):
    """Base exception raised by a provider implementation.

    This is the exception that concrete providers (Gemini, Imagen, etc.)
    raise when they encounter errors.  The gateway catches these and
    decides whether to retry or fall back to another provider.
    """

    code = "PROVIDER_EXCEPTION"
    status_code = 502

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(f"Provider '{provider}' error: {detail}")
        self.provider = provider


class ProviderNotInitializedError(ProviderException):
    """Raised when a provider method is called before ``initialize()``."""

    code = "PROVIDER_NOT_INITIALIZED"

    def __init__(self, provider: str) -> None:
        super().__init__(provider, "provider not initialized")


class ProviderResponseParsingError(ProviderException):
    """Raised when a provider response cannot be parsed."""

    code = "PROVIDER_RESPONSE_PARSING_ERROR"
    status_code = 502

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(provider, f"response parsing failed: {detail}")


# ---------------------------------------------------------------------------
# Prompt Errors
# ---------------------------------------------------------------------------
class PromptException(AppError):
    """Base exception for prompt management errors."""

    code = "PROMPT_ERROR"
    status_code = 500


class PromptNotFoundError(PromptException):
    """Raised when a requested prompt template cannot be located."""

    code = "PROMPT_NOT_FOUND"
    status_code = 404

    def __init__(self, agent_type: str, prompt_name: str, version: str | None = None) -> None:
        version_str = f" version {version}" if version else ""
        super().__init__(
            f"Prompt '{prompt_name}' for agent '{agent_type}'{version_str} not found"
        )


class PromptValidationError(PromptException):
    """Raised when a prompt template fails validation."""

    code = "PROMPT_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, detail: str) -> None:
        super().__init__(f"Prompt validation error: {detail}")


class PromptRenderingError(PromptException):
    """Raised when prompt template rendering fails (missing variables, etc.)."""

    code = "PROMPT_RENDERING_ERROR"
    status_code = 422

    def __init__(self, template: str, missing_variables: list[str]) -> None:
        super().__init__(
            f"Prompt rendering failed for '{template}': missing variables {missing_variables}"
        )


# ---------------------------------------------------------------------------
# Registry Errors
# ---------------------------------------------------------------------------
class RegistryError(AppError):
    """Base exception for provider registry errors."""

    code = "REGISTRY_ERROR"
    status_code = 500


class ProviderNotRegisteredError(RegistryError):
    """Raised when a requested provider is not in the registry."""

    code = "PROVIDER_NOT_REGISTERED"
    status_code = 404

    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider '{provider}' is not registered")


class ProviderAlreadyRegisteredError(RegistryError):
    """Raised when attempting to register a duplicate provider."""

    code = "PROVIDER_ALREADY_REGISTERED"
    status_code = 409

    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider '{provider}' is already registered")


# ---------------------------------------------------------------------------
# Event Bus Errors
# ---------------------------------------------------------------------------
class EventBusError(AppError):
    """Base exception for event bus errors."""

    code = "EVENT_BUS_ERROR"
    status_code = 500


class EventPublishError(EventBusError):
    """Raised when publishing an event fails."""

    code = "EVENT_PUBLISH_ERROR"

    def __init__(self, event_type: str, detail: str) -> None:
        super().__init__(f"Failed to publish event '{event_type}': {detail}")


# ---------------------------------------------------------------------------
# Observability Errors
# ---------------------------------------------------------------------------
class ObservabilityError(AppError):
    """Base exception for observability/metrics errors."""

    code = "OBSERVABILITY_ERROR"
    status_code = 500


# ---------------------------------------------------------------------------
# Workflow State Errors
# ---------------------------------------------------------------------------
class WorkflowStateError(DomainError):
    """Raised when workflow state is invalid or corrupted."""

    code = "WORKFLOW_STATE_ERROR"
    status_code = 422
