"""Continuity Agent — ensures visual consistency across all scenes.

Eighth agent in the storyboard workflow.  Takes all scenes, visual
plans, and camera plans to check consistency of characters, colors,
objects, visual style, camera style, aspect ratio, lighting,
transitions, and brand style.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import CONTINUITY_PROMPT
from src.ai.agents.storyboard.schema import (
    CameraPlanResult,
    ContinuityResult,
    SceneSegmentationResult,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ContinuityAgent(BaseAgent):
    """Ensures visual consistency across all scenes.

    Tracks:
    - Characters
    - Colors
    - Objects
    - Visual style
    - Camera style
    - Aspect ratio
    - Lighting
    - Transitions
    - Brand style
    """

    def __init__(self) -> None:
        super().__init__(
            name="continuity",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SCENE_PLANNER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {"required_fields": ["consistency_score"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        scenes_data = context.state.storyboard.metadata.get("scenes", {})
        scenes = SceneSegmentationResult.model_validate(scenes_data) if scenes_data else SceneSegmentationResult()

        vp_data = context.state.storyboard.metadata.get("visual_plans", {})
        visual_plans = VisualStoryboardResult.model_validate(vp_data) if vp_data else VisualStoryboardResult()

        cp_data = context.state.storyboard.metadata.get("camera_plans", {})
        camera_plans = CameraPlanResult.model_validate(cp_data) if cp_data else CameraPlanResult()

        scenes_text = "\n".join(f"[{s.scene_id}] {s.title} ({s.scene_type})" for s in scenes.scenes)
        vp_text = "\n".join(f"[{p.scene_id}] mood={p.mood}, colors={p.color_palette}, style={p.visual_style}" for p in visual_plans.visual_plans)
        cp_text = "\n".join(f"[{p.scene_id}] {p.camera_angle} / {p.movement}" for p in camera_plans.camera_plans)

        return CONTINUITY_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "brand_style": sp.narrative_strategy.tone,
            "scenes": scenes_text or "No scenes available.",
            "visual_plans": vp_text or "No visual plans available.",
            "camera_plans": cp_text or "No camera plans available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return ContinuityResult(
            character_consistency=data.get("character_consistency", ""),
            color_consistency=data.get("color_consistency", ""),
            object_consistency=data.get("object_consistency", ""),
            visual_style_consistency=data.get("visual_style_consistency", ""),
            camera_style_consistency=data.get("camera_style_consistency", ""),
            aspect_ratio=data.get("aspect_ratio", "16:9"),
            lighting_consistency=data.get("lighting_consistency", ""),
            transition_consistency=data.get("transition_consistency", ""),
            brand_style=data.get("brand_style", ""),
            issues=data.get("issues", []),
            consistency_score=data.get("consistency_score", 0.0),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, ContinuityResult):
            context.state.storyboard.metadata["continuity"] = result.model_dump()
