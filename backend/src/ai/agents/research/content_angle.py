"""Content Angle Agent — generates and selects the best content angle.

Seventh agent in the research workflow.  Generates multiple content
angles (educational, storytelling, comparison, timeline, explainer,
case study, opinion), evaluates them, and selects the best one.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import CONTENT_ANGLE_PROMPT
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    ContentAngle,
    ContentAngleResult,
    TopicAnalysis,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ContentAngleAgent(BaseAgent):
    """Generates and selects the best content angle.

    Generates multiple angles covering:
    - Educational
    - Storytelling
    - Comparison
    - Timeline
    - Explainer
    - Case Study
    - Opinion

    Selects the best angle based on engagement potential, audience
    fit, and production difficulty.
    """

    def __init__(self) -> None:
        super().__init__(
            name="content_angle",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.RESEARCH

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["angles", "selected_angle"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic_data = context.state.research.metadata.get("topic_analysis", {})
        topic_analysis = TopicAnalysis.model_validate(topic_data) if topic_data else TopicAnalysis()
        topic = topic_analysis.expanded_topic or context.state.topic.expanded_topic

        audience_data = context.state.research.metadata.get("audience", {})
        audience_result = AudienceAnalysisResult.model_validate(audience_data) if audience_data else AudienceAnalysisResult()
        audience_desc = audience_result.primary_persona.persona_name or "general audience"

        return CONTENT_ANGLE_PROMPT, {
            "topic": topic,
            "category": topic_analysis.category,
            "audience": audience_desc,
            "content_type": topic_analysis.content_type,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        def parse_angle(a: dict) -> ContentAngle:
            return ContentAngle(
                angle_type=a.get("angle_type", ""),
                title=a.get("title", ""),
                description=a.get("description", ""),
                rationale=a.get("rationale", ""),
                estimated_engagement=a.get("estimated_engagement", 0.0),
                difficulty_to_produce=a.get("difficulty_to_produce", "medium"),
            )

        angles = [parse_angle(a) for a in data.get("angles", [])]
        selected_data = data.get("selected_angle", {})
        selected = parse_angle(selected_data) if selected_data else None

        return ContentAngleResult(
            angles=angles,
            selected_angle=selected,
            selection_rationale=data.get("selection_rationale", ""),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, ContentAngleResult):
            context.state.research.metadata["content_angle"] = result.model_dump()
            if result.selected_angle:
                context.state.topic.content_angle = result.selected_angle.angle_type
