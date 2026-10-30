"""Storyboard package schema — structured output from the storyboard & scene planning subsystem.

The ``StoryboardPackage`` is the final reusable object produced by the
storyboard workflow.  It contains all data that downstream agents
(Image, Video, Voice, Rendering) need to generate and render assets.

All models are strongly-typed Pydantic v2 models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Story analysis
# ---------------------------------------------------------------------------
class StoryAnalysis(BaseModel):
    """Analysis of the script's narrative structure.

    Produced by ``StoryAnalyzerAgent``.
    """

    narrative_flow: str = ""
    emotional_peaks: list[str] = Field(default_factory=list)
    pacing: str = "moderate"  # fast, moderate, slow, varied
    scene_boundaries: list[str] = Field(default_factory=list)
    emphasis_points: list[str] = Field(default_factory=list)
    dramatic_moments: list[str] = Field(default_factory=list)
    visual_opportunities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Story beats
# ---------------------------------------------------------------------------
class StoryBeat(BaseModel):
    """A single story beat in the narrative.

    Examples: introduction, conflict, explanation, reveal, transition, conclusion.
    """

    beat_type: str = ""  # introduction, conflict, explanation, reveal, transition, conclusion
    purpose: str = ""
    emotion: str = ""
    duration_seconds: int = 0
    importance: str = "medium"  # low, medium, high, critical
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryBeatResult(BaseModel):
    """Result of story beat generation from ``StoryBeatAgent``."""

    beats: list[StoryBeat] = Field(default_factory=list)
    total_beats: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scene segmentation
# ---------------------------------------------------------------------------
class PlannedScene(BaseModel):
    """A single production scene from ``SceneSegmentationAgent``.

    Contains scene number, timing, narration, goal, and type.
    """

    scene_number: int = 0
    scene_id: str = ""
    title: str = ""
    start_timestamp: float = 0.0
    end_timestamp: float = 0.0
    narration: str = ""
    estimated_duration_seconds: int = 0
    scene_goal: str = ""
    scene_type: str = ""  # talking, diagram, animation, timeline, infographic, comparison, map, screenshot, code, product_demo, stock_footage, ai_image, ai_video, mixed
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneSegmentationResult(BaseModel):
    """Result of scene segmentation from ``SceneSegmentationAgent``."""

    scenes: list[PlannedScene] = Field(default_factory=list)
    total_scenes: int = 0
    total_duration_seconds: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Visual storyboard
# ---------------------------------------------------------------------------
class VisualPlan(BaseModel):
    """Visual description for a single scene.

    Produced by ``StoryboardAgent``.
    """

    scene_id: str = ""
    visual_description: str = ""
    composition: str = ""
    foreground: str = ""
    background: str = ""
    objects: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    environment: str = ""
    mood: str = ""
    lighting: str = ""
    color_palette: list[str] = Field(default_factory=list)
    depth: str = ""  # flat, shallow, deep
    visual_style: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualStoryboardResult(BaseModel):
    """Result of visual storyboard generation from ``StoryboardAgent``."""

    visual_plans: list[VisualPlan] = Field(default_factory=list)
    # Canonical character + setting description, prepended verbatim to
    # every scene's generation prompt so independently generated clips
    # keep the same protagonist and location.
    shared_context: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Camera planning
# ---------------------------------------------------------------------------
class CameraPlan(BaseModel):
    """Camera plan for a single scene.

    Produced by ``CameraPlannerAgent``.
    """

    scene_id: str = ""
    camera_angle: str = ""  # wide, medium, close_up, extreme_close_up, overhead, low_angle, high_angle, dutch, pov
    camera_distance: str = ""  # far, medium, close
    lens: str = ""  # wide, standard, telephoto, macro
    movement: str = ""  # static, pan_left, pan_right, zoom_in, zoom_out, tilt_up, tilt_down, dolly_in, dolly_out, tracking, orbit
    motion_speed: str = "normal"  # slow, normal, fast
    focus_point: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CameraPlanResult(BaseModel):
    """Result of camera planning from ``CameraPlannerAgent``."""

    camera_plans: list[CameraPlan] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Animation planning
# ---------------------------------------------------------------------------
class AnimationPlan(BaseModel):
    """Animation plan for a single scene.

    Produced by ``AnimationPlannerAgent``.
    """

    scene_id: str = ""
    element_animation: str = ""
    text_animation: str = ""
    camera_motion: str = ""
    object_motion: str = ""
    background_motion: str = ""
    timing: str = ""
    entrance_transition: str = ""
    exit_transition: str = ""
    scene_effects: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnimationPlanResult(BaseModel):
    """Result of animation planning from ``AnimationPlannerAgent``."""

    animation_plans: list[AnimationPlan] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Asset decision
# ---------------------------------------------------------------------------
class AssetSceneDecision(BaseModel):
    """Asset decision for a single scene.

    Produced by ``AssetDecisionAgent``.
    """

    scene_id: str = ""
    asset_type: str = ""  # ai_image, ai_video, stock_video, diagram, chart, icon, screenshot, animation_only, mixed_assets
    confidence_score: float = 0.0  # 0.0 to 1.0
    estimated_generation_cost: float = 0.0
    estimated_rendering_complexity: str = "low"  # low, medium, high
    rationale: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetDecisionResult(BaseModel):
    """Result of asset decision from ``AssetDecisionAgent``."""

    decisions: list[AssetSceneDecision] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Continuity
# ---------------------------------------------------------------------------
class ContinuityResult(BaseModel):
    """Result of continuity checking from ``ContinuityAgent``.

    Ensures consistency across scenes.
    """

    character_consistency: str = ""
    color_consistency: str = ""
    object_consistency: str = ""
    visual_style_consistency: str = ""
    camera_style_consistency: str = ""
    aspect_ratio: str = "16:9"
    lighting_consistency: str = ""
    transition_consistency: str = ""
    brand_style: str = ""
    issues: list[str] = Field(default_factory=list)
    consistency_score: float = 0.0  # 0.0 to 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Storyboard review
# ---------------------------------------------------------------------------
class StoryboardReviewResult(BaseModel):
    """Result of storyboard review from ``StoryboardReviewAgent``.

    Validates scene flow, visual variety, duration, continuity, etc.
    """

    scene_flow_score: float = 0.0
    visual_variety_score: float = 0.0
    scene_balance_score: float = 0.0
    narrative_consistency_score: float = 0.0
    camera_variety_score: float = 0.0
    animation_quality_score: float = 0.0
    budget_efficiency_score: float = 0.0
    rendering_feasibility_score: float = 0.0
    overall_score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    passed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Storyboard quality evaluation
# ---------------------------------------------------------------------------
class StoryboardQualityEvaluation(BaseModel):
    """Quality evaluation of the final storyboard."""

    visual_diversity: float = 0.0
    scene_balance: float = 0.0
    narrative_consistency: float = 0.0
    camera_variety: float = 0.0
    animation_quality: float = 0.0
    budget_efficiency: float = 0.0
    overall_production_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scene package (per-scene aggregated data)
# ---------------------------------------------------------------------------
class ScenePackage(BaseModel):
    """Complete package for a single scene — all planning data aggregated.

    This is what downstream agents (Image, Video, Voice, Rendering) consume
    for each scene.
    """

    scene_id: str = ""
    scene_number: int = 0
    title: str = ""
    narration: str = ""
    duration_seconds: int = 0
    visual_prompt_summary: str = ""
    asset_type: str = ""
    camera_plan: CameraPlan = Field(default_factory=CameraPlan)
    animation_plan: AnimationPlan = Field(default_factory=AnimationPlan)
    visual_plan: VisualPlan = Field(default_factory=VisualPlan)
    transition: str = ""
    priority: str = "medium"  # low, medium, high, critical
    dependencies: list[str] = Field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_tokens: int = 0
    quality_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Storyboard package (final output)
# ---------------------------------------------------------------------------
class StoryboardPackage(BaseModel):
    """The complete storyboard package — final output of the storyboard workflow.

    This is the reusable object that downstream agents (Image, Video,
    Voice, Rendering) consume to generate and render assets.

    Attributes:
        id: Unique identifier for this storyboard package.
        story_analysis: Narrative analysis of the script.
        story_beats: Story beats extracted from the script.
        scenes: Segmented production scenes.
        visual_plans: Visual descriptions for each scene.
        camera_plans: Camera plans for each scene.
        animation_plans: Animation plans for each scene.
        asset_decisions: Asset decisions for each scene.
        continuity: Continuity metadata.
        review: Storyboard review results.
        quality: Quality evaluation scores.
        scene_packages: Aggregated per-scene packages.
        estimated_budget: Total estimated budget.
        estimated_timeline: Estimated production timeline.
        version: Version number.
        created_at: When the package was created.
    """

    id: UUID = Field(default_factory=uuid4)
    story_analysis: StoryAnalysis = Field(default_factory=StoryAnalysis)
    story_beats: StoryBeatResult = Field(default_factory=StoryBeatResult)
    scenes: SceneSegmentationResult = Field(default_factory=SceneSegmentationResult)
    visual_plans: VisualStoryboardResult = Field(default_factory=VisualStoryboardResult)
    camera_plans: CameraPlanResult = Field(default_factory=CameraPlanResult)
    animation_plans: AnimationPlanResult = Field(default_factory=AnimationPlanResult)
    asset_decisions: AssetDecisionResult = Field(default_factory=AssetDecisionResult)
    continuity: ContinuityResult = Field(default_factory=ContinuityResult)
    review: StoryboardReviewResult = Field(default_factory=StoryboardReviewResult)
    quality: StoryboardQualityEvaluation = Field(default_factory=StoryboardQualityEvaluation)
    scene_packages: list[ScenePackage] = Field(default_factory=list)
    estimated_budget: float = 0.0
    estimated_timeline_minutes: int = 0
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_ready(self) -> bool:
        """Check if the storyboard package has minimum required data."""
        return self.scenes.total_scenes > 0 and len(self.scene_packages) > 0

    @property
    def scene_count(self) -> int:
        """Return the number of scenes."""
        return self.scenes.total_scenes

    @property
    def total_estimated_cost(self) -> float:
        """Return total estimated cost across all scenes."""
        return sum(sp.estimated_cost for sp in self.scene_packages)
