"""Research-specific event types for the research workflow.

Extends the agent event framework with research-specific events:
- ResearchStarted
- TopicAnalyzed
- ResearchPlanned
- ResearchCompleted
- FactVerified
- KeywordsGenerated
- AudienceIdentified
- ContentAngleSelected
- ResearchPackageCreated
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.ai.agents.events import AgentEventEmitter


class ResearchEvents:
    """Constants for research event types."""

    RESEARCH_STARTED = "ResearchStarted"
    TOPIC_ANALYZED = "TopicAnalyzed"
    RESEARCH_PLANNED = "ResearchPlanned"
    RESEARCH_COMPLETED = "ResearchCompleted"
    FACT_VERIFIED = "FactVerified"
    KEYWORDS_GENERATED = "KeywordsGenerated"
    AUDIENCE_IDENTIFIED = "AudienceIdentified"
    CONTENT_ANGLE_SELECTED = "ContentAngleSelected"
    RESEARCH_PACKAGE_CREATED = "ResearchPackageCreated"


class ResearchEventEmitter(AgentEventEmitter):
    """Event emitter for research-specific events.

    Extends ``AgentEventEmitter`` with research workflow events.
    """

    async def emit_research_started(
        self,
        topic: str,
        execution_id: UUID,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.RESEARCH_STARTED,
            {"topic": topic, "execution_id": str(execution_id)},
            correlation_id=correlation_id,
            source="research_workflow",
        )

    async def emit_topic_analyzed(
        self,
        topic: str,
        category: str,
        difficulty: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.TOPIC_ANALYZED,
            {"topic": topic, "category": category, "difficulty": difficulty},
            correlation_id=correlation_id,
            source="research.topic_analyzer",
        )

    async def emit_research_planned(
        self,
        total_queries: int,
        sections: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.RESEARCH_PLANNED,
            {"total_queries": total_queries, "sections": sections},
            correlation_id=correlation_id,
            source="research.research_planner",
        )

    async def emit_research_completed(
        self,
        total_results: int,
        facts_gathered: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.RESEARCH_COMPLETED,
            {"total_results": total_results, "facts_gathered": facts_gathered},
            correlation_id=correlation_id,
            source="research.research_agent",
        )

    async def emit_fact_verified(
        self,
        total_checked: int,
        total_verified: int,
        overall_confidence: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.FACT_VERIFIED,
            {
                "total_checked": total_checked,
                "total_verified": total_verified,
                "overall_confidence": overall_confidence,
            },
            correlation_id=correlation_id,
            source="research.fact_verification",
        )

    async def emit_keywords_generated(
        self,
        primary_count: int,
        total_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.KEYWORDS_GENERATED,
            {"primary_count": primary_count, "total_count": total_count},
            correlation_id=correlation_id,
            source="research.keyword_extraction",
        )

    async def emit_audience_identified(
        self,
        persona_name: str,
        knowledge_level: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.AUDIENCE_IDENTIFIED,
            {"persona_name": persona_name, "knowledge_level": knowledge_level},
            correlation_id=correlation_id,
            source="research.audience_analysis",
        )

    async def emit_content_angle_selected(
        self,
        angle_type: str,
        title: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.CONTENT_ANGLE_SELECTED,
            {"angle_type": angle_type, "title": title},
            correlation_id=correlation_id,
            source="research.content_angle",
        )

    async def emit_research_package_created(
        self,
        package_id: UUID,
        confidence_score: float,
        total_facts: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ResearchEvents.RESEARCH_PACKAGE_CREATED,
            {
                "package_id": str(package_id),
                "confidence_score": confidence_score,
                "total_facts": total_facts,
            },
            correlation_id=correlation_id,
            source="research.summary",
        )
