"""Storyboard entity — versioned storyboard for a project.

The storyboard represents the high-level narrative structure,
including scene count, estimated duration, and visual style.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import StoryboardStatus, VideoStyle


class Storyboard:
    """A versioned storyboard for a project.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        workflow_id: UUID of the workflow that produced this storyboard.
        version: Storyboard version number.
        scene_count: Number of scenes planned.
        estimated_duration_seconds: Estimated total duration.
        style: Visual style for the storyboard.
        status: Storyboard lifecycle status.
        narrative_structure: Description of narrative arc.
        pacing_notes: Notes on pacing and rhythm.
        created_by: UUID of the user or agent that created this storyboard.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        version: int = 1,
        scene_count: int = 0,
        estimated_duration_seconds: int = 0,
        style: VideoStyle = VideoStyle.MIXED,
        status: StoryboardStatus = StoryboardStatus.DRAFT,
        narrative_structure: str = "",
        pacing_notes: str = "",
        package_json: str = "",
        created_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.version = version
        self.scene_count = scene_count
        self.estimated_duration_seconds = estimated_duration_seconds
        self.style = style
        self.status = status
        self.narrative_structure = narrative_structure
        self.pacing_notes = pacing_notes
        self.package_json = package_json
        self.created_by = created_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def approve(self) -> None:
        """Mark this storyboard version as approved."""
        self.status = StoryboardStatus.APPROVED
        self.updated_at = datetime.now(dt_timezone.utc)

    def reject(self) -> None:
        """Mark this storyboard version as rejected."""
        self.status = StoryboardStatus.REJECTED
        self.updated_at = datetime.now(dt_timezone.utc)

    def supersede(self) -> None:
        """Mark this storyboard version as superseded."""
        self.status = StoryboardStatus.SUPERSEDED
        self.updated_at = datetime.now(dt_timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "version": self.version,
            "scene_count": self.scene_count,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "style": self.style.value,
            "status": self.status.value,
            "narrative_structure": self.narrative_structure,
            "pacing_notes": self.pacing_notes,
            "package_json": self.package_json,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
