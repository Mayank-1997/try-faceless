"""Story Beat Agent — converts script into story beats.

Second agent in the storyboard workflow.  Takes the story analysis
and script to produce structured story beats (introduction, conflict,
explanation, reveal, transition, conclusion).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.script.schema import ScriptPackage
from src.ai.agents.storyboard.prompts import STORY_BEAT_PROMPT
from src.ai.agents.storyboard.schema import StoryAnalysis, StoryBeat, StoryBeatResult
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class StoryBeatAgent(BaseAgent):
    """Converts the script into story beats.

    Each beat contains:
    - Beat type (introduction, conflict, explanation, reveal, transition, conclusion)
    - Purpose
    - Emotion
    - Duration
    - Importance
    """

    def __init__(self) -> None:
        super().__init__(
            name="story_beat",
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
        return {"required_fields": ["beats"], "max_repair_attempts": 2}

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        sp_data = context.state.script.metadata.get("script_package", {})
        sp = ScriptPackage.model_validate(sp_data) if sp_data else ScriptPackage()

        sa_data = context.state.storyboard.metadata.get("story_analysis", {})
        analysis = StoryAnalysis.model_validate(sa_data) if sa_data else StoryAnalysis()

        analysis_text = f"Flow: {analysis.narrative_flow}\nPeaks: {', '.join(analysis.emotional_peaks)}\nPacing: {analysis.pacing}"

        return STORY_BEAT_PROMPT, {
            "script_title": sp.title,
            "narrative_style": sp.narrative_strategy.style,
            "full_script": sp.full_script or "No script available.",
            "story_analysis": analysis_text,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        beats = [
            StoryBeat(
                beat_type=b.get("beat_type", ""),
                purpose=b.get("purpose", ""),
                emotion=b.get("emotion", ""),
                duration_seconds=b.get("duration_seconds", 0),
                importance=b.get("importance", "medium"),
                description=b.get("description", ""),
            )
            for b in data.get("beats", [])
        ]
        return StoryBeatResult(beats=beats, total_beats=len(beats))

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, StoryBeatResult):
            context.state.storyboard.metadata["story_beats"] = result.model_dump()
            context.state.storyboard.beats = [b.description for b in result.beats]
            context.state.storyboard.act_count = len(result.beats)
