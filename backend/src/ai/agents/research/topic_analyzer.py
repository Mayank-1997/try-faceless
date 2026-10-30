"""Topic Analyzer Agent — analyzes user topic and produces structured analysis.

First agent in the research workflow.  Understands user intent,
identifies category, difficulty, content type, longevity, and
research depth requirements.
"""

from __future__ import annotations

import json
from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.events import ResearchEventEmitter
from src.ai.agents.research.prompts import TOPIC_ANALYZER_PROMPT
from src.ai.agents.research.schema import TopicAnalysis
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class TopicAnalyzerAgent(BaseAgent):
    """Analyzes a user topic and produces a structured ``TopicAnalysis``.

    Identifies:
    - User intent and expanded topic
    - Category and subcategory
    - Difficulty level
    - Educational vs entertainment
    - Evergreen vs trending
    - Target duration
    - Required research depth
    - Missing information
    """

    def __init__(self) -> None:
        super().__init__(
            name="topic_analyzer",
            retry_policy=RetryPolicies.PROVIDER,
            enable_quality_check=True,
            enable_output_validation=True,
            enable_artifact_creation=True,
            quality_threshold=0.5,
        )

    @property
    def agent_type(self) -> AgentType:
        return AgentType.TOPIC

    @property
    def output_validator_config(self) -> dict[str, Any]:
        return {
            "required_fields": ["expanded_topic", "category", "difficulty", "content_type"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic = context.state.topic.raw_topic or context.state.project.name
        return TOPIC_ANALYZER_PROMPT, {
            "topic": topic,
            "target_duration": context.state.project.target_duration_seconds or 600,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return TopicAnalysis(
            raw_topic=context.state.topic.raw_topic or context.state.project.name,
            expanded_topic=data.get("expanded_topic", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            difficulty=data.get("difficulty", "intermediate"),
            content_type=data.get("content_type", "educational"),
            longevity=data.get("longevity", "evergreen"),
            # The user's requested duration is authoritative — never let
            # the model override it with its own estimate.
            target_duration_seconds=(
                context.state.project.target_duration_seconds
                or data.get("target_duration_seconds", 600)
            ),
            research_depth=data.get("research_depth", "standard"),
            user_intent=data.get("user_intent", ""),
            missing_information=data.get("missing_information", []),
            suggested_angles=data.get("suggested_angles", []),
            language=data.get("language", "en"),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, TopicAnalysis):
            context.state.topic.raw_topic = result.raw_topic
            context.state.topic.expanded_topic = result.expanded_topic
            context.state.topic.target_audience = result.category
            # Store topic analysis in research metadata for later agents
            context.state.research.metadata["topic_analysis"] = result.model_dump()
