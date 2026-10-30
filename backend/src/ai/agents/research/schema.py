"""Research package schema — structured output from the research subsystem.

The ``ResearchPackage`` is the final reusable object produced by the
research workflow.  It contains all data that downstream agents
(Script, Story Planner, Scene Planner) need to generate content.

All models are strongly-typed Pydantic v2 models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Topic analysis
# ---------------------------------------------------------------------------
class TopicAnalysis(BaseModel):
    """Structured analysis of a user's topic.

    Produced by ``TopicAnalyzerAgent``.
    """

    raw_topic: str = ""
    expanded_topic: str = ""
    category: str = ""
    subcategory: str = ""
    difficulty: str = "intermediate"  # beginner, intermediate, advanced, expert
    content_type: str = "educational"  # educational, entertainment, mixed
    longevity: str = "evergreen"  # evergreen, trending, seasonal
    target_duration_seconds: int = 600
    research_depth: str = "standard"  # light, standard, deep, comprehensive
    user_intent: str = ""
    missing_information: list[str] = Field(default_factory=list)
    suggested_angles: list[str] = Field(default_factory=list)
    language: str = "en"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Research plan
# ---------------------------------------------------------------------------
class SearchQuery(BaseModel):
    """A single search query in the research plan."""

    query: str = ""
    priority: int = 1  # 1 = highest
    source_types: list[str] = Field(default_factory=list)
    expected_results: str = ""


class ResearchSection(BaseModel):
    """A planned section of research."""

    title: str = ""
    description: str = ""
    priority: int = 1
    queries: list[SearchQuery] = Field(default_factory=list)
    fact_requirements: list[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    """Research plan produced by ``ResearchPlannerAgent``."""

    strategy: str = ""
    sections: list[ResearchSection] = Field(default_factory=list)
    total_queries: int = 0
    source_diversity_required: bool = True
    min_sources: int = 3
    max_sources: int = 10
    language: str = "en"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Research data (web search results)
# ---------------------------------------------------------------------------
class ResearchFact(BaseModel):
    """A single verified or unverified fact."""

    fact: str = ""
    source_url: str = ""
    source_title: str = ""
    category: str = ""  # fact, statistic, example, historical_event, definition
    confidence: float = 0.0  # 0.0 to 1.0
    verified: bool = False
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchItem(BaseModel):
    """A single research item gathered from web search."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    content: str = ""
    source_type: str = ""  # web, academic, news, blog, documentation
    relevance_score: float = 0.0
    published_date: str | None = None
    facts: list[ResearchFact] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebResearchResult(BaseModel):
    """Result of web research from ``ResearchAgent``."""

    query: str = ""
    items: list[ResearchItem] = Field(default_factory=list)
    total_results: int = 0
    facts: list[ResearchFact] = Field(default_factory=list)
    statistics: list[ResearchFact] = Field(default_factory=list)
    examples: list[ResearchFact] = Field(default_factory=list)
    historical_events: list[ResearchFact] = Field(default_factory=list)
    definitions: list[ResearchFact] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Fact verification
# ---------------------------------------------------------------------------
class VerifiedFact(BaseModel):
    """A fact that has been cross-checked and verified."""

    fact: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    verified: bool = False
    conflicting: bool = False
    sources: list[str] = Field(default_factory=list)
    source_count: int = 0
    notes: str = ""
    category: str = ""


class FactVerificationResult(BaseModel):
    """Result of fact verification from ``FactVerificationAgent``."""

    verified_facts: list[VerifiedFact] = Field(default_factory=list)
    flagged_facts: list[VerifiedFact] = Field(default_factory=list)
    removed_facts: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0
    total_checked: int = 0
    total_verified: int = 0
    total_flagged: int = 0
    total_removed: int = 0


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------
class KeywordSet(BaseModel):
    """Extracted keywords from ``KeywordExtractionAgent``."""

    primary_keywords: list[str] = Field(default_factory=list)
    secondary_keywords: list[str] = Field(default_factory=list)
    semantic_keywords: list[str] = Field(default_factory=list)
    long_tail_keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    seo_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audience analysis
