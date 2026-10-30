"""Workflow entity — tracks individual workflow executions for a project.

A project can have multiple workflow executions (e.g., re-runs after
editing). Each workflow tracks the current step, status, timing, and
checkpoint information for resumption.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import WorkflowStatus, WorkflowStep


class Workflow:
    """A single workflow execution for a project.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        version: Workflow version (incremented for re-runs).
        current_step: Current step in the pipeline.
        status: Execution lifecycle status.
        started_at: When execution began.
        completed_at: When execution finished (None if running).
        execution_time_seconds: Total wall-clock duration.
        failure_reason: Error message if failed.
        retry_count: Number of retry attempts.
        checkpoint_ref: Reference to checkpoint data for resumption.
        created_by: UUID of the user who triggered this workflow.
        updated_by: UUID of the last user who updated this workflow.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        version: int = 1,
        current_step: WorkflowStep = WorkflowStep.INITIALIZATION,
        status: WorkflowStatus = WorkflowStatus.PENDING,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        execution_time_seconds: float | None = None,
        failure_reason: str | None = None,
        retry_count: int = 0,
        checkpoint_ref: str | None = None,
        created_by: UUID | None = None,
        updated_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.version = version
        self.current_step = current_step
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.execution_time_seconds = execution_time_seconds
        self.failure_reason = failure_reason
        self.retry_count = retry_count
        self.checkpoint_ref = checkpoint_ref
        self.created_by = created_by
        self.updated_by = updated_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def start(self) -> None:
        """Mark the workflow as running."""
        self.status = WorkflowStatus.RUNNING
        self.started_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    def advance_to(self, step: WorkflowStep) -> None:
        """Advance the workflow to the next step."""
        self.current_step = step
        self.updated_at = datetime.now(dt_timezone.utc)

    def complete(self) -> None:
        """Mark the workflow as completed."""
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = datetime.now(dt_timezone.utc)
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.execution_time_seconds = delta.total_seconds()
        self.updated_at = datetime.now(dt_timezone.utc)

    def fail(self, reason: str) -> None:
        """Mark the workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.failure_reason = reason
        self.completed_at = datetime.now(dt_timezone.utc)
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.execution_time_seconds = delta.total_seconds()
        self.updated_at = datetime.now(dt_timezone.utc)

    def cancel(self) -> None:
        """Cancel the workflow."""
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)

    def pause(self) -> None:
        """Pause the workflow."""
        self.status = WorkflowStatus.PAUSED
        self.updated_at = datetime.now(dt_timezone.utc)

    def resume(self) -> None:
        """Resume a paused workflow."""
        self.status = WorkflowStatus.RUNNING
        self.updated_at = datetime.now(dt_timezone.utc)

    def retry(self) -> None:
        """Increment retry count and reset to running."""
        self.retry_count += 1
        self.status = WorkflowStatus.RUNNING
        self.failure_reason = None
        self.updated_at = datetime.now(dt_timezone.utc)

    def save_checkpoint(self, ref: str) -> None:
        """Save a checkpoint reference for resumption."""
        self.checkpoint_ref = ref
        self.updated_at = datetime.now(dt_timezone.utc)

    @property
    def is_active(self) -> bool:
        """Check if the workflow is currently active."""
        return self.status in (WorkflowStatus.PENDING, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "version": self.version,
            "current_step": self.current_step.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_time_seconds": self.execution_time_seconds,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
            "checkpoint_ref": self.checkpoint_ref,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
