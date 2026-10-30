"""Research Summary Agent — generates structured research summary.

Eighth and final agent in the research workflow.  Takes all research
data (verified facts, statistics, audience, content angle) and
produces a structured ``ResearchSummary`` with overview, important
facts, timeline, examples, statistics, warnings, references, and
suggested narrative.

Also assembles the final ``ResearchPackage`` that downstream agents
consume.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.prompts import RESEARCH_SUMMARY_PROMPT
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    ContentAngleResult,
    FactVerificationResult,
    KeywordSet,
    ResearchPackage,
    ResearchPlan,
    ResearchSummary,
    TopicAnalysis,
    WebResearchResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ResearchSummaryAgent(BaseAgent):
    """Generates a structured research summary and assembles the research package.

    Produces:
    - Overview (2-3 paragraphs)
    - Important facts
    - Timeline of key events
    - Examples
    - Statistics with context
    - Warnings and caveats
    - References
    - Suggested narrative
    - Key takeaways

    Assembles the final ``ResearchPackage`` from all agent outputs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="research_summary",
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
            "required_fields": ["overview", "important_facts"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        topic = context.state.topic.expanded_topic or context.state.topic.raw_topic

        # Gather all research data
        fv_data = context.state.research.metadata.get("fact_verification", {})
        fv_result = FactVerificationResult.model_validate(fv_data) if fv_data else FactVerificationResult()

        verified_facts_text = "\n".join(
            f"- [{vf.category}] {vf.fact} (Confidence: {vf.confidence:.2f})"
            for vf in fv_result.verified_facts[:20]
        ) or "No verified facts available."

        statistics_text = "\n".join(
            f"- {vf.fact}"
            for vf in fv_result.verified_facts if vf.category == "statistic"
        ) or "No statistics available."

        audience_data = context.state.research.metadata.get("audience", {})
        audience_result = AudienceAnalysisResult.model_validate(audience_data) if audience_data else AudienceAnalysisResult()
        audience_text = audience_result.primary_persona.description or "General audience"

        angle_data = context.state.research.metadata.get("content_angle", {})
        angle_result = ContentAngleResult.model_validate(angle_data) if angle_data else ContentAngleResult()
        angle_text = ""
        if angle_result.selected_angle:
            angle_text = f"{angle_result.selected_angle.angle_type}: {angle_result.selected_angle.title}"

        return RESEARCH_SUMMARY_PROMPT, {
            "topic": topic,
            "verified_facts": verified_facts_text,
            "statistics": statistics_text,
            "audience": audience_text,
            "content_angle": angle_text,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}
        return ResearchSummary(
            overview=data.get("overview", ""),
            important_facts=data.get("important_facts", []),
            timeline=data.get("timeline", []),
            examples=data.get("examples", []),
            statistics=data.get("statistics", []),
            warnings=data.get("warnings", []),
            references=data.get("references", []),
            suggested_narrative=data.get("suggested_narrative", ""),
            key_takeaways=data.get("key_takeaways", []),
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if not isinstance(result, ResearchSummary):
            return

        context.state.research.metadata["research_summary"] = result.model_dump()
        context.state.research.summary = result.overview

        # Assemble the final ResearchPackage
        package = self._assemble_package(context, result)
        context.state.research.metadata["research_package"] = package.model_dump()

    def _assemble_package(self, context: AgentContext, summary: ResearchSummary) -> ResearchPackage:
        """Assemble the final research package from all agent outputs."""
        meta = context.state.research.metadata

        topic_analysis = TopicAnalysis.model_validate(meta.get("topic_analysis", {}))
        research_plan = ResearchPlan.model_validate(meta.get("research_plan", {}))
        web_research = WebResearchResult.model_validate(meta.get("web_research", {}))
        fact_verification = FactVerificationResult.model_validate(meta.get("fact_verification", {}))
        keywords = KeywordSet.model_validate(meta.get("keywords", {}))
        audience = AudienceAnalysisResult.model_validate(meta.get("audience", {}))
        content_angle = ContentAngleResult.model_validate(meta.get("content_angle", {}))

        confidence = fact_verification.overall_confidence
        if confidence == 0.0 and fact_verification.total_checked > 0:
            confidence = fact_verification.total_verified / fact_verification.total_checked

        return ResearchPackage(
            topic_analysis=topic_analysis,
            research_plan=research_plan,
            web_research=web_research,
            fact_verification=fact_verification,
            keywords=keywords,
            audience=audience,
            content_angle=content_angle,
            summary=summary,
            confidence_score=confidence,
        )
