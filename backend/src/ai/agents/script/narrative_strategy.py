"""Narrative Strategy Agent — chooses the best storytelling approach.

First agent in the script workflow.  Takes the Research Package
and selects the best narrative style, flow, pacing, and tone
based on audience, topic, duration, and content type.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    ContentAngleResult,
    ResearchPackage,
    ResearchSummary,
    TopicAnalysis,
)
from src.ai.agents.script.prompts import NARRATIVE_STRATEGY_PROMPT
from src.ai.agents.script.schema import NarrativeStrategy
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class NarrativeStrategyAgent(BaseAgent):
    """Chooses the best narrative strategy for the script.

    Selects:
    - Storytelling style (educational, storytelling, documentary, etc.)
    - Narrative flow
    - Pacing (fast, moderate, slow, varied)
    - Tone (informative, casual, dramatic, humorous, inspirational)
    - Emotional arc
    - Key narrative beats
    """

    def __init__(self) -> None:
        super().__init__(
            name="narrative_strategy",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.SCRIPT_WRITER

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["style", "rationale", "flow"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        audience = rp.audience.primary_persona.persona_name or context.state.topic.target_audience
        content_angle = rp.content_angle.selected_angle.angle_type if rp.content_angle.selected_angle else ""

        return NARRATIVE_STRATEGY_PROMPT, {
            "topic": topic,
            "category": rp.topic_analysis.category,
            "content_type": rp.topic_analysis.content_type,
            "target_duration": (
                context.state.project.target_duration_seconds
                or rp.topic_analysis.target_duration_seconds
            ),
            "audience": audience,
            "content_angle": content_angle,
            "research_summary": rp.summary.overview or "No summary available.",
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return NarrativeStrategy(
            style=data.get("style", "educational"),
            rationale=data.get("rationale", ""),
            flow=data.get("flow", ""),
            pacing=data.get("pacing", "moderate"),
            tone=data.get("tone", "informative"),
            emotional_arc=data.get("emotional_arc", ""),
            key_beats=data.get("key_beats", []),
            audience_alignment=data.get("audience_alignment", ""),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, NarrativeStrategy):
            context.state.script.metadata["narrative_strategy"] = result.model_dump()
