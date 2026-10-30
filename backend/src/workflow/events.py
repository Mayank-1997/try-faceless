"""Workflow event emission for the orchestration framework.

Emits structured events on the existing ``EventBus`` for workflow
lifecycle changes:

- ``WorkflowStarted``
- ``WorkflowCompleted``
- ``WorkflowFailed``
- ``WorkflowPaused``
- ``WorkflowCancelled``
- ``NodeStarted``
- ``NodeCompleted``
- ``NodeFailed``
- ``CheckpointSaved``
- ``RetryTriggered``
- ``CancellationRequested``

Events include correlation IDs and trace IDs for distributed tracing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.application.services.event_bus import Event, EventBus
from src.core.logging import get_logger


# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------
class WorkflowEvents:
    """Constants for workflow event types."""

    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_FAILED = "WorkflowFailed"
    WORKFLOW_PAUSED = "WorkflowPaused"
    WORKFLOW_CANCELLED = "WorkflowCancelled"
    NODE_STARTED = "NodeStarted"
    NODE_COMPLETED = "NodeCompleted"
    NODE_FAILED = "NodeFailed"
    CHECKPOINT_SAVED = "CheckpointSaved"
    RETRY_TRIGGERED = "RetryTriggered"
    CANCELLATION_REQUESTED = "CancellationRequested"


# ---------------------------------------------------------------------------
# Event emitter
# ---------------------------------------------------------------------------
class WorkflowEventEmitter:
    """Emits workflow events on the event bus.

    Wraps the existing ``EventBus`` with workflow-specific event
    helpers that automatically include correlation IDs and trace IDs.

    Attributes:
        event_bus: The underlying event bus.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the event emitter.

        Args:
            event_bus: The event bus to emit on. If None, events are
                only logged (useful for testing).
        """
        self._event_bus = event_bus
        self._logger = get_logger(__name__)

    async def emit(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        source: str = "workflow_engine",
    ) -> None:
        """Emit a workflow event.

        Args:
            event_type: The event type string.
            data: The event payload data.
            correlation_id: Optional correlation ID for tracing.
            source: The component emitting the event.
        """
        event = Event(
            event_type=event_type,
            data=data,
            correlation_id=correlation_id,
            source=source,
        )

        self._logger.info(
            "workflow_event_emitted",
            event_type=event_type,
            correlation_id=correlation_id,
        )

        if self._event_bus is not None:
            try:
                await self._event_bus.publish(event)
            except Exception as exc:
                self._logger.error(
                    "workflow_event_publish_failed",
                    event_type=event_type,
                    error=str(exc),
                )

    # -----------------------------------------------------------------------
    # Workflow lifecycle events
    # -----------------------------------------------------------------------
    async def emit_workflow_started(
        self,
        execution_id: UUID,
        workflow_id: str,
        project_id: UUID | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a WorkflowStarted event."""
        await self.emit(
            WorkflowEvents.WORKFLOW_STARTED,
            {
                "execution_id": str(execution_id),
                "workflow_id": workflow_id,
                "project_id": str(project_id) if project_id else None,
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
        )

    async def emit_workflow_completed(
        self,
        execution_id: UUID,
        workflow_id: str,
        execution_time_seconds: float,
        total_cost_usd: float,
        total_tokens: int,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a WorkflowCompleted event."""
        await self.emit(
            WorkflowEvents.WORKFLOW_COMPLETED,
            {
                "execution_id": str(execution_id),
                "workflow_id": workflow_id,
                "execution_time_seconds": execution_time_seconds,
                "total_cost_usd": total_cost_usd,
                "total_tokens": total_tokens,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
        )

    async def emit_workflow_failed(
        self,
        execution_id: UUID,
        workflow_id: str,
        error: str,
        node_name: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a WorkflowFailed event."""
        await self.emit(
            WorkflowEvents.WORKFLOW_FAILED,
            {
                "execution_id": str(execution_id),
                "workflow_id": workflow_id,
                "error": error,
                "node_name": node_name,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
        )

    async def emit_workflow_paused(
        self,
        execution_id: UUID,
        workflow_id: str,
        checkpoint_ref: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a WorkflowPaused event."""
        await self.emit(
            WorkflowEvents.WORKFLOW_PAUSED,
            {
                "execution_id": str(execution_id),
                "workflow_id": workflow_id,
                "checkpoint_ref": checkpoint_ref,
            },
            correlation_id=correlation_id,
        )

    async def emit_workflow_cancelled(
        self,
        execution_id: UUID,
        workflow_id: str,
        reason: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a WorkflowCancelled event."""
        await self.emit(
            WorkflowEvents.WORKFLOW_CANCELLED,
            {
                "execution_id": str(execution_id),
                "workflow_id": workflow_id,
                "reason": reason,
            },
            correlation_id=correlation_id,
        )

    # -----------------------------------------------------------------------
    # Node lifecycle events
    # -----------------------------------------------------------------------
    async def emit_node_started(
        self,
        execution_id: UUID,
        node_name: str,
        node_type: str = "",
        correlation_id: str | None = None,
    ) -> None:
        """Emit a NodeStarted event."""
        await self.emit(
            WorkflowEvents.NODE_STARTED,
            {
                "execution_id": str(execution_id),
                "node_name": node_name,
                "node_type": node_type,
            },
            correlation_id=correlation_id,
        )

    async def emit_node_completed(
        self,
        execution_id: UUID,
        node_name: str,
        execution_time_ms: int,
        cost_usd: float = 0.0,
        tokens: int = 0,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a NodeCompleted event."""
        await self.emit(
            WorkflowEvents.NODE_COMPLETED,
            {
                "execution_id": str(execution_id),
                "node_name": node_name,
                "execution_time_ms": execution_time_ms,
                "cost_usd": cost_usd,
                "tokens": tokens,
            },
            correlation_id=correlation_id,
        )

    async def emit_node_failed(
        self,
        execution_id: UUID,
        node_name: str,
        error: str,
        retry_count: int = 0,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a NodeFailed event."""
        await self.emit(
            WorkflowEvents.NODE_FAILED,
            {
                "execution_id": str(execution_id),
                "node_name": node_name,
                "error": error,
                "retry_count": retry_count,
            },
            correlation_id=correlation_id,
        )

    # -----------------------------------------------------------------------
    # Other events
    # -----------------------------------------------------------------------
    async def emit_checkpoint_saved(
        self,
        execution_id: UUID,
        checkpoint_ref: str,
        node_name: str,
        step: int,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a CheckpointSaved event."""
        await self.emit(
            WorkflowEvents.CHECKPOINT_SAVED,
            {
                "execution_id": str(execution_id),
                "checkpoint_ref": checkpoint_ref,
                "node_name": node_name,
                "step": step,
            },
            correlation_id=correlation_id,
        )

    async def emit_retry_triggered(
        self,
        execution_id: UUID,
        node_name: str,
        attempt: int,
        delay_seconds: float,
        error: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a RetryTriggered event."""
        await self.emit(
            WorkflowEvents.RETRY_TRIGGERED,
            {
                "execution_id": str(execution_id),
                "node_name": node_name,
                "attempt": attempt,
                "delay_seconds": delay_seconds,
                "error": error,
            },
            correlation_id=correlation_id,
        )

    async def emit_cancellation_requested(
        self,
        execution_id: UUID,
        reason: str,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a CancellationRequested event."""
        await self.emit(
            WorkflowEvents.CANCELLATION_REQUESTED,
            {
                "execution_id": str(execution_id),
                "reason": reason,
            },
            correlation_id=correlation_id,
        )
