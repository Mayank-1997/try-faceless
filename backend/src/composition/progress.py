"""Progress Tracking.

Exposes rendering progress for REST, WebSockets, and future SSE.

Supports:
- Timeline compilation progress
- Rendering progress
- Encoding progress
- Optimization progress
- Validation progress
- Completion
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from src.composition.schema import RenderProgress, RenderStatus
from src.core.logging import get_logger


class ProgressTracker:
    """Tracks and exposes rendering progress.

    Maintains progress state for each render job and provides
    callbacks for real-time updates via WebSockets or SSE.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._progress: dict[UUID, RenderProgress] = {}
        self._callbacks: dict[UUID, list[Callable[[RenderProgress], None]]] = {}

    def register(self, job_id: UUID) -> RenderProgress:
        """Register a new job for progress tracking.

        Args:
            job_id: The render job ID.

        Returns:
            Initial ``RenderProgress``.
        """
        progress = RenderProgress(job_id=job_id)
        self._progress[job_id] = progress
        self._logger.info("progress_registered", job_id=str(job_id))
        return progress

    def update(
        self,
        job_id: UUID,
        *,
        status: RenderStatus | None = None,
        percentage: float | None = None,
        stage: str | None = None,
        frames_processed: int | None = None,
        total_frames: int | None = None,
        estimated_time_remaining: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RenderProgress:
        """Update progress for a job.

        Args:
            job_id: The render job ID.
            status: New status.
            percentage: Progress percentage (0-100).
            stage: Current stage name.
            frames_processed: Frames processed so far.
            total_frames: Total frames to process.
            estimated_time_remaining: Estimated seconds remaining.
            metadata: Additional metadata.

        Returns:
            Updated ``RenderProgress``.
        """
        if job_id not in self._progress:
            self.register(job_id)

        progress = self._progress[job_id]

        if status is not None:
            progress.status = status
        if percentage is not None:
            progress.progress_percentage = max(0.0, min(100.0, percentage))
        if stage is not None:
            progress.current_stage = stage
            if stage not in progress.stages_completed:
                progress.stages_completed.append(stage)
        if frames_processed is not None:
            progress.frames_processed = frames_processed
        if total_frames is not None:
            progress.total_frames = total_frames
        if estimated_time_remaining is not None:
            progress.estimated_time_remaining = estimated_time_remaining
        if metadata is not None:
            progress.metadata.update(metadata)

        # Notify callbacks
        for cb in self._callbacks.get(job_id, []):
            try:
                cb(progress)
            except Exception:
                pass

        return progress

    def get(self, job_id: UUID) -> RenderProgress | None:
        """Get current progress for a job.

        Args:
            job_id: The render job ID.

        Returns:
            Current ``RenderProgress``, or ``None``.
        """
        return self._progress.get(job_id)

    def subscribe(self, job_id: UUID, callback: Callable[[RenderProgress], None]) -> None:
        """Subscribe to progress updates for a job.

        Args:
            job_id: The render job ID.
            callback: Called with updated progress.
        """
        if job_id not in self._callbacks:
            self._callbacks[job_id] = []
        self._callbacks[job_id].append(callback)

    def unsubscribe(self, job_id: UUID, callback: Callable[[RenderProgress], None]) -> None:
        """Unsubscribe from progress updates."""
        if job_id in self._callbacks:
            try:
                self._callbacks[job_id].remove(callback)
            except ValueError:
                pass

    def remove(self, job_id: UUID) -> None:
        """Remove progress tracking for a job."""
        self._progress.pop(job_id, None)
        self._callbacks.pop(job_id, None)

    @property
    def active_jobs(self) -> int:
        """Number of jobs being tracked."""
        return len(self._progress)

    def get_all_progress(self) -> dict[str, RenderProgress]:
        """Get progress for all tracked jobs.

        Returns:
            Dict mapping job ID string to progress.
        """
        return {str(jid): p for jid, p in self._progress.items()}
