"""Project aggregate root — the central business entity.

Everything in the system belongs to a Project. A project represents
a single content creation effort (e.g., a YouTube video) and owns
all workflows, research, scripts, storyboards, scenes, assets, and jobs.

This is a pure domain entity with no ORM dependencies. Repositories
convert between this and the SQLAlchemy ORM model.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import ContentType, ProjectStatus, VideoStyle, WorkflowStep


class Project:
    """Project aggregate root.

    Encapsulates all metadata about a content creation project. The
    project lifecycle is tracked via ``status`` (high-level) and
    ``workflow_status`` (pipeline step).

    Attributes:
        id: UUID primary key.
        owner_id: UUID of the user who owns this project.
        title: Human-readable project title.
        description: Long-form description.
        language: ISO 639-1 language code (e.g., "en").
        audience: Target audience description.
        content_type: Type of content being produced.
        video_style: Visual style for video projects.
        target_duration_seconds: Desired final video length.
        status: High-level project lifecycle status.
        current_step: Current workflow step.
        tags: List of user-defined tags.
        metadata: Arbitrary key-value metadata.
        created_by: UUID of the user who created this project.
        updated_by: UUID of the last user who updated this project.
        deleted_by: UUID of the user who soft-deleted this project.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
        deleted_at: Soft-delete timestamp (None if active).
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        owner_id: UUID,
        title: str,
        description: str = "",
        language: str = "en",
        audience: str = "",
        content_type: ContentType = ContentType.YOUTUBE_VIDEO,
        video_style: VideoStyle = VideoStyle.MIXED,
        target_duration_seconds: int | None = None,
        status: ProjectStatus = ProjectStatus.DRAFT,
        current_step: WorkflowStep = WorkflowStep.INITIALIZATION,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: UUID | None = None,
        updated_by: UUID | None = None,
        deleted_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        deleted_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.owner_id = owner_id
        self.title = title
        self.description = description
        self.language = language
        self.audience = audience
        self.content_type = content_type
        self.video_style = video_style
        self.target_duration_seconds = target_duration_seconds
        self.status = status
        self.current_step = current_step
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_by = created_by
        self.updated_by = updated_by
        self.deleted_by = deleted_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)
        self.deleted_at = deleted_at

    def update_status(self, status: ProjectStatus) -> None:
        """Update the project's lifecycle status."""
        self.status = status
        self.updated_at = datetime.now(dt_timezone.utc)

    def update_step(self, step: WorkflowStep) -> None:
        """Update the current workflow step."""
        self.current_step = step
        self.updated_at = datetime.now(dt_timezone.utc)

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(dt_timezone.utc)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(dt_timezone.utc)

    def soft_delete(self, deleted_by: UUID) -> None:
        """Soft-delete the project."""
        self.deleted_at = datetime.now(dt_timezone.utc)
        self.deleted_by = deleted_by
        self.status = ProjectStatus.CANCELLED
        self.updated_at = datetime.now(dt_timezone.utc)

    def restore(self) -> None:
        """Restore a soft-deleted project."""
        self.deleted_at = None
        self.deleted_by = None
        self.updated_at = datetime.now(dt_timezone.utc)

    @property
    def is_deleted(self) -> bool:
        """Check if the project is soft-deleted."""
        return self.deleted_at is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "title": self.title,
            "description": self.description,
            "language": self.language,
            "audience": self.audience,
            "content_type": self.content_type.value,
            "video_style": self.video_style.value,
            "target_duration_seconds": self.target_duration_seconds,
            "status": self.status.value,
            "current_step": self.current_step.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_by": str(self.created_by) if self.created_by else None,
            "updated_by": str(self.updated_by) if self.updated_by else None,
            "deleted_by": str(self.deleted_by) if self.deleted_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
