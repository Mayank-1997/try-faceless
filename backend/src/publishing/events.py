"""Publishing Platform events.

Events emitted during the publishing lifecycle:
- PublishingPlanned
- PublishingStarted
- UploadProgress
- PublishingCompleted
- PublishingFailed
- RetryTriggered
- ScheduleCreated
- DraftSaved
"""

from __future__ import annotations

from uuid import UUID

from src.core.logging import get_logger


class PublishingEvents:
    """Constants for publishing event types."""

    PUBLISHING_PLANNED = "PublishingPlanned"
    PUBLISHING_STARTED = "PublishingStarted"
    UPLOAD_PROGRESS = "UploadProgress"
    PUBLISHING_COMPLETED = "PublishingCompleted"
    PUBLISHING_FAILED = "PublishingFailed"
    RETRY_TRIGGERED = "RetryTriggered"
    SCHEDULE_CREATED = "ScheduleCreated"
    DRAFT_SAVED = "DraftSaved"


class PublishingEventEmitter:
    """Event emitter for publishing platform events.

    Uses structured logging for event emission. When an EventBus is
    available, events are also published to the bus for real-time
    progress tracking via WebSockets/SSE.
    """

    def __init__(self, event_bus: object | None = None) -> None:
        self._event_bus = event_bus
        self._logger = get_logger(__name__)

    async def emit(
        self,
        event_type: str,
        data: dict,
        *,
        correlation_id: str | None = None,
        source: str = "publishing",
    ) -> None:
        """Emit a publishing event."""
        self._logger.info(
            "publishing_event_emitted",
            event_type=event_type,
            correlation_id=correlation_id,
            source=source,
            **{k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
        )
        if self._event_bus is not None:
            try:
                await self._event_bus.publish(event_type, data)  # type: ignore[attr-defined]
            except Exception:
                pass

    async def emit_publishing_planned(
        self, plan_id: UUID, project_id: str, platform_count: int, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.PUBLISHING_PLANNED,
            {"plan_id": str(plan_id), "project_id": project_id, "platform_count": platform_count},
            correlation_id=correlation_id,
            source="publishing.planner",
        )

    async def emit_publishing_started(
        self, task_id: UUID, platform: str, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.PUBLISHING_STARTED,
            {"task_id": str(task_id), "platform": platform},
            correlation_id=correlation_id,
            source="publishing.publisher",
        )

    async def emit_upload_progress(
        self, task_id: UUID, progress: float, bytes_uploaded: int = 0, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.UPLOAD_PROGRESS,
            {"task_id": str(task_id), "progress": progress, "bytes_uploaded": bytes_uploaded},
            correlation_id=correlation_id,
            source="publishing.publisher",
        )

    async def emit_publishing_completed(
        self, task_id: UUID, platform: str, video_url: str, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.PUBLISHING_COMPLETED,
            {"task_id": str(task_id), "platform": platform, "video_url": video_url},
            correlation_id=correlation_id,
            source="publishing.publisher",
        )

    async def emit_publishing_failed(
        self, task_id: UUID, platform: str, error: str, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.PUBLISHING_FAILED,
            {"task_id": str(task_id), "platform": platform, "error": error},
            correlation_id=correlation_id,
            source="publishing.publisher",
        )

    async def emit_retry_triggered(
        self, task_id: UUID, retry_count: int, max_retries: int, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.RETRY_TRIGGERED,
            {"task_id": str(task_id), "retry_count": retry_count, "max_retries": max_retries},
            correlation_id=correlation_id,
            source="publishing.queue",
        )

    async def emit_schedule_created(
        self, task_id: UUID, scheduled_at: str, platform: str, *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.SCHEDULE_CREATED,
            {"task_id": str(task_id), "scheduled_at": scheduled_at, "platform": platform},
            correlation_id=correlation_id,
            source="publishing.scheduler",
        )

    async def emit_draft_saved(
        self, task_id: UUID, platform: str, draft_id: str = "", *, correlation_id: str | None = None
    ) -> None:
        await self.emit(
            PublishingEvents.DRAFT_SAVED,
            {"task_id": str(task_id), "platform": platform, "draft_id": draft_id},
            correlation_id=correlation_id,
            source="publishing.publisher",
        )
