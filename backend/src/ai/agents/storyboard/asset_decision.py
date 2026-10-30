"""Asset Decision Agent — decides asset types for each scene.

Seventh agent in the storyboard workflow.  Takes scenes and visual
plans to decide the best asset type (AI image, AI video, stock,
diagram, chart, etc.), assign confidence scores, estimate costs,
and rendering complexity.
"""

from __future__ import annotations

import math
from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import ASSET_DECISION_PROMPT
from src.ai.agents.storyboard.schema import (
    AssetDecisionResult,
    AssetSceneDecision,
    SceneSegmentationResult,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies

# Asset types that never touch an image/video generation provider — the
# rendering pipeline draws these programmatically, so they cost nothing.
_ZERO_COST_ASSET_TYPES = frozenset({"diagram", "chart", "icon", "screenshot"})


def _veo_enabled() -> bool:
    """True when the pipeline will actually route scenes through Veo.

    Mirrors the ``veo_enabled`` check in
    ``workflow_tasks._create_step_output`` (ASSET_GENERATION step) so the
    cost estimate here matches what will really be billed.
    """
    try:
        from src.core.config import get_settings

        return bool(getattr(get_settings().veo, "enabled", False))
    except Exception:
        return False


def _real_generation_cost(asset_type: str, duration_seconds: float) -> float:
    """Estimate the real provider cost for a scene's asset.

    The LLM is unreliable at arithmetic (and has no knowledge of which
    provider is actually wired up), so the cost is computed deterministically
    here from the same pricing config and Veo clip-billing rules the
    ASSET_GENERATION step uses — the storyboard's estimated budget should
    match what actually gets billed, not a flat per-image guess.
    """
    from src.core.config import get_settings

    if (asset_type or "").lower() in _ZERO_COST_ASSET_TYPES:
        return 0.0

    settings = get_settings()
    if _veo_enabled():
        # Veo bills in 4/6/8s clips; a scene is covered by the smallest
        # even-second total >= its duration (same rule as
        # workflow_tasks._plan_veo_clip_durations).
        duration = max(float(duration_seconds or 0), 4.0)
        billed_seconds = 2 * math.ceil(duration / 2.0)
        return round(settings.cost.veo_per_second * billed_seconds, 4)

    return round(settings.cost.imagen_per_image, 4)


class AssetDecisionAgent(BaseAgent):
    """Decides the best asset type for each scene.

    For every scene decides:
    - Asset type (ai_video, ai_image, diagram, chart, icon, screenshot, animation_only, mixed_assets)
    - Confidence score
    - Estimated generation cost
    - Estimated rendering complexity
    - Rationale
    """

    def __init__(self) -> None:
        super().__init__(
            name="asset_decision",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.ASSET_DECISION

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {"required_fields": ["decisions"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        scenes_data = context.state.storyboard.metadata.get("scenes", {})
        scenes = SceneSegmentationResult.model_validate(scenes_data) if scenes_data else SceneSegmentationResult()

        vp_data = context.state.storyboard.metadata.get("visual_plans", {})
        visual_plans = VisualStoryboardResult.model_validate(vp_data) if vp_data else VisualStoryboardResult()

        scenes_text = "\n".join(
            f"[{s.scene_id}] {s.title} ({s.scene_type}, {s.estimated_duration_seconds}s)"
            for s in scenes.scenes
        )
        vp_text = "\n".join(f"[{p.scene_id}] {p.visual_description}" for p in visual_plans.visual_plans)

        # Cache scene durations so process_response can recompute real costs
        # without re-parsing storyboard metadata.
        context.state.storyboard.metadata["_asset_decision_scene_durations"] = {
            s.scene_id: s.estimated_duration_seconds for s in scenes.scenes
        }

        return ASSET_DECISION_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "scenes": scenes_text or "No scenes available.",
            "visual_plans": vp_text or "No visual plans available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        durations = context.state.storyboard.metadata.get("_asset_decision_scene_durations", {})
        # When the model omits asset_type, default to what the pipeline will
        # actually generate: ai_video when Veo is enabled, ai_image otherwise.
        default_type = "ai_video" if _veo_enabled() else "ai_image"
        decisions = [
            AssetSceneDecision(
                scene_id=d.get("scene_id", ""),
                asset_type=(d.get("asset_type") or default_type).lower(),
                confidence_score=d.get("confidence_score", 0.0),
                estimated_generation_cost=_real_generation_cost(
                    d.get("asset_type") or default_type,
                    durations.get(d.get("scene_id", ""), 4),
                ),
                estimated_rendering_complexity=d.get("estimated_rendering_complexity", "low"),
                rationale=d.get("rationale", ""),
            )
            for d in data.get("decisions", [])
        ]
        total_cost = sum(d.estimated_generation_cost for d in decisions)
        return AssetDecisionResult(decisions=decisions, total_estimated_cost=total_cost)

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, AssetDecisionResult):
            context.state.storyboard.metadata["asset_decisions"] = result.model_dump()
