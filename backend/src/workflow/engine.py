"""Workflow engine for orchestration execution.

The ``WorkflowEngine`` is the central orchestrator that:
- Executes registered workflow graphs
- Manages workflow lifecycle (start, pause, resume, cancel)
- Integrates checkpointing for recovery
- Emits events via the ``WorkflowEventEmitter``
- Tracks metrics (execution time, cost, tokens)
- Persists execution history
- Handles timeouts and cancellation

The engine is the primary entry point for executing any workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.logging import get_logger
from src.workflow.base_graph import BaseWorkflowGraph
from src.workflow.checkpoint import CheckpointManager
from src.workflow.contexts import (
    CancellationToken,
    ExecutionContext,
    IdentityContext,
    WorkflowContext,
)
from src.workflow.events import WorkflowEventEmitter
from src.workflow.exceptions import (
    WorkflowCancelledError,
    WorkflowExecutionError,
    WorkflowNotFoundError,
    WorkflowTimeoutError,
)
from src.workflow.registry import GraphRegistry
from src.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------
class ExecutionResult:
    """Result of a workflow execution.

    Attributes:
        success: Whether the execution succeeded.
        execution_id: The unique execution ID.
        workflow_id: The workflow definition ID.
        state: The final workflow state.
        execution_time_seconds: Total execution time.
        total_cost_usd: Total cost incurred.
        total_tokens: Total tokens consumed.
        error: The error that occurred, if any.
        checkpoint_ref: The last checkpoint reference, if any.
    """

    def __init__(
        self,
        success: bool,
        execution_id: UUID,
        workflow_id: str,
        state: WorkflowState,
        execution_time_seconds: float = 0.0,
        total_cost_usd: float = 0.0,
        total_tokens: int = 0,
        error: Exception | None = None,
        checkpoint_ref: str | None = None,
    ) -> None:
        self.success = success
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.state = state
        self.execution_time_seconds = execution_time_seconds
        self.total_cost_usd = total_cost_usd
        self.total_tokens = total_tokens
        self.error = error
        self.checkpoint_ref = checkpoint_ref
        self.completed_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        status = "succeeded" if self.success else "failed"
        return (
            f"ExecutionResult({status}, "
            f"workflow={self.workflow_id}, "
            f"time={self.execution_time_seconds:.1f}s, "
            f"cost=${self.total_cost_usd:.4f}, "
            f"tokens={self.total_tokens})"
        )


# ---------------------------------------------------------------------------
# Workflow engine
# ---------------------------------------------------------------------------
class WorkflowEngine:
    """Central workflow execution engine.

    Manages the complete lifecycle of workflow executions:
    - Start, pause, resume, cancel
    - Checkpoint save/restore
    - Event emission
    - Metrics tracking
    - Timeout enforcement
    - Error handling

    Attributes:
        registry: The graph registry for workflow lookup.
        checkpoint_manager: The checkpoint manager.
        event_emitter: The workflow event emitter.
    """

    def __init__(
        self,
        registry: GraphRegistry | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        event_emitter: WorkflowEventEmitter | None = None,
    ) -> None:
        """Initialize the workflow engine.

        Args:
            registry: Graph registry. Created if not provided.
            checkpoint_manager: Checkpoint manager. Created if not provided.
            event_emitter: Event emitter. Created if not provided.
        """
        self.registry = registry or GraphRegistry()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.event_emitter = event_emitter or WorkflowEventEmitter()
        self._logger = get_logger(__name__)
        self._active_executions: dict[UUID, CancellationToken] = {}

    # -----------------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------------
    def register_workflow(self, graph: BaseWorkflowGraph) -> None:
        """Register a workflow graph.

        Args:
            graph: The workflow graph to register.
        """
        self.registry.register(graph)

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------
    async def execute(
        self,
        workflow_name: str,
        initial_state: WorkflowState,
        *,
        version: str | None = None,
        project_id: UUID | None = None,
        user_id: UUID | None = None,
        timeout_seconds: int | None = None,
        repositories: dict[str, Any] | None = None,
        gateways: dict[str, Any] | None = None,
        services: dict[str, Any] | None = None,
        config: Any = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
    ) -> ExecutionResult:
        """Execute a registered workflow.

        Args:
            workflow_name: The name of the workflow to execute.
            initial_state: The initial workflow state.
            version: Optional workflow version. Defaults to latest.
            project_id: Optional project ID.
            user_id: Optional user ID.
            timeout_seconds: Optional execution timeout.
            repositories: Optional repository instances for DI.
            gateways: Optional gateway instances for DI.
            services: Optional service instances for DI.
            config: Optional application configuration.
            correlation_id: Optional correlation ID for tracing.
            trace_id: Optional trace ID for OpenTelemetry.

        Returns:
            An ``ExecutionResult`` with execution details.

        Raises:
            WorkflowNotFoundError: If the workflow is not registered.
            WorkflowTimeoutError: If execution exceeds timeout.
            WorkflowCancelledError: If execution is cancelled.
            WorkflowExecutionError: If execution fails.
        """
        # Look up the graph
        graph = self.registry.get(workflow_name, version)
        workflow_id = f"{workflow_name}:{graph.metadata.version}"

        # Create execution identity
        execution_id = uuid4()
        identity = IdentityContext(
            project_id=project_id,
            user_id=user_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
        )

        # Create execution context
        execution_ctx = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            timeout_seconds=timeout_seconds,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        # Create cancellation token
        cancellation_token = CancellationToken()
        self._active_executions[execution_id] = cancellation_token

        # Create workflow context
        context = WorkflowContext(
            identity=identity,
            execution=execution_ctx,
            config=config,
            repositories=repositories or {},
            gateways=gateways or {},
            services=services or {},
            cancellation_token=cancellation_token,
        )

        # Set state metadata
        initial_state.execution_id = execution_id
        initial_state.workflow_id = workflow_id
        initial_state.correlation_id = correlation_id
        initial_state.trace_id = trace_id
        initial_state.metadata = initial_state.metadata.model_copy(
            update={
                "workflow_name": workflow_name,
                "workflow_version": graph.metadata.version,
                "content_type": graph.metadata.content_type,
            }
        )

        # Emit start event
        await self.event_emitter.emit_workflow_started(
            execution_id, workflow_id, project_id, correlation_id
        )

        start_time = datetime.now(timezone.utc)
        self._logger.info(
            "workflow_execution_started",
            execution_id=str(execution_id),
            workflow_id=workflow_id,
            project_id=str(project_id) if project_id else None,
        )

        try:
            # Build the graph if not already built
            if not graph.is_built:
                await graph.build()

            # Check timeout
            if timeout_seconds is not None:
                import asyncio
                try:
                    final_state = await asyncio.wait_for(
                        graph.execute(context, initial_state),
                        timeout=timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    raise WorkflowTimeoutError(workflow_id, timeout_seconds)
            else:
                final_state = await graph.execute(context, initial_state)

            # Check cancellation
            if cancellation_token.is_cancelled:
                self._logger.info(
                    "workflow_cancelled",
                    execution_id=str(execution_id),
                    reason=cancellation_token.reason,
                )
                await self.event_emitter.emit_workflow_cancelled(
                    execution_id, workflow_id,
                    cancellation_token.reason or "Cancelled",
                    correlation_id,
                )
                raise WorkflowCancelledError(
                    workflow_id, cancellation_token.reason or "Cancelled"
                )

            # Mark completed
            final_state.execution.mark_completed()

            # Calculate metrics
            end_time = datetime.now(timezone.utc)
            exec_seconds = (end_time - start_time).total_seconds()
            total_cost = final_state.total_cost_usd
            total_tokens = final_state.total_tokens

            # Save final checkpoint
            checkpoint = await self.checkpoint_manager.save(
                execution_id=execution_id,
                workflow_id=workflow_id,
                node_name="__end__",
                step=final_state.execution.completed_steps,
                state=final_state,
            )

            # Emit completion event
            await self.event_emitter.emit_workflow_completed(
                execution_id, workflow_id, exec_seconds,
                total_cost, total_tokens, correlation_id,
            )

            self._logger.info(
                "workflow_execution_completed",
                execution_id=str(execution_id),
                workflow_id=workflow_id,
                execution_time_seconds=exec_seconds,
                total_cost_usd=total_cost,
                total_tokens=total_tokens,
            )

            return ExecutionResult(
                success=True,
                execution_id=execution_id,
                workflow_id=workflow_id,
                state=final_state,
                execution_time_seconds=exec_seconds,
                total_cost_usd=total_cost,
                total_tokens=total_tokens,
                checkpoint_ref=checkpoint.checkpoint_ref if checkpoint else None,
            )

        except WorkflowCancelledError:
            raise
        except WorkflowTimeoutError:
            raise
        except Exception as exc:
            # Determine failing node
            node_name = final_state.execution.current_node if 'final_state' in dir() else None

            self._logger.error(
                "workflow_execution_failed",
                execution_id=str(execution_id),
                workflow_id=workflow_id,
                error=str(exc),
            )

            await self.event_emitter.emit_workflow_failed(
                execution_id, workflow_id, str(exc),
                node_name, correlation_id,
            )

            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                workflow_id=workflow_id,
                state=initial_state,
                error=exc,
            )
        finally:
            self._active_executions.pop(execution_id, None)

    # -----------------------------------------------------------------------
    # Cancellation
    # -----------------------------------------------------------------------
    async def cancel(
        self,
        execution_id: UUID,
        reason: str = "Cancelled by request",
    ) -> bool:
        """Cancel a running workflow execution.

        Args:
            execution_id: The execution ID to cancel.
            reason: Cancellation reason.

        Returns:
            True if the execution was found and cancellation requested.
        """
        token = self._active_executions.get(execution_id)
        if token is None:
            return False

        token.cancel(reason)
        self._logger.info(
            "workflow_cancellation_requested",
            execution_id=str(execution_id),
            reason=reason,
        )

        await self.event_emitter.emit_cancellation_requested(
            execution_id, reason,
        )

        return True

    # -----------------------------------------------------------------------
    # Resume
    # -----------------------------------------------------------------------
    async def resume(
        self,
        execution_id: UUID,
        checkpoint_ref: str | None = None,
        *,
        repositories: dict[str, Any] | None = None,
        gateways: dict[str, Any] | None = None,
        services: dict[str, Any] | None = None,
        config: Any = None,
    ) -> ExecutionResult:
        """Resume a paused or interrupted workflow from a checkpoint.

        Args:
            execution_id: The execution ID to resume.
            checkpoint_ref: Optional checkpoint reference. If None,
                uses the latest checkpoint for the execution.
            repositories: Optional repository instances for DI.
            gateways: Optional gateway instances for DI.
            services: Optional service instances for DI.
            config: Optional application configuration.

        Returns:
            An ``ExecutionResult`` with execution details.

        Raises:
            CheckpointNotFoundError: If no checkpoint is found.
            WorkflowExecutionError: If resume fails.
        """
        if checkpoint_ref is None:
            checkpoint = await self.checkpoint_manager.get_latest(execution_id)
            if checkpoint is None:
                from src.workflow.exceptions import CheckpointNotFoundError
                raise CheckpointNotFoundError(f"No checkpoint for execution {execution_id}")
            checkpoint_ref = checkpoint.checkpoint_ref

        self._logger.info(
            "workflow_resume_requested",
            execution_id=str(execution_id),
            checkpoint_ref=checkpoint_ref,
        )

        # In a full implementation, this would:
        # 1. Load the state from the checkpoint
        # 2. Reconstruct the WorkflowContext
        # 3. Resume the LangGraph from the checkpoint
        # For now, this is a framework placeholder

        raise NotImplementedError(
            "Resume from checkpoint requires LangGraph checkpoint integration. "
            "This will be implemented with the first concrete workflow."
        )

    # -----------------------------------------------------------------------
    # Querying
    # -----------------------------------------------------------------------
    @property
    def active_execution_count(self) -> int:
        """Return the number of currently active executions."""
        return len(self._active_executions)

    @property
    def active_execution_ids(self) -> list[UUID]:
        """Return the IDs of currently active executions."""
        return list(self._active_executions.keys())

    def is_active(self, execution_id: UUID) -> bool:
        """Check if an execution is currently active."""
        return execution_id in self._active_executions

    # -----------------------------------------------------------------------
    # History
    # -----------------------------------------------------------------------
    def get_execution_history(
        self,
        state: WorkflowState,
    ) -> list[dict[str, Any]]:
        """Get the execution history from a workflow state.

        Args:
            state: The workflow state with node history.

        Returns:
            List of node execution records as dictionaries.
        """
        return [
            record.model_dump()
            for record in state.execution.node_history
        ]
