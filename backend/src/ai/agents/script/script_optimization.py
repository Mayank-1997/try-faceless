"""Script Optimization Agent — improves retention, clarity, and engagement.

Eighth and final agent in the script workflow.  Takes the reviewed
script and optimizes it for retention, clarity, redundancy, sentence
variety, natural speech, and engagement.  Also assembles the final
``ScriptPackage`` that downstream agents consume.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.base import BaseAgent
from src.ai.agents.context import AgentContext
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.research.schema import ResearchPackage
from src.ai.agents.script.prompts import SCRIPT_OPTIMIZATION_PROMPT
from src.ai.agents.script.schema import (
    CTAResult,
    HookResult,
    NarrativeStrategy,
    ScriptOptimizationResult,
    ScriptOutline,
    ScriptPackage,
    ScriptQualityEvaluation,
    ScriptReviewResult,
    ScriptSection,
    TransitionResult,
)
from src.ai.agents.response import AIResponse
from src.core.enums import AgentType
from src.workflow.retry_policy import RetryPolicies


class ScriptOptimizationAgent(BaseAgent):
    """Optimizes the script and assembles the final ScriptPackage.

    Improves:
    - Retention potential
    - Clarity
    - Redundancy (reduces repetition)
    - Sentence variety
    - Natural speech
    - Engagement

    Assembles the final ``ScriptPackage`` from all agent outputs.
    """

    def __init__(self) -> None:
        super().__init__(
            name="script_optimization",
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
            "required_fields": ["optimized_content"],
            "max_repair_attempts": 2,
        }

    async def prepare_prompt(self, context: AgentContext) -> tuple[PromptTemplate, dict[str, Any]]:
        rp_data = context.state.research.metadata.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        topic = rp.topic_analysis.expanded_topic or context.state.topic.expanded_topic
        audience = rp.audience.primary_persona.persona_name or "general audience"

        # Assemble full script
        sections_data = context.state.script.metadata.get("sections", [])
        sections = [ScriptSection.model_validate(s) for s in sections_data] if sections_data else []

        hook_data = context.state.script.metadata.get("hook_result", {})
        hook_result = HookResult.model_validate(hook_data) if hook_data else HookResult()

        cta_data = context.state.script.metadata.get("cta_result", {})
        cta_result = CTAResult.model_validate(cta_data) if cta_data else CTAResult()

        parts = []
        if hook_result.selected_hook:
            parts.append(f"[HOOK] {hook_result.selected_hook.content}")
        for s in sections:
            parts.append(f"[{s.section_id}] {s.title}\n{s.narration}")
            if s.transition:
                parts.append(f"[TRANSITION] {s.transition}")
        if cta_result.primary_cta:
            parts.append(f"[CTA] {cta_result.primary_cta.content}")

        full_script = "\n\n".join(parts) if parts else "No script content available."

        # Get review issues
        review_data = context.state.script.metadata.get("review", {})
        review = ScriptReviewResult.model_validate(review_data) if review_data else ScriptReviewResult()
        review_issues = "\n".join(f"- {issue}" for issue in review.issues) if review.issues else "No specific issues identified."

        return SCRIPT_OPTIMIZATION_PROMPT, {
            "topic": topic,
            "audience": audience,
            "full_script": full_script,
            "review_issues": review_issues,
        }

    async def process_response(self, response: AIResponse, context: AgentContext) -> Any:
        data = response.structured_data or {}

        optimized_sections = [
            ScriptSection(
                section_id=s.get("section_id", ""),
                title=s.get("title", ""),
                narration=s.get("narration", ""),
                estimated_duration_seconds=s.get("estimated_duration_seconds", 0),
                word_count=s.get("word_count", len(s.get("narration", "").split()) if s.get("narration") else 0),
                emotion=s.get("emotion", "neutral"),
                importance=s.get("importance", "medium"),
                purpose=s.get("purpose", "inform"),
                references=s.get("references", []),
                facts_used=s.get("facts_used", []),
                examples=s.get("examples", []),
                future_scene_count=s.get("future_scene_count", 0),
            )
            for s in data.get("optimized_sections", [])
            if s.get("narration")
        ]

        return ScriptOptimizationResult(
            optimized_content=data.get("optimized_content", ""),
            retention_improvement=data.get("retention_improvement", 0.0),
            clarity_improvement=data.get("clarity_improvement", 0.0),
            redundancy_reduction=data.get("redundancy_reduction", 0.0),
            sentence_variety_score=data.get("sentence_variety_score", 0.0),
            natural_speech_score=data.get("natural_speech_score", 0.0),
            engagement_score=data.get("engagement_score", 0.0),
            changes_made=data.get("changes_made", []),
            optimized_sections=optimized_sections,
        )

    async def update_workflow_state(
        self,
        result: Any,
        response: AIResponse,
        context: AgentContext,
    ) -> None:
        if not isinstance(result, ScriptOptimizationResult):
            return

        context.state.script.metadata["optimization"] = result.model_dump()

        # Update sections with optimized versions if available
        if result.optimized_sections:
            context.state.script.metadata["sections"] = [s.model_dump() for s in result.optimized_sections]

        # Assemble the final ScriptPackage
        package = self._assemble_package(context, result)
        context.state.script.metadata["script_package"] = package.model_dump()

        # Update top-level script fields — use package.full_script (which
        # falls back to assemble_full_script() when optimized_content is
        # empty, e.g. when the LLM output failed JSON validation).
        context.state.script.content = package.full_script
        context.state.script.word_count = package.word_count
        context.state.script.estimated_duration_seconds = package.estimated_duration_seconds
        context.state.script.body = package.full_script

    def _assemble_package(
        self,
        context: AgentContext,
        optimization: ScriptOptimizationResult,
    ) -> ScriptPackage:
        """Assemble the final script package from all agent outputs."""
        meta = context.state.script.metadata
        rmeta = context.state.research.metadata

        rp_data = rmeta.get("research_package", {})
        rp = ResearchPackage.model_validate(rp_data) if rp_data else ResearchPackage()

        narrative_strategy = NarrativeStrategy.model_validate(meta.get("narrative_strategy", {}))
        outline = ScriptOutline.model_validate(meta.get("script_outline", {}))
        hook_result = HookResult.model_validate(meta.get("hook_result", {}))
        transitions = TransitionResult.model_validate(meta.get("transitions", {}))
        cta_result = CTAResult.model_validate(meta.get("cta_result", {}))
        review = ScriptReviewResult.model_validate(meta.get("review", {}))

        # Use optimized sections if available, otherwise original
        if optimization.optimized_sections:
            sections = optimization.optimized_sections
        else:
            sections_data = meta.get("sections", [])
            sections = [ScriptSection.model_validate(s) for s in sections_data] if sections_data else []

        # Section lengths are budgeted at outline/write time so the story
        # is sized to the requested duration — no post-hoc trimming here.

        # Calculate totals
        word_count = sum(s.word_count for s in sections)
        if hook_result.selected_hook:
            word_count += len(hook_result.selected_hook.content.split())
        if cta_result.primary_cta:
            word_count += len(cta_result.primary_cta.content.split())

        # Derive duration from the actual word count rather than trusting
        # per-section estimates, which drift from real narration length.
        duration = int(word_count / _WORDS_PER_SECOND)
        reading_time = word_count / 150.0  # ~150 wpm reading

        # Quality evaluation
        quality = ScriptQualityEvaluation(
            retention_potential=optimization.engagement_score,
            curiosity=review.overall_score * 0.8,
            flow=review.flow_score,
            clarity=optimization.clarity_improvement + 0.5 if optimization.clarity_improvement > 0 else review.overall_score,
            natural_speech=optimization.natural_speech_score,
            fact_density=review.fact_usage_score,
            audience_alignment=review.audience_alignment_score,
            overall_score=review.overall_score,
        )

        # Assemble full script
        package = ScriptPackage(
            narrative_strategy=narrative_strategy,
            outline=outline,
            hook_result=hook_result,
            sections=sections,
            transitions=transitions,
            cta_result=cta_result,
            review=review,
            optimization=optimization,
            quality=quality,
            full_script=optimization.optimized_content,
            title=outline.title,
            word_count=word_count,
            estimated_duration_seconds=duration,
            reading_time_minutes=reading_time,
            references=rp.all_references,
        )
        # If optimized content is empty, assemble from parts
        if not package.full_script:
            package.full_script = package.assemble_full_script()

        return package


_WORDS_PER_SECOND = 2.5  # ~150 wpm narration rate
