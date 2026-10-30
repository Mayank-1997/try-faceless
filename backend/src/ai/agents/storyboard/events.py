"""Storyboard event types for the storyboard & scene planning workflow.

Extends the agent event framework with storyboard-specific events:
- StoryboardStarted
- StoryAnalyzed
- BeatsGenerated
- ScenesPlanned
- VisualStoryboardGenerated
- CameraPlanned
- AnimationPlanned
- AssetDecisionCompleted
- ContinuityValidated
- StoryboardReviewed
- StoryboardCompleted
"""

from __future__ import annotations

from uuid import UUID

from src.ai.agents.events import AgentEventEmitter


class StoryboardEvents:
    """Constants for storyboard event types."""

    STORYBOARD_STARTED = "StoryboardStarted"
    STORY_ANALYZED = "StoryAnalyzed"
    BEATS_GENERATED = "BeatsGenerated"
    SCENES_PLANNED = "ScenesPlanned"
    VISUAL_STORYBOARD_GENERATED = "VisualStoryboardGenerated"
    CAMERA_PLANNED = "CameraPlanned"
    ANIMATION_PLANNED = "AnimationPlanned"
    ASSET_DECISION_COMPLETED = "AssetDecisionCompleted"
    CONTINUITY_VALIDATED = "ContinuityValidated"
    STORYBOARD_REVIEWED = "StoryboardReviewed"
    STORYBOARD_COMPLETED = "StoryboardCompleted"


class StoryboardEventEmitter(AgentEventEmitter):
    """Event emitter for storyboard-specific events.

    Extends ``AgentEventEmitter`` with storyboard workflow events.
    """

    async def emit_storyboard_started(
        self,
        script_title: str,
        execution_id: UUID,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.STORYBOARD_STARTED,
            {"script_title": script_title, "execution_id": str(execution_id)},
            correlation_id=correlation_id,
            source="storyboard_workflow",
        )

    async def emit_story_analyzed(
        self,
        emotional_peak_count: int,
        visual_opportunity_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.STORY_ANALYZED,
            {"emotional_peak_count": emotional_peak_count, "visual_opportunity_count": visual_opportunity_count},
            correlation_id=correlation_id,
            source="storyboard.story_analyzer",
        )

    async def emit_beats_generated(
        self,
        beat_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.BEATS_GENERATED,
            {"beat_count": beat_count},
            correlation_id=correlation_id,
            source="storyboard.story_beat",
        )

    async def emit_scenes_planned(
        self,
        scene_count: int,
        total_duration_seconds: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.SCENES_PLANNED,
            {"scene_count": scene_count, "total_duration_seconds": total_duration_seconds},
            correlation_id=correlation_id,
            source="storyboard.scene_segmentation",
        )

    async def emit_visual_storyboard_generated(
        self,
        plan_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.VISUAL_STORYBOARD_GENERATED,
            {"plan_count": plan_count},
            correlation_id=correlation_id,
            source="storyboard.visual",
        )

    async def emit_camera_planned(
        self,
        plan_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.CAMERA_PLANNED,
            {"plan_count": plan_count},
            correlation_id=correlation_id,
            source="storyboard.camera",
        )

    async def emit_animation_planned(
        self,
        plan_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.ANIMATION_PLANNED,
            {"plan_count": plan_count},
            correlation_id=correlation_id,
            source="storyboard.animation",
        )

    async def emit_asset_decision_completed(
        self,
        decision_count: int,
        total_estimated_cost: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.ASSET_DECISION_COMPLETED,
            {"decision_count": decision_count, "total_estimated_cost": total_estimated_cost},
            correlation_id=correlation_id,
            source="storyboard.asset_decision",
        )

    async def emit_continuity_validated(
        self,
        consistency_score: float,
        issue_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.CONTINUITY_VALIDATED,
            {"consistency_score": consistency_score, "issue_count": issue_count},
            correlation_id=correlation_id,
            source="storyboard.continuity",
        )

    async def emit_storyboard_reviewed(
        self,
        overall_score: float,
        passed: bool,
        issue_count: int,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.STORYBOARD_REVIEWED,
            {"overall_score": overall_score, "passed": passed, "issue_count": issue_count},
            correlation_id=correlation_id,
            source="storyboard.review",
        )

    async def emit_storyboard_completed(
        self,
        package_id: UUID,
        scene_count: int,
        estimated_budget: float,
        quality_score: float,
        *,
        correlation_id: str | None = None,
    ) -> None:
        await self.emit(
            StoryboardEvents.STORYBOARD_COMPLETED,
            {
                "package_id": str(package_id),
                "scene_count": scene_count,
                "estimated_budget": estimated_budget,
                "quality_score": quality_score,
            },
            correlation_id=correlation_id,
            source="storyboard.workflow",
        )
