"""Workflow State — strongly-typed state object for the LangGraph workflow.

Every LangGraph node receives ``WorkflowState`` and returns
``WorkflowState``.  No dictionaries, no untyped data.

The state contains all data produced by the workflow pipeline:

- **Project metadata**: ID, user, status, input type.
- **Topic**: Expanded topic (if input was a raw topic).
- **Research**: Sources, key facts, summary.
- **Script**: Full script content, structure, word count.
- **Storyboard**: High-level narrative structure.
- **Scenes**: Ordered list of scene definitions with all visual/audio metadata.
- **Assets**: Generated assets (images, videos, voice, subtitles).
- **Voice**: Voice generation settings and results.
- **Rendering**: Render job status and output path.
- **SEO**: Optimized title, description, tags.
- **Publishing**: YouTube publish status and metadata.
- **Analytics**: Post-publish analytics snapshots.
- **Cost**: Running cost total.
- **Token Usage**: Running token total.
- **Execution Status**: Current agent, step, errors, checkpoints.

Usage in LangGraph::

    def research_node(state: WorkflowState) -> WorkflowState:
        state.research = ResearchData(...)
        state.current_agent = AgentType.SCENE_PLANNER
        return state
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.enums import (
    AgentType,
    AssetDecision,
    AssetStatus,
    AssetType,
    CameraAngle,
    CameraMotion,
    JobStatus,
    ProjectInputType,
    ProjectStatus,
    PublishStatus,
    TransitionType,
    VisualType,
    VoiceGender,
    VoiceTone,
)


# ---------------------------------------------------------------------------
# Sub-state models
# ---------------------------------------------------------------------------
class ProjectInfo(BaseModel):
    """Project-level metadata."""

    project_id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    name: str = ""
    input_type: ProjectInputType = ProjectInputType.TOPIC
    status: ProjectStatus = ProjectStatus.DRAFT
    target_duration_seconds: int | None = None
    target_resolution: str = "1920x1080"


class TopicData(BaseModel):
    """Topic expansion result from the Topic Agent."""

    raw_topic: str = ""
    expanded_topic: str = ""
    keywords: list[str] = Field(default_factory=list)
    target_audience: str = ""
    content_angle: str = ""


class ResearchSource(BaseModel):
    """A single research source."""

    url: str = ""
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0


class ResearchData(BaseModel):
    """Research result from the Research Agent."""

    query: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    summary: str = ""
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScriptData(BaseModel):
    """Script result from the Script Writer Agent."""

    version: int = 1
    title: str = ""
    content: str = ""
    hook: str = ""
    intro: str = ""
    body: str = ""
    outro: str = ""
    word_count: int = 0
    estimated_duration_seconds: int = 0
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    quality_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StoryboardData(BaseModel):
    """Storyboard / narrative structure from the Story Planner Agent."""

    narrative_structure: str = ""
    act_count: int = 0
    beats: list[str] = Field(default_factory=list)
    pacing_notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneData(BaseModel):
    """A single scene definition from the Scene Planner Agent."""

    scene_number: int = 0
    title: str = ""
    narration: str = ""
    start_time: float | None = None
    end_time: float | None = None
    estimated_duration: float | None = None
    visual_importance_score: float | None = None
    audience_attention_score: float | None = None
    visual_type: VisualType | None = None
    asset_decision: AssetDecision | None = None
    camera_angle: CameraAngle | None = None
    camera_motion: CameraMotion | None = None
    lens: str | None = None
    lighting: str | None = None
    composition: str | None = None
    emotion: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    transition: TransitionType | None = None
    music_suggestion: str | None = None
    sound_effects: list[str] = Field(default_factory=list)
    image_prompt: str | None = None
    video_prompt: str | None = None
    negative_prompt: str | None = None
    animation_instructions: str | None = None
    subtitle_text: str | None = None
    voice_timing: dict[str, Any] | None = None


class AssetData(BaseModel):
    """A single generated asset."""

    asset_id: UUID = Field(default_factory=uuid4)
    scene_number: int | None = None
    asset_type: AssetType = AssetType.IMAGE
    status: AssetStatus = AssetStatus.PLANNED
    provider: str = ""
    file_path: str = ""
    file_size_bytes: int = 0
    cost_usd: float = 0.0
    quality_score: float | None = None
    storage_uri: str = ""
    content_hash: str = ""
    checksum: str = ""
    version: int = 1
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceData(BaseModel):
    """Voice generation settings and results."""

    language: str = "en-US"
    voice_name: str | None = None
    gender: VoiceGender | None = None
    tone: VoiceTone | None = None
    speaking_rate: float = 1.0
    pitch: float = 0.0
    total_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0


class RenderingData(BaseModel):
    """Rendering job status and output."""

    status: JobStatus = JobStatus.QUEUED
    output_path: str = ""
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    resolution: str = "1920x1080"
    fps: int = 30
    render_time_seconds: float = 0.0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SEOData(BaseModel):
    """SEO optimization result."""

    title: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    category: str = ""
    keywords: list[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0


class PublishingData(BaseModel):
    """YouTube publishing status and metadata."""

    status: PublishStatus = PublishStatus.NOT_PUBLISHED
    youtube_video_id: str | None = None
    privacy_status: str = "private"
    published_at: datetime | None = None
    error_message: str | None = None


class AnalyticsData(BaseModel):
    """Post-publish analytics snapshot."""

    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    watch_time_hours: float = 0.0
    average_view_duration_seconds: float = 0.0
    click_through_rate: float = 0.0
    recorded_at: datetime | None = None


class CostData(BaseModel):
    """Running cost total for the project."""

    total_cost_usd: float = 0.0
    llm_cost_usd: float = 0.0
    image_cost_usd: float = 0.0
    video_cost_usd: float = 0.0
    voice_cost_usd: float = 0.0
    render_cost_usd: float = 0.0

    def add(self, amount: float, category: str = "llm") -> None:
        """Add a cost to the total and the appropriate category."""
        self.total_cost_usd += amount
        if category == "llm":
            self.llm_cost_usd += amount
        elif category == "image":
            self.image_cost_usd += amount
        elif category == "video":
            self.video_cost_usd += amount
        elif category == "voice":
            self.voice_cost_usd += amount
        elif category == "render":
            self.render_cost_usd += amount


class TokenUsageData(BaseModel):
    """Running token usage total for the project."""

    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    def add(self, input_t: int = 0, output_t: int = 0, cached_t: int = 0) -> None:
        """Add token counts to the totals."""
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.cached_tokens += cached_t
        self.total_tokens = self.input_tokens + self.output_tokens + self.cached_tokens


class NodeExecutionRecord(BaseModel):
    """Record of a single node execution within a workflow."""

    node_name: str = ""
    node_type: str = ""
    status: str = "pending"  # pending, running, succeeded, failed, skipped, retried
    started_at: datetime | None = None
    completed_at: datetime | None = None
    execution_time_ms: int = 0
    retry_count: int = 0
    error_message: str | None = None
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    output_summary: str = ""

    @property
    def duration_seconds(self) -> float:
        """Execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class WorkflowMetadata(BaseModel):
    """Arbitrary metadata associated with a workflow execution."""

    workflow_name: str = ""
    workflow_version: str = "1.0.0"
    content_type: str = "youtube_video"
    tags: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class ExecutionStatus(BaseModel):
    """Workflow execution tracking."""

    current_agent: AgentType | None = None
    completed_agents: list[AgentType] = Field(default_factory=list)
    failed_agents: list[AgentType] = Field(default_factory=list)
    skipped_agents: list[AgentType] = Field(default_factory=list)
    current_step: str = ""
    current_node: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkpoint_data: dict[str, Any] = Field(default_factory=dict)
    checkpoint_ref: str | None = None
    retry_count: int = 0
    timeout_seconds: int | None = None
    node_history: list[NodeExecutionRecord] = Field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100.0

    @property
    def is_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self.current_node != "" and self.completed_at is None

    def mark_agent_complete(self, agent: AgentType) -> None:
        """Mark an agent as completed."""
        if agent not in self.completed_agents:
            self.completed_agents.append(agent)
        self.updated_at = datetime.now(timezone.utc)

    def mark_agent_failed(self, agent: AgentType, error: str) -> None:
        """Mark an agent as failed."""
        if agent not in self.failed_agents:
            self.failed_agents.append(agent)
        self.errors.append(f"{agent.value}: {error}")
        self.updated_at = datetime.now(timezone.utc)

    def mark_agent_skipped(self, agent: AgentType) -> None:
        """Mark an agent as skipped."""
        if agent not in self.skipped_agents:
            self.skipped_agents.append(agent)
        self.updated_at = datetime.now(timezone.utc)

    def record_node(self, record: NodeExecutionRecord) -> None:
        """Add a node execution record to the history."""
        self.node_history.append(record)
        self.updated_at = datetime.now(timezone.utc)

    def get_node_history(self, node_name: str | None = None) -> list[NodeExecutionRecord]:
        """Get node execution history, optionally filtered by node name."""
        if node_name:
            return [r for r in self.node_history if r.node_name == node_name]
        return list(self.node_history)

    def mark_completed(self) -> None:
        """Mark the workflow as completed."""
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = self.completed_at


