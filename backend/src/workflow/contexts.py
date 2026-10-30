"""Context objects for workflow orchestration.

Provides strongly-typed context objects that are passed to nodes and
graphs during execution.  These objects encapsulate identity, execution
state, and dependency injection — nodes never access global state or
instantiate dependencies directly.

Contexts are created by the ``WorkflowEngine`` at execution time and
passed to each node via the ``BaseNode.execute`` method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Identity context
# ---------------------------------------------------------------------------
class IdentityContext(BaseModel):
    """Identifies who and what is being executed.

    Attributes:
        project_id: The project this workflow belongs to.
        user_id: The user who initiated the workflow.
        workflow_id: The workflow definition identifier (e.g. "youtube_video_v1").
        execution_id: Unique identifier for this specific execution run.
    """

    project_id: UUID | None = None
    user_id: UUID | None = None
    workflow_id: str = ""
    execution_id: UUID = Field(default_factory=uuid4)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Execution context
# ---------------------------------------------------------------------------
class ExecutionContext(BaseModel):
    """Tracks the runtime state of a single workflow execution.

    Attributes:
        execution_id: Unique identifier for this execution.
        workflow_id: The workflow definition being executed.
        started_at: When the execution started.
        current_node: The name of the currently executing node.
        retry_count: Total retries across all nodes.
        timeout_seconds: Maximum execution time before timeout.
        correlation_id: Correlation ID for distributed tracing.
        trace_id: Trace ID for OpenTelemetry compatibility.
    """

    execution_id: UUID = Field(default_factory=uuid4)
    workflow_id: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_node: str = ""
    retry_count: int = 0
    timeout_seconds: int | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time since execution started."""
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    @property
    def is_timed_out(self) -> bool:
        """Check if the execution has exceeded its timeout."""
        if self.timeout_seconds is None:
            return False
        return self.elapsed_seconds > self.timeout_seconds


# ---------------------------------------------------------------------------
# Cancellation token
# ---------------------------------------------------------------------------
class CancellationToken:
    """Cooperative cancellation token for workflow execution.

    Nodes should check ``is_cancelled`` periodically and abort
    gracefully if cancellation is requested.
    """

    def __init__(self) -> None:
        self._cancelled: bool = False
        self._reason: str | None = None

    def cancel(self, reason: str = "Cancelled by request") -> None:
        """Request cancellation of the workflow."""
        self._cancelled = True
        self._reason = reason

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancelled

    @property
    def reason(self) -> str | None:
        """The cancellation reason, if any."""
        return self._reason

    def reset(self) -> None:
        """Reset the token for reuse."""
        self._cancelled = False
        self._reason = None


# ---------------------------------------------------------------------------
# Repository protocol (for type hints in NodeContext)
# ---------------------------------------------------------------------------
class RepositoryProtocol(Protocol):
    """Protocol for repository objects passed to nodes."""

    async def get_by_id(self, id: UUID) -> Any: ...
    async def add(self, entity: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Gateway protocol (for type hints in NodeContext)
# ---------------------------------------------------------------------------
class GatewayProtocol(Protocol):
    """Protocol for gateway objects passed to nodes."""

    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...


# ---------------------------------------------------------------------------
# Node context
# ---------------------------------------------------------------------------
class NodeContext(BaseModel):
    """Complete context passed to every workflow node.

    Encapsulates all dependencies, state, and metadata that a node
    needs to execute.  Nodes receive this object and should never
    access global state or instantiate dependencies directly.

    Attributes:
        identity: Who and what is being executed.
        state: The current workflow state (mutable).
        execution: Runtime execution tracking.
        repositories: Dictionary of repository instances by name.
        gateways: Dictionary of gateway instances by name.
        services: Dictionary of service instances by name.
        logger: Structured logger instance.
        config: Application configuration service.
        cancellation_token: Cooperative cancellation token.
    """

    identity: IdentityContext = Field(default_factory=IdentityContext)
    state: WorkflowState = Field(default_factory=WorkflowState)
    execution: ExecutionContext = Field(default_factory=ExecutionContext)
    repositories: dict[str, Any] = Field(default_factory=dict)
    gateways: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)
    config: Any = None
    cancellation_token: CancellationToken = Field(default_factory=CancellationToken)

    model_config = {"arbitrary_types_allowed": True}

    @property
    def logger(self) -> Any:
        """Return a logger bound to the current node context."""
        return get_logger(f"workflow.node.{self.execution.current_node or 'unknown'}")

    def get_repository(self, name: str) -> Any:
        """Get a repository by name.

        Args:
            name: The repository name (e.g. "project", "workflow").

        Returns:
            The repository instance.

        Raises:
            KeyError: If the repository is not found.
        """
        if name not in self.repositories:
            raise KeyError(f"Repository '{name}' not available in node context")
        return self.repositories[name]

    def get_gateway(self, name: str) -> Any:
        """Get a gateway by name.

        Args:
            name: The gateway name (e.g. "llm", "image", "video").

        Returns:
            The gateway instance.

        Raises:
            KeyError: If the gateway is not found.
        """
        if name not in self.gateways:
            raise KeyError(f"Gateway '{name}' not available in node context")
        return self.gateways[name]

    def get_service(self, name: str) -> Any:
        """Get a service by name.

        Args:
            name: The service name (e.g. "cost_tracker", "token_tracker").

        Returns:
            The service instance.

        Raises:
            KeyError: If the service is not found.
        """
        if name not in self.services:
            raise KeyError(f"Service '{name}' not available in node context")
        return self.services[name]

    @property
    def is_cancelled(self) -> bool:
        """Check if the workflow has been cancelled."""
        return self.cancellation_token.is_cancelled


# ---------------------------------------------------------------------------
# Workflow context (for graph-level access)
# ---------------------------------------------------------------------------
class WorkflowContext(BaseModel):
    """Context for a complete workflow execution.

    Higher-level than ``NodeContext`` — contains the graph definition,
    checkpoint manager, and event emitter alongside the execution state.

    Attributes:
        identity: Who and what is being executed.
        execution: Runtime execution tracking.
        config: Application configuration service.
        repositories: Dictionary of repository instances by name.
        gateways: Dictionary of gateway instances by name.
        services: Dictionary of service instances by name.
        cancellation_token: Cooperative cancellation token.
    """

    identity: IdentityContext = Field(default_factory=IdentityContext)
    execution: ExecutionContext = Field(default_factory=ExecutionContext)
    config: Any = None
    repositories: dict[str, Any] = Field(default_factory=dict)
    gateways: dict[str, Any] = Field(default_factory=dict)
    services: dict[str, Any] = Field(default_factory=dict)
    cancellation_token: CancellationToken = Field(default_factory=CancellationToken)

    model_config = {"arbitrary_types_allowed": True}

    def create_node_context(self, state: WorkflowState, node_name: str) -> NodeContext:
        """Create a ``NodeContext`` for a specific node execution.

        Args:
            state: The current workflow state.
            node_name: The name of the node to execute.

        Returns:
            A ``NodeContext`` with the node name set in execution context.
        """
        return NodeContext(
            identity=self.identity,
            state=state,
            execution=self.execution.model_copy(update={"current_node": node_name}),
            repositories=self.repositories,
            gateways=self.gateways,
            services=self.services,
            config=self.config,
            cancellation_token=self.cancellation_token,
        )
