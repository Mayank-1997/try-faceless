"""Publishing Queue.

Supports:
- Priority
- Retries
- Pause
- Resume
- Cancellation
- Scheduled publishing
- Future distributed workers
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.publishing.events import PublishingEventEmitter
from src.publishing.schema import PublishingJob, PublishingJobStatus, PublishingPriority
from src.core.logging import get_logger


class PublishingQueue:
    """Priority-based async publishing queue with retry support.

    Jobs are ordered by priority (lower value = higher priority).
    Failed jobs are retried up to ``max_retries`` times before being
    moved to a dead-letter list.
    """

    def __init__(self, event_emitter: PublishingEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or PublishingEventEmitter()
        self._queue: list[PublishingJob] = []
        self._active: dict[UUID, PublishingJob] = {}
        self._completed: list[PublishingJob] = []
        self._failed: list[PublishingJob] = []
        self._dead_letter: list[PublishingJob] = []
        self._paused: bool = False
        self._lock = asyncio.Lock()

    async def submit(self, job: PublishingJob) -> PublishingJob:
        """Submit a job to the queue.

        Args:
            job: The publishing job to submit.

        Returns:
            The submitted job.
        """
        job.status = PublishingJobStatus.QUEUED
        async with self._lock:
            self._queue.append(job)
            self._queue.sort(key=lambda j: j.priority.value)
        self._logger.info("job_submitted", job_id=str(job.id), priority=job.priority.name)
        return job

    async def dequeue(self) -> PublishingJob | None:
        """Dequeue the next job.

        Returns:
            The next job, or ``None`` if queue is empty or paused.
        """
        if self._paused:
            return None
        async with self._lock:
            if not self._queue:
                return None
            job = self._queue.pop(0)
            job.started_at = datetime.now(timezone.utc)
            self._active[job.id] = job
            return job

    async def complete(self, job_id: UUID) -> bool:
        """Mark a job as completed.

        Args:
            job_id: The job ID to complete.

        Returns:
            ``True`` if the job was found and completed.
        """
        async with self._lock:
            job = self._active.pop(job_id, None)
            if job is None:
                return False
            job.status = PublishingJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            self._completed.append(job)
            self._logger.info(
                "job_completed",
                job_id=str(job_id),
                execution_time=job.execution_time_seconds,
            )
            return True

    async def fail(self, job_id: UUID, error: str) -> bool:
        """Mark a job as failed and schedule retry if possible.

        Args:
            job_id: The job ID that failed.
            error: Error message.

        Returns:
            ``True`` if the job was found and handled.
        """
        async with self._lock:
            job = self._active.pop(job_id, None)
            if job is None:
                return False
            job.error = error

            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = PublishingJobStatus.RETRYING
                self._queue.append(job)
                self._queue.sort(key=lambda j: j.priority.value)
                self._logger.info(
                    "job_retry",
                    job_id=str(job_id),
                    retry=job.retry_count,
                    max=job.max_retries,
                )
                await self._events.emit_retry_triggered(job_id, job.retry_count, job.max_retries)
            else:
                job.status = PublishingJobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                self._dead_letter.append(job)
                self._logger.error("job_dead_lettered", job_id=str(job_id), error=error)
            return True

    async def cancel(self, job_id: UUID) -> bool:
        """Cancel a job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            ``True`` if the job was cancelled.
        """
        async with self._lock:
            # Check active
            job = self._active.pop(job_id, None)
            if job is not None:
                job.status = PublishingJobStatus.CANCELLED
                job.completed_at = datetime.now(timezone.utc)
                self._failed.append(job)
                return True

            # Check queue
            for i, j in enumerate(self._queue):
                if j.id == job_id:
                    j.status = PublishingJobStatus.CANCELLED
                    j.completed_at = datetime.now(timezone.utc)
                    self._failed.append(j)
                    self._queue.pop(i)
                    return True

            return False

    def pause(self) -> None:
        """Pause the queue."""
        self._paused = True
        self._logger.info("queue_paused")

    def resume(self) -> None:
        """Resume the queue."""
        self._paused = False
        self._logger.info("queue_resumed")

    @property
    def queue_size(self) -> int:
        """Number of jobs waiting in the queue."""
        return len(self._queue)

    @property
    def active_count(self) -> int:
        """Number of actively running jobs."""
        return len(self._active)

    @property
    def completed_count(self) -> int:
        """Number of completed jobs."""
        return len(self._completed)

    @property
    def failed_count(self) -> int:
        """Number of failed jobs."""
        return len(self._failed)

    @property
    def dead_letter_count(self) -> int:
        """Number of dead-lettered jobs."""
        return len(self._dead_letter)

    @property
    def is_paused(self) -> bool:
        """Whether the queue is paused."""
        return self._paused

    def get_job(self, job_id: UUID) -> PublishingJob | None:
        """Get a job by ID from any state."""
        for j in self._queue:
            if j.id == job_id:
                return j
        if job_id in self._active:
            return self._active[job_id]
        for j in self._completed:
            if j.id == job_id:
                return j
        for j in self._failed:
            if j.id == job_id:
                return j
        for j in self._dead_letter:
            if j.id == job_id:
                return j
        return None

    def get_dead_letter_jobs(self) -> list[PublishingJob]:
        """Get all dead-lettered jobs."""
        return list(self._dead_letter)

    def clear_completed(self) -> int:
        """Clear completed jobs.

        Returns:
            Number of jobs cleared.
        """
        count = len(self._completed)
        self._completed.clear()
        return count
