"""Agent-specific exceptions for the AI Agent Framework.

Extends the existing ``AppError`` hierarchy with fine-grained
exceptions for agent execution, prompt handling, output validation,
quality evaluation, artifact management, and tool execution.
"""

from __future__ import annotations

from src.core.exceptions import DomainError, InfrastructureError


# ---------------------------------------------------------------------------
# Agent execution errors
# ---------------------------------------------------------------------------
class AgentExecutionError(DomainError):
    """Raised when an agent fails during execution."""

    code = "AGENT_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, agent_name: str, detail: str) -> None:
        super().__init__(f"Agent '{agent_name}' execution failed: {detail}")
        self.agent_name = agent_name


class AgentInitializationError(DomainError):
    """Raised when an agent cannot be initialized."""

    code = "AGENT_INITIALIZATION_ERROR"
    status_code = 500

    def __init__(self, agent_name: str, detail: str) -> None:
        super().__init__(f"Agent '{agent_name}' initialization failed: {detail}")
        self.agent_name = agent_name


class AgentTimeoutError(DomainError):
    """Raised when an agent exceeds its execution timeout."""

    code = "AGENT_TIMEOUT"
    status_code = 504

    def __init__(self, agent_name: str, timeout_seconds: int) -> None:
        super().__init__(
            f"Agent '{agent_name}' timed out after {timeout_seconds}s"
        )
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds


# ---------------------------------------------------------------------------
# Prompt errors
# ---------------------------------------------------------------------------
class PromptExecutionError(DomainError):
    """Raised when prompt execution fails."""

    code = "PROMPT_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, agent_name: str, detail: str) -> None:
        super().__init__(f"Prompt execution in '{agent_name}' failed: {detail}")
        self.agent_name = agent_name


class PromptRenderingError(DomainError):
    """Raised when a prompt template cannot be rendered."""

    code = "PROMPT_RENDERING_ERROR"
    status_code = 422

    def __init__(self, template_name: str, detail: str) -> None:
        super().__init__(f"Prompt template '{template_name}' rendering failed: {detail}")
        self.template_name = template_name


class PromptValidationError(DomainError):
    """Raised when prompt variables fail validation."""

    code = "PROMPT_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, template_name: str, missing: list[str]) -> None:
        super().__init__(
            f"Prompt template '{template_name}' missing variables: {', '.join(missing)}"
        )
        self.template_name = template_name
        self.missing_variables = missing


# ---------------------------------------------------------------------------
# Output validation errors
# ---------------------------------------------------------------------------
class OutputValidationError(DomainError):
    """Raised when agent output fails validation."""

    code = "OUTPUT_VALIDATION_ERROR"
    status_code = 422

    def __init__(self, agent_name: str, detail: str) -> None:
        super().__init__(f"Agent '{agent_name}' output validation failed: {detail}")
        self.agent_name = agent_name


class OutputRepairError(DomainError):
    """Raised when output repair attempts are exhausted."""

    code = "OUTPUT_REPAIR_ERROR"
    status_code = 422

    def __init__(self, agent_name: str, attempts: int) -> None:
        super().__init__(
            f"Agent '{agent_name}' output repair failed after {attempts} attempts"
        )
        self.agent_name = agent_name
        self.attempts = attempts


# ---------------------------------------------------------------------------
# Quality evaluation errors
# ---------------------------------------------------------------------------
class QualityEvaluationError(DomainError):
    """Raised when quality evaluation fails."""

    code = "QUALITY_EVALUATION_ERROR"
    status_code = 500

    def __init__(self, agent_name: str, detail: str) -> None:
        super().__init__(f"Quality evaluation for '{agent_name}' failed: {detail}")
        self.agent_name = agent_name


class QualityThresholdError(DomainError):
    """Raised when output quality is below the required threshold."""

    code = "QUALITY_THRESHOLD_NOT_MET"
    status_code = 422

    def __init__(self, agent_name: str, score: float, threshold: float) -> None:
        super().__init__(
            f"Agent '{agent_name}' quality score {score:.2f} below threshold {threshold:.2f}"
        )
        self.agent_name = agent_name
        self.score = score
        self.threshold = threshold


# ---------------------------------------------------------------------------
# Artifact errors
# ---------------------------------------------------------------------------
class ArtifactError(InfrastructureError):
    """Raised when artifact storage or retrieval fails."""

    code = "ARTIFACT_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Artifact error: {detail}")


class ArtifactNotFoundError(InfrastructureError):
    """Raised when an artifact cannot be found."""

    code = "ARTIFACT_NOT_FOUND"
    status_code = 404

    def __init__(self, artifact_id: str) -> None:
        super().__init__(f"Artifact '{artifact_id}' not found")
        self.artifact_id = artifact_id


# ---------------------------------------------------------------------------
# Tool errors
# ---------------------------------------------------------------------------
class ToolExecutionError(DomainError):
    """Raised when a tool execution fails."""

    code = "TOOL_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, tool_name: str, detail: str) -> None:
        super().__init__(f"Tool '{tool_name}' execution failed: {detail}")
        self.tool_name = tool_name


class ToolNotFoundError(DomainError):
    """Raised when a requested tool is not registered."""

    code = "TOOL_NOT_FOUND"
    status_code = 404

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found in registry")
        self.tool_name = tool_name


# ---------------------------------------------------------------------------
# Memory errors
# ---------------------------------------------------------------------------
class MemoryError(InfrastructureError):
    """Raised when agent memory operations fail."""

    code = "MEMORY_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(f"Agent memory error: {detail}")


# ---------------------------------------------------------------------------
# Registry errors
# ---------------------------------------------------------------------------
class AgentNotFoundError(DomainError):
    """Raised when a requested agent is not registered."""

    code = "AGENT_NOT_FOUND"
    status_code = 404

    def __init__(self, agent_name: str, version: str | None = None) -> None:
        version_str = f" version {version}" if version else ""
        super().__init__(
            f"Agent '{agent_name}'{version_str} not found in registry"
        )
        self.agent_name = agent_name


class AgentAlreadyRegisteredError(DomainError):
    """Raised when attempting to register a duplicate agent."""

    code = "AGENT_ALREADY_REGISTERED"
    status_code = 409

    def __init__(self, agent_name: str, version: str) -> None:
        super().__init__(
            f"Agent '{agent_name}' version '{version}' already registered"
        )
        self.agent_name = agent_name
