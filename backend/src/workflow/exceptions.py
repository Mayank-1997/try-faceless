"""Workflow-specific exceptions for the orchestration framework.

These exceptions extend the base ``AppError`` hierarchy and provide
fine-grained error categories for workflow execution, node failures,
checkpointing, and registry operations.
"""

from __future__ import annotations

from src.core.exceptions import AppError, DomainError, InfrastructureError


# ---------------------------------------------------------------------------
# Workflow execution errors
# ---------------------------------------------------------------------------
class WorkflowExecutionError(DomainError):
    """Raised when a workflow execution encounters an unrecoverable error."""

    code = "WORKFLOW_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, workflow_id: str, detail: str) -> None:
        super().__init__(f"Workflow '{workflow_id}' execution failed: {detail}")
        self.workflow_id = workflow_id


class WorkflowCancelledError(DomainError):
    """Raised when a workflow execution is cancelled."""

    code = "WORKFLOW_CANCELLED"
    status_code = 499

    def __init__(self, workflow_id: str, reason: str = "Cancelled by request") -> None:
        super().__init__(f"Workflow '{workflow_id}' cancelled: {reason}")
        self.workflow_id = workflow_id


class WorkflowTimeoutError(DomainError):
    """Raised when a workflow execution exceeds its timeout."""

    code = "WORKFLOW_TIMEOUT"
    status_code = 504

    def __init__(self, workflow_id: str, timeout_seconds: int) -> None:
        super().__init__(
            f"Workflow '{workflow_id}' timed out after {timeout_seconds}s"
        )
        self.workflow_id = workflow_id


class WorkflowPausedError(DomainError):
    """Raised when a workflow execution is paused."""

    code = "WORKFLOW_PAUSED"
    status_code = 200

    def __init__(self, workflow_id: str, checkpoint_ref: str) -> None:
        super().__init__(
            f"Workflow '{workflow_id}' paused at checkpoint '{checkpoint_ref}'"
        )
        self.workflow_id = workflow_id
        self.checkpoint_ref = checkpoint_ref


# ---------------------------------------------------------------------------
# Node errors
# ---------------------------------------------------------------------------
class NodeExecutionError(DomainError):
    """Raised when a workflow node fails to execute."""

    code = "NODE_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, node_name: str, detail: str) -> None:
        super().__init__(f"Node '{node_name}' execution failed: {detail}")
        self.node_name = node_name


class NodeValidationError(DomainError):
    """Raised when node input or output validation fails."""

    code = "NODE_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, node_name: str, validation_type: str, detail: str) -> None:
        super().__init__(
            f"Node '{node_name}' {validation_type} validation failed: {detail}"
        )
        self.node_name = node_name


class NodeRetryExhaustedError(DomainError):
    """Raised when a node has exhausted all retry attempts."""

    code = "NODE_RETRY_EXHAUSTED"
    status_code = 503

    def __init__(self, node_name: str, attempts: int, last_error: str) -> None:
        super().__init__(
            f"Node '{node_name}' exhausted {attempts} retry attempts. Last error: {last_error}"
        )
        self.node_name = node_name
        self.attempts = attempts


# ---------------------------------------------------------------------------
# Checkpoint errors
# ---------------------------------------------------------------------------
class CheckpointError(InfrastructureError):
    """Raised when checkpoint save/restore fails."""

    code = "CHECKPOINT_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Checkpoint error: {detail}")


class CheckpointNotFoundError(InfrastructureError):
    """Raised when a checkpoint cannot be found."""

    code = "CHECKPOINT_NOT_FOUND"
    status_code = 404

    def __init__(self, checkpoint_ref: str) -> None:
        super().__init__(f"Checkpoint '{checkpoint_ref}' not found")


# ---------------------------------------------------------------------------
# Registry errors
# ---------------------------------------------------------------------------
class WorkflowNotFoundError(DomainError):
    """Raised when a requested workflow is not registered."""

    code = "WORKFLOW_NOT_FOUND"
    status_code = 404

    def __init__(self, workflow_name: str, version: str | None = None) -> None:
        version_str = f" version {version}" if version else ""
        super().__init__(
            f"Workflow '{workflow_name}'{version_str} not found in registry"
        )
        self.workflow_name = workflow_name


class WorkflowAlreadyRegisteredError(DomainError):
    """Raised when attempting to register a duplicate workflow."""

    code = "WORKFLOW_ALREADY_REGISTERED"
    status_code = 409

    def __init__(self, workflow_name: str, version: str) -> None:
        super().__init__(
            f"Workflow '{workflow_name}' version '{version}' already registered"
        )
        self.workflow_name = workflow_name


# ---------------------------------------------------------------------------
# Error classification helpers
# ---------------------------------------------------------------------------
class ErrorSeverity(str):
    """Error severity levels for workflow error handling."""

    RECOVERABLE = "recoverable"
    FATAL = "fatal"
    RETRYABLE = "retryable"
    VALIDATION = "validation"
    PROVIDER = "provider"


def classify_error(error: Exception) -> str:
    """Classify an error for workflow retry logic.

    Args:
        error: The exception to classify.

    Returns:
        One of ``ErrorSeverity`` values indicating how the workflow
        should handle the error.
    """
    from src.core.exceptions import (
        AIProviderError,
        AIProviderTimeoutError,
        AgentValidationError,
        InfrastructureError,
        ProviderException,
        ValidationError,
    )

    if isinstance(error, (AgentValidationError, ValidationError, NodeValidationError)):
        return ErrorSeverity.VALIDATION
    if isinstance(error, (AIProviderError, AIProviderTimeoutError, ProviderException)):
        return ErrorSeverity.PROVIDER
    if isinstance(error, InfrastructureError):
        return ErrorSeverity.RETRYABLE
    if isinstance(error, (WorkflowCancelledError, WorkflowTimeoutError)):
        return ErrorSeverity.FATAL
    if isinstance(error, (NodeExecutionError,)):
        return ErrorSeverity.RETRYABLE
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return ErrorSeverity.RETRYABLE
    return ErrorSeverity.FATAL
