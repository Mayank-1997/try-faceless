"""Script package schema — structured output from the script generation subsystem.

The ``ScriptPackage`` is the final reusable object produced by the
script workflow.  It contains all data that downstream agents
(Storyboard, Scene Planner) need to plan visual scenes.

All models are strongly-typed Pydantic v2 models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Narrative strategy
# ---------------------------------------------------------------------------
class NarrativeStrategy(BaseModel):
    """Storytelling strategy chosen for the script.

    Produced by ``NarrativeStrategyAgent``.
    """

    style: str = "educational"  # educational, storytelling, documentary, mystery, timeline, case_study, comparison, tutorial, problem_solution
    rationale: str = ""
    flow: str = ""  # Description of the narrative flow
    pacing: str = "moderate"  # fast, moderate, slow, varied
    tone: str = "informative"  # informative, casual, dramatic, humorous, inspirational
    emotional_arc: str = ""
    key_beats: list[str] = Field(default_factory=list)
    audience_alignment: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Script outline
# ---------------------------------------------------------------------------
class OutlineSection(BaseModel):
    """A single section in the script outline."""

    section_id: str = ""
    title: str = ""
    description: str = ""
    key_talking_points: list[str] = Field(default_factory=list)
    estimated_time_seconds: int = 0
    target_word_count: int = 0
    references: list[str] = Field(default_factory=list)
    subsections: list[str] = Field(default_factory=list)
    importance: str = "medium"  # low, medium, high, critical
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScriptOutline(BaseModel):
    """Complete script outline produced by ``ScriptOutlineAgent``."""

    title: str = ""
    opening: str = ""
    sections: list[OutlineSection] = Field(default_factory=list)
    closing: str = ""
    total_estimated_time_seconds: int = 0
    total_target_word_count: int = 0
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hook
# ---------------------------------------------------------------------------
class Hook(BaseModel):
    """A single hook option."""

    hook_type: str = ""  # question, bold_statement, unexpected_fact, story, contradiction, curiosity_gap
    content: str = ""
    rationale: str = ""
    estimated_retention_score: float = 0.0  # 0.0 to 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class HookResult(BaseModel):
    """Result of hook generation from ``HookGeneratorAgent``."""

    hooks: list[Hook] = Field(default_factory=list)
    selected_hook: Hook | None = None
    rejected_hooks: list[Hook] = Field(default_factory=list)
    selection_rationale: str = ""


# ---------------------------------------------------------------------------
# Script section
# ---------------------------------------------------------------------------
class ScriptSection(BaseModel):
    """A fully written script section.

    Produced by ``SectionWriterAgent``.
    """

    section_id: str = ""
    title: str = ""
    narration: str = ""
    estimated_duration_seconds: int = 0
    word_count: int = 0
    emotion: str = ""  # neutral, excited, serious, curious, empathetic, dramatic
    importance: str = "medium"  # low, medium, high, critical
    purpose: str = ""  # inform, persuade, entertain, illustrate, transition
    references: list[str] = Field(default_factory=list)
    transition: str = ""  # Transition to the next section
    facts_used: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    future_scene_count: int = 0  # How many visual scenes this section might need
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------
class TransitionResult(BaseModel):
    """Result of transition generation from ``TransitionAgent``."""

    transitions: dict[str, str] = Field(default_factory=dict)  # section_id -> transition text
    flow_analysis: str = ""
    smoothness_score: float = 0.0  # 0.0 to 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Call to action
# ---------------------------------------------------------------------------
class CallToAction(BaseModel):
    """A single CTA option."""

    cta_type: str = ""  # subscribe, like, comment, visit_website, download, newsletter
    content: str = ""
    placement: str = "end"  # end, mid, intro
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CTAResult(BaseModel):
    """Result of CTA generation from ``CallToActionAgent``."""

    ctas: list[CallToAction] = Field(default_factory=list)
    primary_cta: CallToAction | None = None
    secondary_ctas: list[CallToAction] = Field(default_factory=list)
    channel_style_match: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Script review
# ---------------------------------------------------------------------------
class ScriptReviewResult(BaseModel):
    """Result of script review from ``ScriptReviewAgent``.

    Validates logic, flow, completeness, consistency, fact usage,
    audience alignment, length, and reading level.
    """

    logic_score: float = 0.0  # 0.0 to 1.0
    flow_score: float = 0.0
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    fact_usage_score: float = 0.0
    audience_alignment_score: float = 0.0
    length_score: float = 0.0
    reading_level_score: float = 0.0
    overall_score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    passed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Script optimization
# ---------------------------------------------------------------------------
class ScriptOptimizationResult(BaseModel):
    """Result of script optimization from ``ScriptOptimizationAgent``.

    Improves retention, clarity, redundancy, sentence variety,
    natural speech, and engagement.
    """

    optimized_content: str = ""
    retention_improvement: float = 0.0  # Estimated improvement
    clarity_improvement: float = 0.0
    redundancy_reduction: float = 0.0
    sentence_variety_score: float = 0.0
    natural_speech_score: float = 0.0
    engagement_score: float = 0.0
    changes_made: list[str] = Field(default_factory=list)
    optimized_sections: list[ScriptSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Script quality evaluation
# ---------------------------------------------------------------------------
class ScriptQualityEvaluation(BaseModel):
    """Quality evaluation of the final script.

    Evaluates retention potential, curiosity, flow, clarity,
    natural speech, fact density, and audience alignment.
    """

    retention_potential: float = 0.0  # 0.0 to 1.0
    curiosity: float = 0.0
    flow: float = 0.0
    clarity: float = 0.0
    natural_speech: float = 0.0
    fact_density: float = 0.0
    audience_alignment: float = 0.0
    overall_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Script package (final output)
# ---------------------------------------------------------------------------
class ScriptPackage(BaseModel):
    """The complete script package — final output of the script workflow.

    This is the reusable object that downstream agents (Storyboard,
    Scene Planner) consume to plan visual scenes and generate assets.

    Attributes:
        id: Unique identifier for this script package.
        narrative_strategy: Chosen storytelling strategy.
        outline: Complete script outline.
        hook_result: Selected hook with rejected alternatives.
        sections: Fully written script sections.
        transitions: Smooth transitions between sections.
        cta_result: Call-to-action content.
        review: Script review results.
        optimization: Script optimization results.
        quality: Quality evaluation scores.
        full_script: The complete assembled script text.
        title: Script title.
        word_count: Total word count.
        estimated_duration_seconds: Estimated narration duration.
        reading_time_minutes: Estimated reading time.
        references: All references used.
        version: Version number.
        created_at: When the package was created.
    """

    id: UUID = Field(default_factory=uuid4)
    narrative_strategy: NarrativeStrategy = Field(default_factory=NarrativeStrategy)
    outline: ScriptOutline = Field(default_factory=ScriptOutline)
    hook_result: HookResult = Field(default_factory=HookResult)
    sections: list[ScriptSection] = Field(default_factory=list)
    transitions: TransitionResult = Field(default_factory=TransitionResult)
    cta_result: CTAResult = Field(default_factory=CTAResult)
    review: ScriptReviewResult = Field(default_factory=ScriptReviewResult)
    optimization: ScriptOptimizationResult = Field(default_factory=ScriptOptimizationResult)
    quality: ScriptQualityEvaluation = Field(default_factory=ScriptQualityEvaluation)
    full_script: str = ""
    title: str = ""
    word_count: int = 0
    estimated_duration_seconds: int = 0
    reading_time_minutes: float = 0.0
    references: list[str] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_ready(self) -> bool:
        """Check if the script package has minimum required data."""
        return (
            bool(self.full_script)
            and bool(self.title)
            and len(self.sections) > 0
            and self.word_count > 0
        )

    @property
    def section_count(self) -> int:
        """Return the number of sections."""
        return len(self.sections)

    @property
    def all_references(self) -> list[str]:
        """Return all unique references across sections and outline."""
        refs = set(self.references)
        refs.update(self.outline.references)
        for section in self.sections:
            refs.update(section.references)
        return sorted(refs)

    def assemble_full_script(self) -> str:
        """Assemble the full script from hook, sections, transitions, and CTA.

        Returns:
            The complete script as a single string.
        """
        parts: list[str] = []

        # Hook
        if self.hook_result.selected_hook:
            parts.append(self.hook_result.selected_hook.content)
            parts.append("")

        # Sections with transitions
        for i, section in enumerate(self.sections):
            parts.append(section.narration)
            if section.transition and i < len(self.sections) - 1:
                parts.append("")
                parts.append(section.transition)
            parts.append("")

        # CTA
        if self.cta_result.primary_cta:
            parts.append(self.cta_result.primary_cta.content)

        return "\n".join(parts).strip()
