"""Generation job entity — represents a background generation task.

Every generation task (research, script, scene, image, video, voice,
subtitle, rendering, SEO, publishing) is tracked as a job with status,
priority, retry logic, and result metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import JobPriority, JobStatus, JobType


class GenerationJob:
    """A background generation job.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        workflow_id: UUID of the workflow that queued this job.
        scene_id: UUID of the scene this job is for (optional).
        job_type: Type of generation job.
        status: Job lifecycle status.
        priority: Queue priority level.
        payload: Job-specific input data (JSON-serialisable).
        result: Job output data (JSON-serialisable).
        error_message: Error message if failed.
        retry_count: Number of retry attempts.
        max_retries: Maximum allowed retries.
        queued_at: When the job was queued.
        started_at: When execution began.
        completed_at: When execution finished.
        execution_time_seconds: Wall-clock execution duration.
        created_by: UUID of the user or agent that created this job.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        scene_id: UUID | None = None,
        job_type: JobType = JobType.RESEARCH,
        status: JobStatus = JobStatus.QUEUED,
        priority: JobPriority = JobPriority.NORMAL,
        payload: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
        max_retries: int = 3,
        queued_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        execution_time_seconds: float | None = None,
        created_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.scene_id = scene_id
        self.job_type = job_type
        self.status = status
        self.priority = priority
        self.payload = payload or {}
        self.result = result or {}
        self.error_message = error_message
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.queued_at = queued_at or datetime.now(dt_timezone.utc)
        self.started_at = started_at
        self.completed_at = completed_at
        self.execution_time_seconds = execution_time_seconds
        self.created_by = created_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def start(self) -> None:
        """Mark the job as running."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    def complete(self, result: dict[str, Any] | None = None) -> None:
        """Mark the job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.now(dt_timezone.utc)
        if result:
            self.result = result
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_seconds = delta.total_seconds()
        self.updated_at = datetime.now(dt_timezone.utc)

    def fail(self, error: str) -> None:
        """Mark the job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.now(dt_timezone.utc)
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_seconds = delta.total_seconds()
        self.updated_at = datetime.now(dt_timezone.utc)

    def retry(self) -> None:
        """Increment retry count and re-queue."""
        self.retry_count += 1
        self.status = JobStatus.RETRYING
        self.error_message = None
        self.updated_at = datetime.now(dt_timezone.utc)

    def cancel(self) -> None:
        """Cancel the job."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    @property
    def can_retry(self) -> bool:
        """Check if the job can be retried."""
        return self.retry_count < self.max_retries and self.status == JobStatus.FAILED

    @property
    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "scene_id": str(self.scene_id) if self.scene_id else None,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
