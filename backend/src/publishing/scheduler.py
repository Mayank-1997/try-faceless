"""Scheduling Engine.

Supports:
- Immediate publish
- Specific date/time
- Timezone awareness
- Recurring publishing (future)
- Campaign scheduling (future)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.publishing.events import PublishingEventEmitter
from src.publishing.schema import (
    PublishingJobStatus,
    PublishingMode,
    PublishingTask,
    ScheduleConfig,
)
from src.core.logging import get_logger


class SchedulingEngine:
    """Manages publishing schedules.

    Supports immediate publishing, scheduled publishing at a specific
    date/time with timezone awareness, and provides architecture for
    future recurring and campaign scheduling.
    """

    def __init__(self, event_emitter: PublishingEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or PublishingEventEmitter()
        self._schedules: dict[UUID, ScheduleConfig] = {}
        self._task_schedules: dict[UUID, datetime] = {}  # task_id -> scheduled_at

    def schedule_task(self, task: PublishingTask, config: ScheduleConfig) -> PublishingTask:
        """Apply scheduling configuration to a task.

        Args:
            task: The publishing task.
            config: Scheduling configuration.

        Returns:
            The updated task.

        Raises:
            ValueError: If scheduling configuration is invalid.
        """
        if config.is_immediate:
            task.mode = PublishingMode.IMMEDIATE
            task.scheduled_at = None
            self._logger.info("task_scheduled_immediate", task_id=str(task.id))
        elif config.mode == PublishingMode.SCHEDULED:
            if config.scheduled_at is None:
                raise ValueError("Scheduled mode requires scheduled_at")

            # Convert to UTC if needed
            scheduled_at = self._to_utc(config.scheduled_at, config.timezone)

            if scheduled_at <= datetime.now(timezone.utc):
                raise ValueError("Scheduled time must be in the future")

            task.mode = PublishingMode.SCHEDULED
            task.scheduled_at = scheduled_at
            self._schedules[task.id] = config
            self._task_schedules[task.id] = scheduled_at

            self._logger.info(
                "task_scheduled",
                task_id=str(task.id),
                scheduled_at=scheduled_at.isoformat(),
            )
        elif config.mode == PublishingMode.DRAFT:
            task.mode = PublishingMode.DRAFT
            task.scheduled_at = None
        elif config.mode == PublishingMode.MANUAL_APPROVAL:
            task.mode = PublishingMode.MANUAL_APPROVAL
            task.scheduled_at = None

        return task

    async def emit_schedule_created(self, task: PublishingTask) -> None:
        """Emit a ScheduleCreated event for a task."""
        if task.scheduled_at:
            await self._events.emit_schedule_created(
                task.id,
                task.scheduled_at.isoformat(),
                task.platform.value,
            )

    def get_scheduled_time(self, task_id: UUID) -> datetime | None:
        """Get the scheduled time for a task.

        Args:
            task_id: The task ID.

        Returns:
            The scheduled datetime, or ``None`` if not scheduled.
        """
        return self._task_schedules.get(task_id)

    def get_due_tasks(self, now: datetime | None = None) -> list[UUID]:
        """Get task IDs that are due for publishing.

        Args:
            now: Current time (defaults to UTC now).

        Returns:
            List of task IDs that are due.
        """
        now = now or datetime.now(timezone.utc)
        due: list[UUID] = []
        for task_id, scheduled_at in self._task_schedules.items():
            if scheduled_at <= now:
                due.append(task_id)
        return due

    def cancel_schedule(self, task_id: UUID) -> bool:
        """Cancel a scheduled task.

        Args:
            task_id: The task ID to cancel.

        Returns:
            ``True`` if a schedule was cancelled.
        """
        if task_id in self._schedules:
            del self._schedules[task_id]
        if task_id in self._task_schedules:
            del self._task_schedules[task_id]
            self._logger.info("schedule_cancelled", task_id=str(task_id))
            return True
        return False

    def list_scheduled_tasks(self) -> dict[UUID, datetime]:
        """List all scheduled tasks with their scheduled times."""
        return dict(self._task_schedules)

    @property
    def scheduled_count(self) -> int:
        """Number of scheduled tasks."""
        return len(self._task_schedules)

    def _to_utc(self, dt: datetime, tz_name: str = "UTC") -> datetime:
        """Convert a datetime to UTC.

        Args:
            dt: The datetime to convert.
            tz_name: Timezone name (for future use with zoneinfo).

        Returns:
            The datetime in UTC.
        """
        if dt.tzinfo is None:
            # Assume UTC if no timezone info
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def create_schedule_config(
        self,
        *,
        mode: PublishingMode = PublishingMode.IMMEDIATE,
        scheduled_at: datetime | None = None,
        timezone_str: str = "UTC",
        recurring: bool = False,
        recurring_cron: str | None = None,
        campaign_id: str | None = None,
    ) -> ScheduleConfig:
        """Create a scheduling configuration.

        Args:
            mode: Publishing mode.
            scheduled_at: When to publish (for scheduled mode).
            timezone_str: Timezone string.
            recurring: Whether this is recurring.
            recurring_cron: Cron expression for recurring.
            campaign_id: Campaign ID for campaign scheduling.

        Returns:
            A ``ScheduleConfig``.
        """
        return ScheduleConfig(
            mode=mode,
            scheduled_at=scheduled_at,
            timezone=timezone_str,
            recurring=recurring,
            recurring_cron=recurring_cron,
            campaign_id=campaign_id,
        )

    def next_run_time(self, task_id: UUID) -> datetime | None:
        """Get the next run time for a task.

        For recurring tasks, this would calculate the next occurrence
        based on the cron expression. For now, returns the scheduled time.

        Args:
            task_id: The task ID.

        Returns:
            The next run time, or ``None``.
        """
        return self._task_schedules.get(task_id)
