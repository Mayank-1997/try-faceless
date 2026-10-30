"""Research Planner Agent — creates a structured research plan.

Second agent in the research workflow.  Takes the topic analysis
and produces a research plan with sections, search queries, source
diversity requirements, and fact requirements.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import RESEARCH_PLANNER_PROMPT
from src.ai.agents.research.schema import ResearchPlan, ResearchSection, SearchQuery, TopicAnalysis
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ResearchPlannerAgent(BaseAgent):
    """Creates a structured research plan from topic analysis.

    Produces:
    - Search strategy
    - Research sections with queries
    - Priority ordering
    - Source diversity requirements
    - Fact requirements per section
    """

    def __init__(self) -> None:
        super().__init__(
            name="research_planner",
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
            "required_fields": ["strategy", "sections"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic_analysis_data = context.state.research.metadata.get("topic_analysis", {})
        topic_analysis = TopicAnalysis.model_validate(topic_analysis_data) if topic_analysis_data else TopicAnalysis()
        topic = topic_analysis.expanded_topic or context.state.topic.expanded_topic
        return RESEARCH_PLANNER_PROMPT, {
            "topic": topic,
            "category": topic_analysis.category,
            "research_depth": topic_analysis.research_depth,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        sections = []
        for section_data in data.get("sections", []):
            queries = [
                SearchQuery(
                    query=q.get("query", ""),
                    priority=q.get("priority", 1),
                    source_types=q.get("source_types", []),
                    expected_results=q.get("expected_results", ""),
                )
                for q in section_data.get("queries", [])
            ]
            sections.append(ResearchSection(
                title=section_data.get("title", ""),
                description=section_data.get("description", ""),
                priority=section_data.get("priority", 1),
                queries=queries,
                fact_requirements=section_data.get("fact_requirements", []),
            ))
        return ResearchPlan(
            strategy=data.get("strategy", ""),
            sections=sections,
            total_queries=data.get("total_queries", sum(len(s.queries) for s in sections)),
            source_diversity_required=data.get("source_diversity_required", True),
            min_sources=data.get("min_sources", 3),
            max_sources=data.get("max_sources", 10),
            language=data.get("language", "en"),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, ResearchPlan):
            context.state.research.metadata["research_plan"] = result.model_dump()
