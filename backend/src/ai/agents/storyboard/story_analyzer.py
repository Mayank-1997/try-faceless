"""Story Analyzer Agent — analyzes script narrative for visual storytelling.

First agent in the storyboard workflow.  Understands narrative flow,
identifies emotional peaks, pacing, scene boundaries, emphasis,
dramatic moments, and visual opportunities.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import STORY_ANALYZER_PROMPT
from src.ai.agents.storyboard.schema import StoryAnalysis
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class StoryAnalyzerAgent(BaseAgent):
    """Analyzes the script's narrative structure for visual storytelling.

    Identifies:
    - Narrative flow
    - Emotional peaks
    - Pacing
    - Scene boundaries
    - Emphasis points
    - Dramatic moments
    - Visual opportunities
    """

    def __init__(self) -> None:
        super().__init__(
            name="story_analyzer",
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
        return {"required_fields": ["narrative_flow"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        return STORY_ANALYZER_PROMPT, {
            "script_title": sp.title or context.state.script.title,
            "narrative_style": sp.narrative_strategy.style,
            "full_script": sp.full_script or context.state.script.content or "No script available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return StoryAnalysis(
            narrative_flow=data.get("narrative_flow", ""),
            emotional_peaks=data.get("emotional_peaks", []),
            pacing=data.get("pacing", "moderate"),
            scene_boundaries=data.get("scene_boundaries", []),
            emphasis_points=data.get("emphasis_points", []),
            dramatic_moments=data.get("dramatic_moments", []),
            visual_opportunities=data.get("visual_opportunities", []),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, StoryAnalysis):
            context.state.storyboard.metadata["story_analysis"] = result.model_dump()
            context.state.storyboard.pacing_notes = result.pacing
