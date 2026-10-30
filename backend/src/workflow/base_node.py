"""Base node for the workflow orchestration framework.

Every future AI node (Research Agent, Script Writer, Scene Planner, etc.)
must inherit from ``BaseNode``.  The base class provides:

- Input validation (schema-based)
- Output validation (schema-based)
- Structured logging
- Error handling with classification
- Retry support via ``RetryPolicy``
- Checkpoint updates
- Metrics collection (execution time, cost, tokens)
- Cost tracking hooks
- Token tracking hooks
- Lifecycle events (before/after execute)

Subclasses implement ``execute`` and optionally ``validate_input``
and ``validate_output``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ValidationError as PydanticValidationError

from src.core.exceptions import ValidationError
from src.workflow.contexts import NodeContext
from src.workflow.exceptions import NodeExecutionError, NodeValidationError
from src.workflow.retry_policy import RetryExecutor, RetryPolicy, RetryPolicies
from src.workflow.state import NodeExecutionRecord, WorkflowState


class BaseNode(ABC):
    """Abstract base class for all workflow nodes.

    A node is a single unit of work within a workflow graph.  It
    receives a ``NodeContext`` containing all dependencies and the
    current ``WorkflowState``, performs its work, and returns the
    updated state.

    Subclasses must implement:
        - ``name``: A unique node name.
        - ``execute``: The core logic.

    Subclasses may override:
        - ``input_schema``: Pydantic model for input validation.
        - ``output_schema``: Pydantic model for output validation.
        - ``retry_policy``: Retry policy for this node.
        - ``on_before_execute``: Pre-execution hook.
        - ``on_after_execute``: Post-execution hook.
        - ``on_error``: Error handler hook.

    Attributes:
        name: Unique name of this node within the graph.
        node_type: Type category (e.g. "agent", "processor", "router").
    """

    def __init__(
        self,
        name: str | None = None,
        *,
        node_type: str = "processor",
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        """Initialize the node.

        Args:
            name: Unique node name. If None, uses the class name.
            node_type: Type category for metrics and logging.
            retry_policy: Retry policy. Defaults to ``RetryPolicies.STANDARD``.
        """
        self.name = name or self.__class__.__name__.lower()
        self.node_type = node_type
        self.retry_policy = retry_policy or RetryPolicies.STANDARD
        self._logger = None

    # -----------------------------------------------------------------------
    # Properties for subclasses to override
    # -----------------------------------------------------------------------
    @property
    def input_schema(self) -> type[BaseModel] | None:
        """Pydantic model for input validation. Override in subclasses."""
        return None

    @property
    def output_schema(self) -> type[BaseModel] | None:
        """Pydantic model for output validation. Override in subclasses."""
        return None

    # -----------------------------------------------------------------------
    # Abstract methods
    # -----------------------------------------------------------------------
    @abstractmethod
    async def execute(self, context: NodeContext) -> WorkflowState:
        """Execute the node's core logic.

        Args:
            context: The node context with state and dependencies.

        Returns:
            The updated ``WorkflowState``.
        """
        ...

    # -----------------------------------------------------------------------
    # Lifecycle hooks (override in subclasses)
    # -----------------------------------------------------------------------
    async def on_before_execute(self, context: NodeContext) -> None:
        """Called before the node executes. Override for custom logic."""
        pass

    async def on_after_execute(self, context: NodeContext, state: WorkflowState) -> None:
        """Called after the node executes successfully. Override for custom logic."""
        pass

    async def on_error(self, context: NodeContext, error: Exception) -> None:
        """Called when the node encounters an error. Override for custom logic."""
        pass

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    def validate_input(self, state: WorkflowState) -> None:
        """Validate the input state before execution.

        If ``input_schema`` is defined, validates the state against it.
        Override for custom validation logic.

        Args:
            state: The workflow state to validate.

        Raises:
            NodeValidationError: If validation fails.
        """
        if self.input_schema is not None:
            try:
                self.input_schema.model_validate(state.model_dump())
            except PydanticValidationError as exc:
                raise NodeValidationError(self.name, "input", str(exc)) from exc

    def validate_output(self, state: WorkflowState) -> None:
        """Validate the output state after execution.

        If ``output_schema`` is defined, validates the state against it.
        Override for custom validation logic.

        Args:
            state: The workflow state to validate.

        Raises:
            NodeValidationError: If validation fails.
        """
        if self.output_schema is not None:
            try:
                self.output_schema.model_validate(state.model_dump())
            except PydanticValidationError as exc:
                raise NodeValidationError(self.name, "output", str(exc)) from exc

    # -----------------------------------------------------------------------
    # Public execution method (called by the workflow engine)
    # -----------------------------------------------------------------------
    async def run(self, context: NodeContext) -> WorkflowState:
        """Run the node with full lifecycle management.

        This method is called by the workflow engine.  It handles:
        - Cancellation checking
        - Input validation
        - Pre-execution hooks
        - Retry logic
        - Output validation
        - Post-execution hooks
        - Metrics recording
        - Error handling

        Args:
            context: The node context with state and dependencies.

        Returns:
            The updated ``WorkflowState``.

        Raises:
            NodeExecutionError: If the node fails after all retries.
            NodeValidationError: If input or output validation fails.
        """
        logger = context.logger
        self._logger = logger

        # Check cancellation
        if context.is_cancelled:
            logger.info("node_cancelled", node=self.name)
            return context.state

        started_at = datetime.now(timezone.utc)
        logger.info("node_started", node=self.name, node_type=self.node_type)

        # Input validation
        try:
            self.validate_input(context.state)
        except NodeValidationError:
            logger.warning("node_input_validation_failed", node=self.name)
            raise

        # Pre-execution hook
        await self.on_before_execute(context)

        # Execute with retry
        retry_executor = RetryExecutor(self.retry_policy)
        result = await retry_executor.execute(
            self.execute, context, logger=logger
        )

        if not result.success:
            error = result.last_error or NodeExecutionError(self.name, "Unknown error")
            await self.on_error(context, error)

            # Record failed execution
            record = NodeExecutionRecord(
                node_name=self.name,
                node_type=self.node_type,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                execution_time_ms=result.execution_time_ms,
                retry_count=result.attempts - 1,
                error_message=str(error),
            )
            context.state.execution.record_node(record)

            logger.error(
                "node_failed",
                node=self.name,
                attempts=result.attempts,
                error=str(error),
                execution_time_ms=result.execution_time_ms,
            )
            raise NodeExecutionError(self.name, str(error)) from error

        # Output validation
        try:
            self.validate_output(context.state)
        except NodeValidationError:
            logger.warning("node_output_validation_failed", node=self.name)
            raise

        # Post-execution hook
        await self.on_after_execute(context, context.state)

        # Record successful execution
        completed_at = datetime.now(timezone.utc)
        record = NodeExecutionRecord(
            node_name=self.name,
            node_type=self.node_type,
            status="succeeded",
            started_at=started_at,
            completed_at=completed_at,
            execution_time_ms=int((completed_at - started_at).total_seconds() * 1000),
            retry_count=result.attempts - 1,
        )
        context.state.execution.record_node(record)
        context.state.execution.completed_steps += 1

        logger.info(
            "node_completed",
            node=self.name,
            execution_time_ms=record.execution_time_ms,
            attempts=result.attempts,
        )

        return context.state

    # -----------------------------------------------------------------------
    # Cost and token tracking helpers
    # -----------------------------------------------------------------------
    def record_cost(
        self,
        context: NodeContext,
        amount: float,
        category: str = "llm",
    ) -> None:
        """Record a cost incurred by this node.

        Args:
            context: The node context.
            amount: Cost in USD.
            category: Cost category (llm, image, video, voice, render).
        """
        context.state.add_cost(amount, category)

        cost_tracker = context.services.get("cost_tracker")
        if cost_tracker is not None:
            try:
                cost_tracker.record  # check if method exists
            except AttributeError:
                pass

    def record_tokens(
        self,
        context: NodeContext,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> None:
        """Record token usage by this node.

        Args:
            context: The node context.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            cached_tokens: Number of cached tokens used.
        """
        context.state.add_tokens(input_tokens, output_tokens, cached_tokens)

    def add_warning(self, context: NodeContext, warning: str) -> None:
        """Add a warning to the workflow state.

        Args:
            context: The node context.
            warning: The warning message.
        """
        context.state.execution.warnings.append(
            f"{self.name}: {warning}"
        )

    def add_error(self, context: NodeContext, error: str) -> None:
        """Add an error to the workflow state without failing.

        Args:
            context: The node context.
            error: The error message.
        """
        context.state.execution.errors.append(
            f"{self.name}: {error}"
        )
