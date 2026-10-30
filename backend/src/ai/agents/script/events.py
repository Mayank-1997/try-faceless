"""Script generation event types for the script workflow.

Extends the agent event framework with script-specific events:
- ScriptStarted
- NarrativeStrategySelected
- OutlineGenerated
- HookSelected
- SectionsGenerated
- TransitionsGenerated
- CTAGenerated
- ScriptReviewed
- ScriptOptimized
- ScriptCompleted
"""

from __future__ import annotations

from uuid import UUID

from src.ai.agents.events import AgentEventEmitter


class ScriptEvents:
    """Constants for script event types."""

    SCRIPT_STARTED = "ScriptStarted"
    NARRATIVE_STRATEGY_SELECTED = "NarrativeStrategySelected"
    OUTLINE_GENERATED = "OutlineGenerated"
    HOOK_SELECTED = "HookSelected"
    SECTIONS_GENERATED = "SectionsGenerated"
    TRANSITIONS_GENERATED = "TransitionsGenerated"
    CTA_GENERATED = "CTAGenerated"
    SCRIPT_REVIEWED = "ScriptReviewed"
    SCRIPT_OPTIMIZED = "ScriptOptimized"
    SCRIPT_COMPLETED = "ScriptCompleted"


class ScriptEventEmitter(AgentEventEmitter):
    """Event emitter for script-specific events.

    Extends ``AgentEventEmitter`` with script workflow events.
    """

    async def emit_script_started(
        self,
        topic: str,
        execution_id: UUID,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.SCRIPT_STARTED,
            {"topic": topic, "execution_id": str(execution_id)},
            correlation_id=correlation_id,
            source="script_workflow",
        )

    async def emit_narrative_strategy_selected(
        self,
        style: str,
        rationale: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.NARRATIVE_STRATEGY_SELECTED,
            {"style": style, "rationale": rationale},
            correlation_id=correlation_id,
            source="script.narrative_strategy",
        )

    async def emit_outline_generated(
        self,
        section_count: int,
        total_time_seconds: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.OUTLINE_GENERATED,
            {"section_count": section_count, "total_time_seconds": total_time_seconds},
            correlation_id=correlation_id,
            source="script.outline",
        )

    async def emit_hook_selected(
        self,
        hook_type: str,
        retention_score: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.HOOK_SELECTED,
            {"hook_type": hook_type, "retention_score": retention_score},
            correlation_id=correlation_id,
            source="script.hook_generator",
        )

    async def emit_sections_generated(
        self,
        section_count: int,
        total_word_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.SECTIONS_GENERATED,
            {"section_count": section_count, "total_word_count": total_word_count},
            correlation_id=correlation_id,
            source="script.section_writer",
        )

    async def emit_transitions_generated(
        self,
        transition_count: int,
        smoothness_score: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.TRANSITIONS_GENERATED,
            {"transition_count": transition_count, "smoothness_score": smoothness_score},
            correlation_id=correlation_id,
            source="script.transition",
        )

    async def emit_cta_generated(
        self,
        cta_count: int,
        primary_cta_type: str,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.CTA_GENERATED,
            {"cta_count": cta_count, "primary_cta_type": primary_cta_type},
            correlation_id=correlation_id,
            source="script.cta",
        )

    async def emit_script_reviewed(
        self,
        overall_score: float,
        passed: bool,
        issue_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.SCRIPT_REVIEWED,
            {"overall_score": overall_score, "passed": passed, "issue_count": issue_count},
            correlation_id=correlation_id,
            source="script.review",
        )

    async def emit_script_optimized(
        self,
        changes_count: int,
        engagement_score: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.SCRIPT_OPTIMIZED,
            {"changes_count": changes_count, "engagement_score": engagement_score},
            correlation_id=correlation_id,
            source="script.optimizer",
        )

    async def emit_script_completed(
        self,
        package_id: UUID,
        word_count: int,
        duration_seconds: int,
        quality_score: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            ScriptEvents.SCRIPT_COMPLETED,
            {
                "package_id": str(package_id),
                "word_count": word_count,
                "duration_seconds": duration_seconds,
                "quality_score": quality_score,
            },
            correlation_id=correlation_id,
            source="script.workflow",
        )
