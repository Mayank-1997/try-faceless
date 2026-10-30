"""Progress Tracking for Publishing.

Tracks:
- Queued
- Uploading
- Thumbnail upload
- Metadata update
- Publishing
- Completed
- Failed
- Cancelled

Exposes through:
- REST APIs
- WebSockets
- Future SSE
"""

from __future__ import annotations

from typing import Any, Callable
from uuid import UUID

from src.publishing.schema import PublishingJobStatus, PublishingProgress
from src.core.logging import get_logger


class ProgressTracker:
    """Tracks and exposes publishing progress.

    Maintains progress state for each publishing job and provides
    callbacks for real-time updates via WebSockets or SSE.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._progress: dict[UUID, PublishingProgress] = {}
        self._callbacks: dict[UUID, list[Callable[[PublishingProgress], None]]] = {}

    def register(self, task_id: UUID) -> PublishingProgress:
        """Register a new task for progress tracking.

        Args:
            task_id: The publishing task ID.

        Returns:
            Initial ``PublishingProgress``.
        """
        progress = PublishingProgress(task_id=task_id)
        self._progress[task_id] = progress
        self._logger.info("progress_registered", task_id=str(task_id))
        return progress

    def update(
        self,
        task_id: UUID,
        *,
        status: PublishingJobStatus | None = None,
        percentage: float | None = None,
        stage: str | None = None,
        upload_progress: float | None = None,
        estimated_time_remaining: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PublishingProgress:
        """Update progress for a task.

        Args:
            task_id: The publishing task ID.
            status: New status.
            percentage: Progress percentage (0-100).
            stage: Current stage name.
            upload_progress: Upload progress (0-100).
            estimated_time_remaining: Estimated seconds remaining.
            metadata: Additional metadata.

        Returns:
            Updated ``PublishingProgress``.
        """
        if task_id not in self._progress:
            self.register(task_id)

        progress = self._progress[task_id]

        if status is not None:
            progress.status = status
        if percentage is not None:
            progress.progress_percentage = max(0.0, min(100.0, percentage))
        if stage is not None:
            progress.current_stage = stage
            if stage not in progress.stages_completed:
                progress.stages_completed.append(stage)
        if upload_progress is not None:
            progress.upload_progress = max(0.0, min(100.0, upload_progress))
        if estimated_time_remaining is not None:
            progress.estimated_time_remaining = estimated_time_remaining
        if metadata is not None:
            progress.metadata.update(metadata)

        # Notify callbacks
        for cb in self._callbacks.get(task_id, []):
            try:
                cb(progress)
            except Exception:
                pass

        return progress

    def get(self, task_id: UUID) -> PublishingProgress | None:
        """Get current progress for a task.

        Args:
            task_id: The publishing task ID.

        Returns:
            Current ``PublishingProgress``, or ``None``.
        """
        return self._progress.get(task_id)

    def subscribe(self, task_id: UUID, callback: Callable[[PublishingProgress], None]) -> None:
        """Subscribe to progress updates for a task.

        Args:
            task_id: The publishing task ID.
            callback: Called with updated progress.
        """
        if task_id not in self._callbacks:
            self._callbacks[task_id] = []
        self._callbacks[task_id].append(callback)

    def unsubscribe(self, task_id: UUID, callback: Callable[[PublishingProgress], None]) -> None:
        """Unsubscribe from progress updates."""
        if task_id in self._callbacks:
            try:
                self._callbacks[task_id].remove(callback)
            except ValueError:
                pass

    def remove(self, task_id: UUID) -> None:
        """Remove progress tracking for a task."""
        self._progress.pop(task_id, None)
        self._callbacks.pop(task_id, None)

    @property
    def active_tasks(self) -> int:
        """Number of tasks being tracked."""
        return len(self._progress)

    def get_all_progress(self) -> dict[str, PublishingProgress]:
        """Get progress for all tracked tasks.

        Returns:
            Dict mapping task ID string to progress.
        """
        return {str(tid): p for tid, p in self._progress.items()}
