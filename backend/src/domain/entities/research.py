"""Research entity — versioned research data for a project.

Each research version captures the full research output: summary,
sources, keywords, statistics, audience pain points, and references.
Older versions are superseded when a new version is created.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import ResearchStatus


class Research:
    """A versioned research entry for a project.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        workflow_id: UUID of the workflow that produced this research.
        summary: High-level research summary.
        timeline: Chronological timeline of key events.
        interesting_facts: List of noteworthy facts.
        sources: List of source URLs or references.
        keywords: SEO/content keywords.
        references: Academic or formal references.
        statistics: Quantitative data points.
        audience_pain_points: Identified audience pain points.
        version: Version number (incremented for each new version).
        status: Research lifecycle status.
        created_by: UUID of the user or agent that created this research.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        workflow_id: UUID | None = None,
        summary: str = "",
        timeline: list[str] | None = None,
        interesting_facts: list[str] | None = None,
        sources: list[str] | None = None,
        keywords: list[str] | None = None,
        references: list[str] | None = None,
        statistics: dict[str, Any] | None = None,
        audience_pain_points: list[str] | None = None,
        version: int = 1,
        status: ResearchStatus = ResearchStatus.DRAFT,
        created_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.workflow_id = workflow_id
        self.summary = summary
        self.timeline = timeline or []
        self.interesting_facts = interesting_facts or []
        self.sources = sources or []
        self.keywords = keywords or []
        self.references = references or []
        self.statistics = statistics or {}
        self.audience_pain_points = audience_pain_points or []
        self.version = version
        self.status = status
        self.created_by = created_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def mark_completed(self) -> None:
        """Mark this research version as completed."""
        self.status = ResearchStatus.COMPLETED
        self.updated_at = datetime.now(dt_timezone.utc)

    def supersede(self) -> None:
        """Mark this research version as superseded by a newer version."""
        self.status = ResearchStatus.SUPERSEDED
        self.updated_at = datetime.now(dt_timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "summary": self.summary,
            "timeline": self.timeline,
            "interesting_facts": self.interesting_facts,
            "sources": self.sources,
            "keywords": self.keywords,
            "references": self.references,
            "statistics": self.statistics,
            "audience_pain_points": self.audience_pain_points,
            "version": self.version,
            "status": self.status.value,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
