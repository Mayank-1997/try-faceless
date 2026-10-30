"""Queue Manager — priority-based async job queue for generation jobs.

Supports:
- Priority queue (jobs ordered by priority)
- Retry queue (failed jobs retried with backoff)
- Delayed queue (jobs scheduled for future execution)
- Cancellation queue (jobs marked for cancellation)
- Dead letter queue (permanently failed jobs)

Future: distributed workers via Redis/Celery.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.core.logging import get_logger
from src.generation.schema import GenerationJob, JobPriority, JobStatus


class QueueManager:
    """Manages generation job queues with priority ordering.

    Each asset becomes an independent queue job. Jobs are dequeued
    by priority (lower value = higher priority).
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._queue: list[GenerationJob] = []
        self._retry_queue: list[GenerationJob] = []
        self._dead_letter: list[GenerationJob] = []
        self._cancelled: set[Any] = set()  # set of job IDs
        self._paused: bool = False
        self._lock = asyncio.Lock()

    async def enqueue(self, job: GenerationJob) -> None:
        """Add a job to the priority queue.

        Args:
            job: The generation job to enqueue.
        """
        async with self._lock:
            self._queue.append(job)
            self._queue.sort(key=lambda j: (j.priority.value, j.created_at))
            self._logger.info("job_enqueued", job_id=str(job.id), priority=job.priority.name, queue_size=len(self._queue))

    async def dequeue(self) -> GenerationJob | None:
        """Dequeue the highest-priority job.

        Returns:
            The next job to process, or ``None`` if the queue is empty.
        """
        async with self._lock:
            if self._paused or not self._queue:
                return None

            # Skip cancelled jobs
            while self._queue:
                job = self._queue.pop(0)
                if job.id in self._cancelled:
                    job.status = JobStatus.CANCELLED
                    self._cancelled.discard(job.id)
                    continue
                return job
            return None

    async def cancel(self, job_id: Any) -> bool:
        """Cancel a queued or running job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            ``True`` if the job was marked for cancellation.
        """
        async with self._lock:
            self._cancelled.add(job_id)
            self._logger.info("job_cancelled", job_id=str(job_id))
            return True

    async def retry(self, job: GenerationJob, error: str) -> None:
        """Move a failed job to the retry queue.

        Args:
            job: The failed job.
            error: The error message.
        """
        async with self._lock:
            job.retry_count += 1
            job.error = error
            if job.retry_count >= job.max_retries:
                job.status = JobStatus.FAILED
                self._dead_letter.append(job)
                self._logger.warning("job_dead_lettered", job_id=str(job.id), retries=job.retry_count)
            else:
                job.status = JobStatus.RETRYING
                self._retry_queue.append(job)
                self._logger.info("job_retry_queued", job_id=str(job.id), retry_count=job.retry_count)

    async def move_retries_to_queue(self) -> int:
        """Move all retry queue jobs back to the main queue.

        Returns:
            Number of jobs moved.
        """
        async with self._lock:
            count = len(self._retry_queue)
            for job in self._retry_queue:
                job.status = JobStatus.QUEUED
                self._queue.append(job)
            self._retry_queue.clear()
            if count > 0:
                self._queue.sort(key=lambda j: (j.priority.value, j.created_at))
                self._logger.info("retries_moved_to_queue", count=count)
            return count

    async def dead_letter(self, job: GenerationJob) -> None:
        """Move a job to the dead letter queue.

        Args:
            job: The job to dead-letter.
        """
        async with self._lock:
            job.status = JobStatus.FAILED
            self._dead_letter.append(job)
            self._logger.warning("job_dead_lettered", job_id=str(job.id))

    @property
    def queue_size(self) -> int:
        """Number of jobs in the main queue."""
        return len(self._queue)

    @property
    def retry_queue_size(self) -> int:
        """Number of jobs in the retry queue."""
        return len(self._retry_queue)

    @property
    def dead_letter_size(self) -> int:
        """Number of jobs in the dead letter queue."""
        return len(self._dead_letter)

    @property
    def is_paused(self) -> bool:
        """Check if the queue is paused."""
        return self._paused

    async def pause(self) -> None:
        """Pause the queue (dequeue will return None)."""
        async with self._lock:
            self._paused = True
            self._logger.info("queue_paused")

    async def resume(self) -> None:
        """Resume the queue."""
        async with self._lock:
            self._paused = False
            self._logger.info("queue_resumed")

    def get_dead_letter_jobs(self) -> list[GenerationJob]:
        """Return all dead-lettered jobs."""
        return list(self._dead_letter)

    def clear(self) -> None:
        """Clear all queues (primarily for testing)."""
        self._queue.clear()
        self._retry_queue.clear()
        self._dead_letter.clear()
        self._cancelled.clear()
        self._paused = False
