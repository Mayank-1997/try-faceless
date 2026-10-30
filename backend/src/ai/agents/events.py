"""Agent event types for the AI Agent Framework.

Defines event type constants and an agent event emitter that wraps
the existing ``EventBus`` with agent-specific lifecycle events:

- ``AgentStarted``
- ``PromptGenerated``
- ``PromptExecuted``
- ``ValidationFailed``
- ``RetryTriggered``
- ``AgentCompleted``
- ``AgentFailed``
- ``ArtifactsCreated``
- ``QualityEvaluated``
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
class AgentEvents:
    """Constants for agent event types."""

    AGENT_STARTED = "AgentStarted"
    PROMPT_GENERATED = "PromptGenerated"
    PROMPT_EXECUTED = "PromptExecuted"
    VALIDATION_FAILED = "ValidationFailed"
    RETRY_TRIGGERED = "RetryTriggered"
    AGENT_COMPLETED = "AgentCompleted"
    AGENT_FAILED = "AgentFailed"
    ARTIFACTS_CREATED = "ArtifactsCreated"
    QUALITY_EVALUATED = "QualityEvaluated"


# ---------------------------------------------------------------------------
# Agent event emitter
# ---------------------------------------------------------------------------
class AgentEventEmitter:
    """Emits agent lifecycle events on the event bus.

    Wraps the existing ``EventBus`` with agent-specific event helpers
    that automatically include agent name, execution ID, and
    correlation IDs.

    Attributes:
        event_bus: The underlying event bus.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the agent event emitter.

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
        source: str = "agent_framework",
    ) -> None:
        """Emit an agent event.

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
            "agent_event_emitted",
            event_type=event_type,
            correlation_id=correlation_id,
        )

        if self._event_bus is not None:
            try:
                await self._event_bus.publish(event)
            except Exception as exc:
                self._logger.error(
                    "agent_event_publish_failed",
                    event_type=event_type,
                    error=str(exc),
                )

    async def emit_agent_started(
        self,
        agent_name: str,
        agent_type: str,
        execution_id: UUID,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit an AgentStarted event."""
        await self.emit(
            AgentEvents.AGENT_STARTED,
            {
                "agent_name": agent_name,
                "agent_type": agent_type,
                "execution_id": str(execution_id),
                "started_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_prompt_generated(
        self,
        agent_name: str,
        template_name: str,
        prompt_length: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a PromptGenerated event."""
        await self.emit(
            AgentEvents.PROMPT_GENERATED,
            {
                "agent_name": agent_name,
                "template_name": template_name,
                "prompt_length": prompt_length,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_prompt_executed(
        self,
        agent_name: str,
        provider: str,
        model: str,
        cost_usd: float,
        tokens: int,
        latency_ms: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a PromptExecuted event."""
        await self.emit(
            AgentEvents.PROMPT_EXECUTED,
            {
                "agent_name": agent_name,
                "provider": provider,
                "model": model,
                "cost_usd": cost_usd,
                "tokens": tokens,
                "latency_ms": latency_ms,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_validation_failed(
        self,
        agent_name: str,
        errors: list[str],
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a ValidationFailed event."""
        await self.emit(
            AgentEvents.VALIDATION_FAILED,
            {
                "agent_name": agent_name,
                "errors": errors,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_retry_triggered(
        self,
        agent_name: str,
        attempt: int,
        delay_seconds: float,
        error: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a RetryTriggered event."""
        await self.emit(
            AgentEvents.RETRY_TRIGGERED,
            {
                "agent_name": agent_name,
                "attempt": attempt,
                "delay_seconds": delay_seconds,
                "error": error,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_agent_completed(
        self,
        agent_name: str,
        execution_time_ms: int,
        cost_usd: float,
        tokens: int,
        quality_score: float | None = None,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit an AgentCompleted event."""
        await self.emit(
            AgentEvents.AGENT_COMPLETED,
            {
                "agent_name": agent_name,
                "execution_time_ms": execution_time_ms,
                "cost_usd": cost_usd,
                "tokens": tokens,
                "quality_score": quality_score,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_agent_failed(
        self,
        agent_name: str,
        error: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit an AgentFailed event."""
        await self.emit(
            AgentEvents.AGENT_FAILED,
            {
                "agent_name": agent_name,
                "error": error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_artifacts_created(
        self,
        agent_name: str,
        artifact_count: int,
        artifact_types: list[str],
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit an ArtifactsCreated event."""
        await self.emit(
            AgentEvents.ARTIFACTS_CREATED,
            {
                "agent_name": agent_name,
                "artifact_count": artifact_count,
                "artifact_types": artifact_types,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )

    async def emit_quality_evaluated(
        self,
        agent_name: str,
        score: float,
        passed: bool,
        threshold: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Emit a QualityEvaluated event."""
        await self.emit(
            AgentEvents.QUALITY_EVALUATED,
            {
                "agent_name": agent_name,
                "score": score,
                "passed": passed,
                "threshold": threshold,
            },
            correlation_id=correlation_id,
            source=f"agent.{agent_name}",
        )
