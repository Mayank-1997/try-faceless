"""Script entity — versioned script content for a project.

Scripts are stored separately from research and support versioning.
Each version captures the hook, body, CTA, word count, estimated
duration, and language.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import ScriptStatus


class Script:
    """A versioned script for a project.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        workflow_id: UUID of the workflow that produced this script.
        hook: Opening hook to grab attention.
        body: Main script body.
        cta: Call-to-action at the end.
        word_count: Total word count.
        estimated_duration_seconds: Estimated narration duration.
        version: Version number.
        language: ISO 639-1 language code.
        status: Script lifecycle status.
        created_by: UUID of the user or agent that created this script.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        hook: str = "",
        body: str = "",
        cta: str = "",
        word_count: int = 0,
        estimated_duration_seconds: int = 0,
        version: int = 1,
        language: str = "en",
        status: ScriptStatus = ScriptStatus.DRAFT,
        created_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.hook = hook
        self.body = body
        self.cta = cta
        self.word_count = word_count
        self.estimated_duration_seconds = estimated_duration_seconds
        self.version = version
        self.language = language
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def approve(self) -> None:
        """Mark this script version as approved."""
        self.status = ScriptStatus.APPROVED
        self.updated_at = datetime.now(dt_timezone.utc)

    def reject(self) -> None:
        """Mark this script version as rejected."""
        self.status = ScriptStatus.REJECTED
        self.updated_at = datetime.now(dt_timezone.utc)

    def supersede(self) -> None:
        """Mark this script version as superseded."""
        self.status = ScriptStatus.SUPERSEDED
        self.updated_at = datetime.now(dt_timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "hook": self.hook,
            "body": self.body,
            "cta": self.cta,
            "word_count": self.word_count,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "version": self.version,
            "language": self.language,
            "status": self.status.value,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