# ---------------------------------------------------------------------------
class AudiencePersona(BaseModel):
    """Audience persona from ``AudienceAnalysisAgent``."""

    persona_name: str = ""
    description: str = ""
    knowledge_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    age_range: str = ""
    interests: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    reading_level: str = "standard"  # basic, standard, advanced
    preferred_content_style: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AudienceAnalysisResult(BaseModel):
    """Result of audience analysis."""

    primary_persona: AudiencePersona = Field(default_factory=AudiencePersona)
    secondary_personas: list[AudiencePersona] = Field(default_factory=list)
    estimated_audience_size: str = ""
    engagement_drivers: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Content angle
# ---------------------------------------------------------------------------
class ContentAngle(BaseModel):
    """A single content angle option."""

    angle_type: str = ""  # educational, storytelling, comparison, timeline, explainer, case_study, opinion
    title: str = ""
    description: str = ""
    rationale: str = ""
    estimated_engagement: float = 0.0  # 0.0 to 1.0
    difficulty_to_produce: str = "medium"  # easy, medium, hard
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContentAngleResult(BaseModel):
    """Result of content angle selection."""

    angles: list[ContentAngle] = Field(default_factory=list)
    selected_angle: ContentAngle | None = None
    selection_rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Research summary
# ---------------------------------------------------------------------------
class ResearchSummary(BaseModel):
    """Structured research summary from ``ResearchSummaryAgent``."""

    overview: str = ""
    important_facts: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    suggested_narrative: str = ""
    key_takeaways: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Research package (final output)
# ---------------------------------------------------------------------------
class ResearchPackage(BaseModel):
    """The complete research package — final output of the research workflow.

    This is the reusable object that downstream agents (Script, Story
    Planner, Scene Planner) consume to generate content.

    Attributes:
        id: Unique identifier for this research package.
        topic_analysis: Structured topic analysis.
        research_plan: Research plan with sections and queries.
        web_research: Raw web research results.
        fact_verification: Verified and flagged facts.
        keywords: Extracted keywords for SEO.
        audience: Audience analysis with personas.
        content_angle: Selected content angle.
        summary: Structured research summary.
        confidence_score: Overall confidence in the research (0.0–1.0).
        created_at: When the package was created.
        version: Version number for tracking updates.
    """

    id: UUID = Field(default_factory=uuid4)
    topic_analysis: TopicAnalysis = Field(default_factory=TopicAnalysis)
    research_plan: ResearchPlan = Field(default_factory=ResearchPlan)
    web_research: WebResearchResult = Field(default_factory=WebResearchResult)
    fact_verification: FactVerificationResult = Field(default_factory=FactVerificationResult)
    keywords: KeywordSet = Field(default_factory=KeywordSet)
    audience: AudienceAnalysisResult = Field(default_factory=AudienceAnalysisResult)
    content_angle: ContentAngleResult = Field(default_factory=ContentAngleResult)
    summary: ResearchSummary = Field(default_factory=ResearchSummary)
    confidence_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @property
    def is_ready(self) -> bool:
        """Check if the research package has minimum required data."""
        return (
            bool(self.topic_analysis.expanded_topic)
            and bool(self.summary.overview)
            and len(self.fact_verification.verified_facts) > 0
            and self.confidence_score > 0.0
        )

    @property
    def verified_facts(self) -> list[VerifiedFact]:
        """Return all verified facts."""
        return self.f_verification_verified if False else self.fact_verification.verified_facts

    @property
    def all_keywords(self) -> list[str]:
        """Return all keywords combined."""
        return (
            self.keywords.primary_keywords
            + self.keywords.secondary_keywords
            + self.keywords.semantic_keywords
            + self.keywords.long_tail_keywords
        )

    @property
    def all_references(self) -> list[str]:
        """Return all unique references."""
        refs = set(self.summary.references)
        refs.update(self.web_research.references)
        for vf in self.fact_verification.verified_facts:
            refs.update(vf.sources)
        return sorted(refs)
