"""Keyword Extraction Agent — extracts SEO keywords from research.

Fifth agent in the research workflow.  Generates primary, secondary,
semantic, long-tail keywords, entities, concepts, and SEO tags
for future SEO optimization.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import KEYWORD_EXTRACTION_PROMPT
from src.ai.agents.research.schema import (
    FactVerificationResult,
    KeywordSet,
    WebResearchResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class KeywordExtractionAgent(BaseAgent):
    """Extracts keywords from research content for SEO use.

    Generates:
    - Primary keywords (3-5)
    - Secondary keywords (5-10)
    - Semantic keywords (5-10)
    - Long-tail keywords (5-10)
    - Entities (people, places, organizations)
    - Concepts (abstract themes)
    - SEO tags
    """

    def __init__(self) -> None:
        super().__init__(
            name="keyword_extraction",
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
            "required_fields": ["primary_keywords"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        # Build research summary from verified facts
        fv_data = context.state.research.metadata.get("fact_verification", {})
        fv_result = FactVerificationResult.model_validate(fv_data) if fv_data else FactVerificationResult()

        web_data = context.state.research.metadata.get("web_research", {})
        web_result = WebResearchResult.model_validate(web_data) if web_data else WebResearchResult()

        summary_parts = []
        for vf in fv_result.verified_facts[:20]:
            summary_parts.append(f"- {vf.fact}")
        for fact in web_result.facts[:10]:
            summary_parts.append(f"- {fact.fact}")

        research_summary = "\n".join(summary_parts) if summary_parts else "Limited research data available."

        return KEYWORD_EXTRACTION_PROMPT, {
            "topic": topic,
            "research_summary": research_summary,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return KeywordSet(
            primary_keywords=data.get("primary_keywords", []),
            secondary_keywords=data.get("secondary_keywords", []),
            semantic_keywords=data.get("semantic_keywords", []),
            long_tail_keywords=data.get("long_tail_keywords", []),
            entities=data.get("entities", []),
            concepts=data.get("concepts", []),
            seo_tags=data.get("seo_tags", []),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, KeywordSet):
            context.state.research.metadata["keywords"] = result.model_dump()
            context.state.topic.keywords = result.primary_keywords + result.secondary_keywords
