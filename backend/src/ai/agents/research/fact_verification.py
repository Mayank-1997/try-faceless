"""Fact Verification Agent — cross-checks research facts for accuracy.

Fourth agent in the research workflow.  Takes all gathered facts,
cross-references them, removes conflicting information, flags
uncertain claims, and assigns confidence scores.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import FACT_VERIFICATION_PROMPT
from src.ai.agents.research.schema import (
    FactVerificationResult,
    ResearchFact,
    VerifiedFact,
    WebResearchResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class FactVerificationAgent(BaseAgent):
    """Cross-checks research facts and assigns confidence scores.

    - Verifies facts against multiple sources
    - Removes conflicting information
    - Flags uncertain claims
    - Assigns confidence scores (0.0–1.0)
    - Supports multiple references per fact
    """

    def __init__(self) -> None:
        super().__init__(
            name="fact_verification",
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
            "required_fields": ["verified_facts", "overall_confidence"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        # Gather all facts from web research
        web_data = context.state.research.metadata.get("web_research", {})
        web_result = WebResearchResult.model_validate(web_data) if web_data else WebResearchResult()

        all_facts = web_result.facts + web_result.statistics + web_result.examples + web_result.historical_events + web_result.definitions

        facts_text = "\n".join(
            f"- [{f.category}] {f.fact} (Source: {f.source_url or 'N/A'}, Confidence: {f.confidence:.2f})"
            for f in all_facts if f.fact
        )

        if not facts_text:
            facts_text = "No facts available for verification."

        return FACT_VERIFICATION_PROMPT, {
            "topic": topic,
            "facts": facts_text,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        def parse_verified(raw: list[dict]) -> list[VerifiedFact]:
            return [
                VerifiedFact(
                    fact=f.get("fact", ""),
                    confidence=f.get("confidence", 0.5),
                    verified=f.get("verified", False),
                    conflicting=f.get("conflicting", False),
                    sources=f.get("sources", []),
                    source_count=f.get("source_count", len(f.get("sources", []))),
                    notes=f.get("notes", ""),
                    category=f.get("category", "fact"),
                )
                for f in raw if f.get("fact")
            ]

        return FactVerificationResult(
            verified_facts=parse_verified(data.get("verified_facts", [])),
            flagged_facts=parse_verified(data.get("flagged_facts", [])),
            removed_facts=data.get("removed_facts", []),
            overall_confidence=data.get("overall_confidence", 0.0),
            total_checked=data.get("total_checked", 0),
            total_verified=data.get("total_verified", 0),
            total_flagged=data.get("total_flagged", 0),
            total_removed=data.get("total_removed", 0),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if isinstance(result, FactVerificationResult):
            context.state.research.metadata["fact_verification"] = result.model_dump()
