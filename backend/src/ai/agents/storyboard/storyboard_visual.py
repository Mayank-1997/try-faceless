"""Visual Storyboard Agent — generates detailed visual descriptions for each scene.

Fourth agent in the storyboard workflow.  Takes the segmented scenes
and produces visual plans with composition, foreground, background,
objects, characters, environment, mood, lighting, color palette,
depth, and visual style.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import VISUAL_STORYBOARD_PROMPT
from src.ai.agents.storyboard.schema import (
    SceneSegmentationResult,
    VisualPlan,
    VisualStoryboardResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class StoryboardAgent(BaseAgent):
    """Generates detailed visual descriptions for each scene.

    For every scene generates:
    - Visual description
    - Composition
    - Foreground and background
    - Objects and characters
    - Environment
    - Mood and lighting
    - Color palette
    - Depth and visual style
    """

    def __init__(self) -> None:
        super().__init__(
            name="visual_storyboard",
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
        return {"required_fields": ["visual_plans"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        scenes_data = context.state.storyboard.metadata.get("scenes", {})
        scenes = SceneSegmentationResult.model_validate(scenes_data) if scenes_data else SceneSegmentationResult()

        scenes_text = "\n".join(
            f"[{s.scene_id}] {s.title} ({s.scene_type}, {s.estimated_duration_seconds}s)\n{s.narration[:350]}"
            for s in scenes.scenes
        )

        return VISUAL_STORYBOARD_PROMPT, {
            "topic": sp.title or context.state.topic.expanded_topic,
            "narrative_style": sp.narrative_strategy.style,
            "visual_style": sp.narrative_strategy.tone,
            "scenes": scenes_text or "No scenes available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        plans = [
            VisualPlan(
                scene_id=p.get("scene_id", ""),
                visual_description=p.get("visual_description", ""),
                composition=p.get("composition", ""),
                foreground=p.get("foreground", ""),
                background=p.get("background", ""),
                objects=p.get("objects", []),
                characters=p.get("characters", []),
                environment=p.get("environment", ""),
                mood=p.get("mood", ""),
                lighting=p.get("lighting", ""),
                color_palette=p.get("color_palette", []),
                depth=p.get("depth", ""),
                visual_style=p.get("visual_style", ""),
            )
            for p in data.get("visual_plans", [])
        ]
        return VisualStoryboardResult(
            visual_plans=plans,
            shared_context=(data.get("shared_context") or "").strip(),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, VisualStoryboardResult):
            context.state.storyboard.metadata["visual_plans"] = result.model_dump()
