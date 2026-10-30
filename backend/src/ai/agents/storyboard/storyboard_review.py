"""Storyboard Review Agent — validates storyboard quality and assembles final package.

Ninth and final agent in the storyboard workflow.  Reviews the complete
storyboard for scene flow, visual variety, scene balance, narrative
consistency, camera variety, animation quality, budget efficiency,
and rendering feasibility.  Assembles the final ``StoryboardPackage``
with per-scene ``ScenePackage`` objects for downstream agents.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import STORYBOARD_REVIEW_PROMPT
from src.ai.agents.storyboard.schema import (
    AnimationPlan,
    AnimationPlanResult,
    AssetDecisionResult,
    CameraPlan,
    CameraPlanResult,
    ContinuityResult,
    ScenePackage,
    SceneSegmentationResult,
    StoryboardPackage,
    StoryboardQualityEvaluation,
    StoryboardReviewResult,
    VisualPlan,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class StoryboardReviewAgent(BaseAgent):
    """Reviews the complete storyboard and assembles the final package.

    Validates:
    - Scene flow
    - Visual variety
    - Scene duration
    - Continuity
    - Camera variety
    - Animation variety
    - Cost estimate
    - Rendering feasibility

    Assembles the final ``StoryboardPackage`` with per-scene packages.
    """

    def __init__(self) -> None:
        super().__init__(
            name="storyboard_review",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.STORY_PLANNER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {"required_fields": ["overall_score", "passed"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        meta = context.state.storyboard.metadata
        scenes = SceneSegmentationResult.model_validate(meta.get("scenes", {}))
        visual_plans = VisualStoryboardResult.model_validate(meta.get("visual_plans", {}))
        camera_plans = CameraPlanResult.model_validate(meta.get("camera_plans", {}))
        animation_plans = AnimationPlanResult.model_validate(meta.get("animation_plans", {}))
        asset_decisions = AssetDecisionResult.model_validate(meta.get("asset_decisions", {}))
        continuity = ContinuityResult.model_validate(meta.get("continuity", {}))

        scenes_text = "\n".join(f"[{s.scene_id}] {s.title} ({s.scene_type}, {s.estimated_duration_seconds}s)" for s in scenes.scenes)
        vp_text = "\n".join(f"[{p.scene_id}] {p.visual_description}" for p in visual_plans.visual_plans)
        cp_text = "\n".join(f"[{p.scene_id}] {p.camera_angle}/{p.movement}" for p in camera_plans.camera_plans)
        ap_text = "\n".join(f"[{p.scene_id}] {p.element_animation[:80]}" for p in animation_plans.animation_plans)
        ad_text = "\n".join(f"[{d.scene_id}] {d.asset_type} (${d.estimated_generation_cost:.2f})" for d in asset_decisions.decisions)
        cont_text = f"Score: {continuity.consistency_score:.2f}, Issues: {', '.join(continuity.issues[:3])}"

        return STORYBOARD_REVIEW_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "scene_count": scenes.total_scenes,
            "total_duration": scenes.total_duration_seconds,
            "estimated_budget": asset_decisions.total_estimated_cost,
            "scenes": scenes_text or "No scenes available.",
            "visual_plans": vp_text or "No visual plans available.",
            "camera_plans": cp_text or "No camera plans available.",
            "animation_plans": ap_text or "No animation plans available.",
            "asset_decisions": ad_text or "No asset decisions available.",
            "continuity": cont_text or "No continuity data available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return StoryboardReviewResult(
            scene_flow_score=data.get("scene_flow_score", 0.0),
            visual_variety_score=data.get("visual_variety_score", 0.0),
            scene_balance_score=data.get("scene_balance_score", 0.0),
            narrative_consistency_score=data.get("narrative_consistency_score", 0.0),
            camera_variety_score=data.get("camera_variety_score", 0.0),
            animation_quality_score=data.get("animation_quality_score", 0.0),
            budget_efficiency_score=data.get("budget_efficiency_score", 0.0),
            rendering_feasibility_score=data.get("rendering_feasibility_score", 0.0),
            overall_score=data.get("overall_score", 0.0),
            issues=data.get("issues", []),
            strengths=data.get("strengths", []),
            recommendations=data.get("recommendations", []),
            passed=data.get("passed", False),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if not isinstance(result, StoryboardReviewResult):
            return

        context.state.storyboard.metadata["review"] = result.model_dump()

        # Assemble the final StoryboardPackage
        package = self._assemble_package(context, result)
        context.state.storyboard.metadata["storyboard_package"] = package.model_dump()

        # Update top-level storyboard fields
        context.state.storyboard.narrative_structure = package.story_analysis.narrative_flow
        context.state.storyboard.act_count = package.story_beats.total_beats
        context.state.storyboard.beats = [b.description for b in package.story_beats.beats]

    def _assemble_package(
        self,
        context: AgentContext,
        review: StoryboardReviewResult,
    ) -> StoryboardPackage:
        """Assemble the final storyboard package from all agent outputs."""
        meta = context.state.storyboard.metadata

        from src.ai.agents.storyboard.schema import (
            StoryAnalysis,
            StoryBeatResult,
        )

        story_analysis = StoryAnalysis.model_validate(meta.get("story_analysis", {}))
        story_beats = StoryBeatResult.model_validate(meta.get("story_beats", {}))
        scenes = SceneSegmentationResult.model_validate(meta.get("scenes", {}))
        visual_plans = VisualStoryboardResult.model_validate(meta.get("visual_plans", {}))
        camera_plans = CameraPlanResult.model_validate(meta.get("camera_plans", {}))
        animation_plans = AnimationPlanResult.model_validate(meta.get("animation_plans", {}))
        asset_decisions = AssetDecisionResult.model_validate(meta.get("asset_decisions", {}))
        continuity = ContinuityResult.model_validate(meta.get("continuity", {}))

        # Build per-scene packages
        vp_map = {p.scene_id: p for p in visual_plans.visual_plans}
        cp_map = {p.scene_id: p for p in camera_plans.camera_plans}
        ap_map = {p.scene_id: p for p in animation_plans.animation_plans}
        ad_map = {d.scene_id: d for d in asset_decisions.decisions}

        scene_packages: list[ScenePackage] = []
        for scene in scenes.scenes:
            vp = vp_map.get(scene.scene_id)
            cp = cp_map.get(scene.scene_id)
            ap = ap_map.get(scene.scene_id)
            ad = ad_map.get(scene.scene_id)

            scene_packages.append(ScenePackage(
                scene_id=scene.scene_id,
                scene_number=scene.scene_number,
                title=scene.title,
                narration=scene.narration,
                duration_seconds=scene.estimated_duration_seconds,
                visual_prompt_summary=vp.visual_description if vp else "",
                asset_type=ad.asset_type if ad else "",
                camera_plan=cp or CameraPlan(),
                animation_plan=ap or AnimationPlan(),
                visual_plan=vp or VisualPlan(),
                transition=ap.entrance_transition if ap else "",
                priority=scene.metadata.get("priority", "medium"),
                dependencies=scene.metadata.get("dependencies", []),
                estimated_cost=ad.estimated_generation_cost if ad else 0.0,
                estimated_tokens=scene.metadata.get("estimated_tokens", 0),
                quality_score=review.overall_score,
            ))

        # Quality evaluation
        quality = StoryboardQualityEvaluation(
            visual_diversity=review.visual_variety_score,
            scene_balance=review.scene_balance_score,
            narrative_consistency=review.narrative_consistency_score,
            camera_variety=review.camera_variety_score,
            animation_quality=review.animation_quality_score,
            budget_efficiency=review.budget_efficiency_score,
            overall_production_score=review.overall_score,
        )

        # Estimate timeline (rough: 1 minute per scene + 30% overhead)
        timeline_minutes = int(scenes.total_scenes * 1.3)

        return StoryboardPackage(
            story_analysis=story_analysis,
            story_beats=story_beats,
            scenes=scenes,
            visual_plans=visual_plans,
            camera_plans=camera_plans,
            animation_plans=animation_plans,
            asset_decisions=asset_decisions,
            continuity=continuity,
            review=review,
            quality=quality,
            scene_packages=scene_packages,
            estimated_budget=asset_decisions.total_estimated_cost,
            estimated_timeline_minutes=timeline_minutes,
        )