# ---------------------------------------------------------------------------
# Root WorkflowState
# ---------------------------------------------------------------------------
class WorkflowState(BaseModel):
    """Root strongly-typed state object for the LangGraph workflow.

    Every LangGraph node receives this object and returns it (modified).
    No dictionaries, no untyped data — all fields are explicit Pydantic
    models with validation.

    Attributes:
        project: Project-level metadata.
        topic: Topic expansion data.
        research: Research results.
        script: Script content.
        storyboard: Narrative structure.
        scenes: Ordered list of scene definitions.
        assets: Generated assets (images, videos, voice, subtitles).
        voice: Voice generation settings.
        rendering: Rendering job status.
        seo: SEO optimization data.
        publishing: Publishing status.
        analytics: Post-publish analytics.
        cost: Running cost total.
        token_usage: Running token total.
        execution: Execution tracking.
        execution_id: Unique identifier for this workflow execution.
        workflow_id: Identifier for the workflow definition.
        metadata: Workflow-level metadata (name, version, tags).
        correlation_id: Correlation ID for distributed tracing.
        trace_id: Trace ID for OpenTelemetry compatibility.
    """

    project: ProjectInfo = Field(default_factory=ProjectInfo)
    topic: TopicData = Field(default_factory=TopicData)
    research: ResearchData = Field(default_factory=ResearchData)
    script: ScriptData = Field(default_factory=ScriptData)
    storyboard: StoryboardData = Field(default_factory=StoryboardData)
    scenes: list[SceneData] = Field(default_factory=list)
    assets: list[AssetData] = Field(default_factory=list)
    voice: VoiceData = Field(default_factory=VoiceData)
    rendering: RenderingData = Field(default_factory=RenderingData)
    seo: SEOData = Field(default_factory=SEOData)
    publishing: PublishingData = Field(default_factory=PublishingData)
    analytics: AnalyticsData = Field(default_factory=AnalyticsData)
    cost: CostData = Field(default_factory=CostData)
    token_usage: TokenUsageData = Field(default_factory=TokenUsageData)
    execution: ExecutionStatus = Field(default_factory=ExecutionStatus)

    # --- Phase 4: Orchestration tracking fields ---
    execution_id: UUID = Field(default_factory=uuid4)
    workflow_id: str = ""
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    correlation_id: str | None = None
    trace_id: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def add_cost(self, amount: float, category: str = "llm") -> None:
        """Add a cost to the running total."""
        self.cost.add(amount, category)

    def add_tokens(self, input_t: int = 0, output_t: int = 0, cached_t: int = 0) -> None:
        """Add token usage to the running total."""
        self.token_usage.add(input_t, output_t, cached_t)

    def get_scene(self, scene_number: int) -> SceneData | None:
        """Get a scene by its number.

        Args:
            scene_number: The scene's sequential number.

        Returns:
            The ``SceneData`` if found, ``None`` otherwise.
        """
        for scene in self.scenes:
            if scene.scene_number == scene_number:
                return scene
        return None

    def get_assets_for_scene(self, scene_number: int) -> list[AssetData]:
        """Get all assets associated with a scene.

        Args:
            scene_number: The scene's sequential number.

        Returns:
            List of ``AssetData`` for the scene.
        """
        return [a for a in self.assets if a.scene_number == scene_number]

    @property
    def is_complete(self) -> bool:
        """Check if the workflow has completed all steps."""
        return (
            len(self.execution.completed_agents) > 0
            and len(self.execution.failed_agents) == 0
            and self.rendering.status == JobStatus.COMPLETED
        )

    @property
    def has_failures(self) -> bool:
        """Check if any agents have failed."""
        return len(self.execution.failed_agents) > 0

    @property
    def total_cost_usd(self) -> float:
        """Total cost in USD across all categories."""
        return self.cost.total_cost_usd

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed."""
        return self.token_usage.total_tokens

    @property
    def execution_time_seconds(self) -> float:
        """Total execution time in seconds."""
        if self.execution.completed_at:
            return (self.execution.completed_at - self.execution.started_at).total_seconds()
        return (datetime.now(timezone.utc) - self.execution.started_at).total_seconds()
