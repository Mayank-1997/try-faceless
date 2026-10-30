"""Camera Planner Agent — plans camera angles and movements for each scene.

Fifth agent in the storyboard workflow.  Takes scenes and visual
plans to determine camera angle, distance, lens, movement,
motion speed, and focus point for each scene.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import CAMERA_PLANNER_PROMPT
from src.ai.agents.storyboard.schema import (
    CameraPlan,
    CameraPlanResult,
    SceneSegmentationResult,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class CameraPlannerAgent(BaseAgent):
    """Plans camera angles and movements for each scene.

    Determines:
    - Camera angle (wide, medium, close_up, etc.)
    - Camera distance
    - Lens type
    - Movement (static, pan, zoom, dolly, tilt, orbit, tracking)
    - Motion speed
    - Focus point
    """

    def __init__(self) -> None:
        super().__init__(
            name="camera_planner",
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
        return {"required_fields": ["camera_plans"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        scenes_data = context.state.storyboard.metadata.get("scenes", {})
        scenes = SceneSegmentationResult.model_validate(scenes_data) if scenes_data else SceneSegmentationResult()

        vp_data = context.state.storyboard.metadata.get("visual_plans", {})
        visual_plans = VisualStoryboardResult.model_validate(vp_data) if vp_data else VisualStoryboardResult()

        scenes_text = "\n".join(f"[{s.scene_id}] {s.title} ({s.scene_type})" for s in scenes.scenes)
        vp_text = "\n".join(f"[{p.scene_id}] {p.visual_description}" for p in visual_plans.visual_plans)

        return CAMERA_PLANNER_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "scenes": scenes_text or "No scenes available.",
            "visual_plans": vp_text or "No visual plans available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        plans = [
            CameraPlan(
                scene_id=p.get("scene_id", ""),
                camera_angle=p.get("camera_angle", ""),
                camera_distance=p.get("camera_distance", ""),
                lens=p.get("lens", ""),
                movement=p.get("movement", ""),
                motion_speed=p.get("motion_speed", "normal"),
                focus_point=p.get("focus_point", ""),
            )
            for p in data.get("camera_plans", [])
        ]
        return CameraPlanResult(camera_plans=plans)

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, CameraPlanResult):
            context.state.storyboard.metadata["camera_plans"] = result.model_dump()
