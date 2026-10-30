"""Animation Planner Agent — plans animations for each scene.

Sixth agent in the storyboard workflow.  Takes scenes, visual plans,
and camera plans to produce animation plans with element animation,
text animation, camera motion, object motion, background motion,
timing, transitions, and scene effects.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import ANIMATION_PLANNER_PROMPT
from src.ai.agents.storyboard.schema import (
    AnimationPlan,
    AnimationPlanResult,
    CameraPlanResult,
    SceneSegmentationResult,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class AnimationPlannerAgent(BaseAgent):
    """Plans animations for each scene.

    Plans:
    - Element animation
    - Text animation
    - Camera motion
    - Object motion
    - Background motion
    - Timing
    - Entrance and exit transitions
    - Scene effects
    """

    def __init__(self) -> None:
        super().__init__(
            name="animation_planner",
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
        return {"required_fields": ["animation_plans"], "max_repair_attempts": 2}

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
        vp_text = "\n".join(f"[{p.scene_id}] {p.visual_description}" for p in visual_plans.visual_plans)
        cp_text = "\n".join(f"[{p.scene_id}] {p.camera_angle} / {p.movement}" for p in camera_plans.camera_plans)

        return ANIMATION_PLANNER_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "scenes": scenes_text or "No scenes available.",
            "visual_plans": vp_text or "No visual plans available.",
            "camera_plans": cp_text or "No camera plans available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        plans = [
            AnimationPlan(
                scene_id=p.get("scene_id", ""),
                element_animation=p.get("element_animation", ""),
                text_animation=p.get("text_animation", ""),
                camera_motion=p.get("camera_motion", ""),
                object_motion=p.get("object_motion", ""),
                background_motion=p.get("background_motion", ""),
                timing=p.get("timing", ""),
                entrance_transition=p.get("entrance_transition", ""),
                exit_transition=p.get("exit_transition", ""),
                scene_effects=p.get("scene_effects", []),
            )
            for p in data.get("animation_plans", [])
        ]
        return AnimationPlanResult(animation_plans=plans)

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, AnimationPlanResult):
            context.state.storyboard.metadata["animation_plans"] = result.model_dump()
