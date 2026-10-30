"""Audience Analysis Agent — identifies target audience personas.

Sixth agent in the research workflow.  Identifies audience personas,
knowledge levels, pain points, questions, interests, and reading
levels to inform content creation.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import AUDIENCE_ANALYSIS_PROMPT
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    AudiencePersona,
    TopicAnalysis,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class AudienceAnalysisAgent(BaseAgent):
    """Identifies target audience personas and characteristics.

    Produces:
    - Primary persona with demographics, interests, pain points
    - Secondary personas
    - Knowledge level assessment
    - Engagement drivers
    - Reading level
    """

    def __init__(self) -> None:
        super().__init__(
            name="audience_analysis",
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
            "required_fields": ["primary_persona"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic_data = context.state.research.metadata.get("topic_analysis", {})
        topic_analysis = TopicAnalysis.model_validate(topic_data) if topic_data else TopicAnalysis()
        topic = topic_analysis.expanded_topic or context.state.topic.expanded_topic

        return AUDIENCE_ANALYSIS_PROMPT, {
            "topic": topic,
            "category": topic_analysis.category,
            "content_type": topic_analysis.content_type,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        primary_data = data.get("primary_persona", {})
        primary = AudiencePersona(
            persona_name=primary_data.get("persona_name", ""),
            description=primary_data.get("description", ""),
            knowledge_level=primary_data.get("knowledge_level", "intermediate"),
            age_range=primary_data.get("age_range", ""),
            interests=primary_data.get("interests", []),
            pain_points=primary_data.get("pain_points", []),
            questions=primary_data.get("questions", []),
            reading_level=primary_data.get("reading_level", "standard"),
            preferred_content_style=primary_data.get("preferred_content_style", ""),
        )

        secondary = [
            AudiencePersona(
                persona_name=p.get("persona_name", ""),
                description=p.get("description", ""),
                knowledge_level=p.get("knowledge_level", "intermediate"),
                age_range=p.get("age_range", ""),
                interests=p.get("interests", []),
                pain_points=p.get("pain_points", []),
                questions=p.get("questions", []),
                reading_level=p.get("reading_level", "standard"),
                preferred_content_style=p.get("preferred_content_style", ""),
            )
            for p in data.get("secondary_personas", [])
        ]

        return AudienceAnalysisResult(
            primary_persona=primary,
            secondary_personas=secondary,
            estimated_audience_size=data.get("estimated_audience_size", ""),
            engagement_drivers=data.get("engagement_drivers", []),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, AudienceAnalysisResult):
            context.state.research.metadata["audience"] = result.model_dump()
            context.state.topic.target_audience = result.primary_persona.persona_name
