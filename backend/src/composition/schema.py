"""Video Composition Platform schemas — all Pydantic v2 models.

This module defines every data structure used by the composition platform:
- Composition document (single source of truth for rendering)
- Timeline, tracks, layers, scenes
- Camera motion, image animation, transitions, video effects
- Text overlays, subtitles, audio mixing
- Export profiles, encoding profiles
- Render plan, render cache, render metrics
- Project package (contract for publishing)
- Quality validation, progress tracking
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TrackType(str, Enum):
    """Types of tracks in the timeline."""

    VIDEO = "video"
    IMAGE = "image"
    VOICE = "voice"
    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    SUBTITLE = "subtitle"
    OVERLAY = "overlay"
    ANIMATION = "animation"
    CUSTOM = "custom"


class LayerType(str, Enum):
    """Types of layers within a track."""

    VISUAL = "visual"
    AUDIO = "audio"
    TEXT = "text"
    EFFECT = "effect"
    TRANSITION = "transition"
    OVERLAY = "overlay"


class TransitionType(str, Enum):
    """Supported transition types."""

    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE = "slide"
    PUSH = "push"
    ZOOM = "zoom"
    BLUR = "blur"
    DISSOLVE = "dissolve"
    CUSTOM = "custom"


class EasingType(str, Enum):
    """Easing curves for animations and transitions."""

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    CUBIC = "cubic"
    QUARTIC = "quartic"


class CameraMotionType(str, Enum):
    """Supported camera motion types."""

    PAN = "pan"
    ZOOM = "zoom"
    TILT = "tilt"
    ORBIT = "orbit"
    KEN_BURNS = "ken_burns"
    PARALLAX = "parallax"
    CUSTOM = "custom"


class ImageAnimationType(str, Enum):
    """Supported image animation types."""

    SCALE = "scale"
    TRANSLATE = "translate"
    ROTATE = "rotate"
    OPACITY = "opacity"
    CROP = "crop"
    DEPTH_ILLUSION = "depth_illusion"
    PARALLAX = "parallax"
    MOTION_PRESET = "motion_preset"


class VideoEffectType(str, Enum):
    """Supported video effects."""

    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    COLOR_CORRECTION = "color_correction"
    BLUR = "blur"
    SHARPEN = "sharpen"
    GLOW = "glow"
    NOISE_REDUCTION = "noise_reduction"
    VIGNETTE = "vignette"
    LUT = "lut"


class TextType(str, Enum):
    """Types of text overlays."""

    TITLE = "title"
    LOWER_THIRD = "lower_third"
    CAPTION = "caption"
    CREDITS = "credits"
    WATERMARK = "watermark"
    CALLOUT = "callout"
    ANIMATED_TEXT = "animated_text"


class SubtitleFormat(str, Enum):
    """Subtitle file formats."""

    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"


class ExportFormat(str, Enum):
    """Video export formats."""

    MP4 = "mp4"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"


class ExportResolution(str, Enum):
    """Standard export resolutions."""

    P720 = "1280x720"
    P1080 = "1920x1080"
    P1440 = "2560x1440"
    P2160 = "3840x2160"  # 4K
    SQUARE = "1080x1080"
    PORTRAIT = "1080x1920"
    VERTICAL_720 = "720x1280"


class RenderStatus(str, Enum):
    """Status of a render job."""

    QUEUED = "queued"
    LOADING = "loading"
    VALIDATING = "validating"
    PREPARING = "preparing"
    COMPILING = "compiling"
    COMPOSING = "composing"
    RENDERING = "rendering"
    ENCODING = "encoding"
    VALIDATING_OUTPUT = "validating_output"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class RenderPriority(int, Enum):
    """Priority levels for render queue."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    BACKGROUND = 20


# ---------------------------------------------------------------------------
# Timeline Elements
# ---------------------------------------------------------------------------
class TimelineClip(BaseModel):
    """A single clip on a track in the timeline."""

    id: UUID = Field(default_factory=uuid4)
    track_id: str = ""
    asset_uri: str = ""
    asset_type: str = ""
    start_time: float = 0.0
    duration: float = 0.0
    in_point: float = 0.0  # trim start within the source
    out_point: float | None = None  # trim end within the source
    speed: float = 1.0
    volume: float = 1.0
    opacity: float = 1.0
    position_x: float = 0.0
    position_y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    z_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Track(BaseModel):
    """A track in the timeline (video, audio, subtitle, etc.)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    track_type: TrackType = TrackType.VIDEO
    layer: int = 0
    visible: bool = True
    locked: bool = False
    muted: bool = False
    solo: bool = False
    clips: list[TimelineClip] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_duration(self) -> float:
        """Total duration of all clips on this track."""
        if not self.clips:
            return 0.0
        return max(c.start_time + c.duration for c in self.clips)


class Timeline(BaseModel):
    """The complete timeline for a composition."""

    tracks: list[Track] = Field(default_factory=list)
    total_duration: float = 0.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_track(self, track_id: str) -> Track | None:
        """Get a track by ID."""
        for t in self.tracks:
            if t.id == track_id:
                return t
        return None

    def get_tracks_by_type(self, track_type: TrackType) -> list[Track]:
        """Get all tracks of a given type."""
        return [t for t in self.tracks if t.track_type == track_type]

    def add_track(self, track: Track) -> None:
        """Add a track to the timeline."""
        self.tracks.append(track)
        self._update_duration()

    def _update_duration(self) -> None:
        """Recalculate total duration from all tracks."""
        if not self.tracks:
            self.total_duration = 0.0
        else:
            self.total_duration = max(t.total_duration for t in self.tracks)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
class CompositionScene(BaseModel):
    """A scene within the composition."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    scene_number: int = 0
    scene_id: str = ""  # references the storyboard scene_id
    start_time: float = 0.0
    duration: float = 0.0
    narration: str = ""
    visual_description: str = ""
    camera_plan: dict[str, Any] = Field(default_factory=dict)
    animation_plan: dict[str, Any] = Field(default_factory=dict)
    asset_uris: dict[str, str] = Field(default_factory=dict)
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def end_time(self) -> float:
        """Scene end time."""
        return self.start_time + self.duration


# ---------------------------------------------------------------------------
# Camera Motion
# ---------------------------------------------------------------------------
class CameraMotion(BaseModel):
    """Camera motion configuration for a scene or clip."""

    motion_type: CameraMotionType = CameraMotionType.KEN_BURNS
    start_x: float = 0.0
    start_y: float = 0.0
    start_zoom: float = 1.0
    end_x: float = 0.0
    end_y: float = 0.0
    end_zoom: float = 1.2
    duration: float = 5.0
    easing: EasingType = EasingType.EASE_IN_OUT
    custom_path: list[dict[str, float]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Image Animation
# ---------------------------------------------------------------------------
class ImageAnimation(BaseModel):
    """Animation configuration for an image clip."""

    animation_type: ImageAnimationType = ImageAnimationType.SCALE
    start_value: float = 1.0
    end_value: float = 1.1
    duration: float = 5.0
    easing: EasingType = EasingType.EASE_IN_OUT
    direction: str = "center"  # for translate/slide
    preset_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------
class Transition(BaseModel):
    """A transition between two scenes or clips."""

    transition_type: TransitionType = TransitionType.FADE
    duration: float = 1.0
    easing: EasingType = EasingType.EASE_IN_OUT
    from_scene_id: str = ""
    to_scene_id: str = ""
    from_clip_id: str = ""
    to_clip_id: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Video Effect
# ---------------------------------------------------------------------------
class VideoEffect(BaseModel):
    """A video effect applied to a clip or track."""

    effect_type: VideoEffectType = VideoEffectType.BRIGHTNESS
    intensity: float = 1.0
    params: dict[str, Any] = Field(default_factory=dict)
    target_clip_id: str | None = None
    target_track_id: str | None = None


# ---------------------------------------------------------------------------
# Text Overlay
# ---------------------------------------------------------------------------
class TextOverlay(BaseModel):
    """A text overlay on the video."""

    id: UUID = Field(default_factory=uuid4)
    text_type: TextType = TextType.TITLE
    content: str = ""
    font_family: str = "Arial"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    background_color: str | None = None
    position_x: float = 0.5  # normalized 0-1
    position_y: float = 0.5
    start_time: float = 0.0
    duration: float = 3.0
    opacity: float = 1.0
    animation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Subtitle Configuration
# ---------------------------------------------------------------------------
class SubtitleConfig(BaseModel):
    """Subtitle configuration for the composition."""

    format: SubtitleFormat = SubtitleFormat.SRT
    file_uri: str = ""
    font_family: str = "Arial"
    font_size: int = 24
    font_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 2
    highlight_color: str = "#FFFF00"
    word_highlight: bool = False
    sentence_highlight: bool = False
    speaker_labels: bool = False
    language: str = "en"
    animated: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audio Configuration
# ---------------------------------------------------------------------------
class AudioTrack(BaseModel):
    """An audio track configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    track_type: TrackType = TrackType.VOICE
    file_uri: str = ""
    volume: float = 1.0
    start_time: float = 0.0
    duration: float = 0.0
    fade_in_duration: float = 0.0
    fade_out_duration: float = 0.0
    ducking: bool = False
    ducking_threshold: float = -20.0  # dB
    ducking_amount: float = 0.3
    normalized: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AudioMixConfig(BaseModel):
    """Audio mixing configuration for the composition."""

    voice_tracks: list[AudioTrack] = Field(default_factory=list)
    music_tracks: list[AudioTrack] = Field(default_factory=list)
    sfx_tracks: list[AudioTrack] = Field(default_factory=list)
    master_volume: float = 1.0
    voice_normalization: bool = True
    music_ducking: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Export Profile
# ---------------------------------------------------------------------------
class ExportProfile(BaseModel):
    """Export profile for the final video."""

    format: ExportFormat = ExportFormat.MP4
    resolution: str = "1920x1080"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5M"
    audio_bitrate: str = "192k"
    preset: str = "medium"
    crf: int = 23
    pixel_format: str = "yuv420p"
    hardware_acceleration: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EncodingProfile(BaseModel):
    """Encoding profile preset."""

    name: str = "1080p"
    resolution: ExportResolution = ExportResolution.P1080
    fps: int = 30
    codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "5M"
    audio_bitrate: str = "192k"
    preset: str = "medium"
    crf: int = 23
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rendering Metadata
# ---------------------------------------------------------------------------
class RenderingMetadata(BaseModel):
    """Metadata about the rendering process."""

    estimated_duration: float = 0.0
    estimated_render_time: float = 0.0
    estimated_memory_mb: int = 0
    estimated_output_size_mb: int = 0
    estimated_cpu_usage: float = 0.0
    estimated_gpu_usage: float = 0.0
    rendering_complexity: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation Metadata
# ---------------------------------------------------------------------------
class ValidationMetadata(BaseModel):
    """Validation results for the composition."""

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Composition Document
# ---------------------------------------------------------------------------
class CompositionDocument(BaseModel):
    """The single source of truth for rendering.

    The renderer consumes ONLY this document.  It contains the complete
    timeline, all tracks, scenes, assets, audio, subtitles, transitions,
    animations, effects, text overlays, and export settings.
    """

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    version: int = 1
    timeline: Timeline = Field(default_factory=Timeline)
    scenes: list[CompositionScene] = Field(default_factory=list)
    camera_motions: dict[str, CameraMotion] = Field(default_factory=dict)  # scene_id -> motion
    image_animations: dict[str, ImageAnimation] = Field(default_factory=dict)  # clip_id -> animation
    transitions: list[Transition] = Field(default_factory=list)
    effects: list[VideoEffect] = Field(default_factory=list)
    text_overlays: list[TextOverlay] = Field(default_factory=list)
    subtitle_config: SubtitleConfig | None = None
    audio_config: AudioMixConfig = Field(default_factory=AudioMixConfig)
    export_profile: ExportProfile = Field(default_factory=ExportProfile)
    rendering_metadata: RenderingMetadata = Field(default_factory=RenderingMetadata)
    validation_metadata: ValidationMetadata = Field(default_factory=ValidationMetadata)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_duration(self) -> float:
        """Total composition duration in seconds."""
        return self.timeline.total_duration

    @property
    def scene_count(self) -> int:
        """Number of scenes."""
        return len(self.scenes)

    @property
    def track_count(self) -> int:
        """Number of tracks."""
        return len(self.timeline.tracks)

    @property
    def is_valid(self) -> bool:
        """Check if the composition has been validated."""
        return self.validation_metadata.valid

    def to_hash(self) -> str:
        """Generate a deterministic hash for cache keys."""
        import hashlib
        import json
        data = self.model_dump_json(exclude={"id", "created_at", "metadata"})
        return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Render Plan
# ---------------------------------------------------------------------------
class RenderPlan(BaseModel):
    """A plan for rendering a composition.

    Generated by the RenderPlanner before rendering begins.
    Contains estimates for time, CPU, memory, disk, GPU, and
    optimization suggestions.
    """

    id: UUID = Field(default_factory=uuid4)
    composition_id: UUID = Field(default_factory=uuid4)
    estimated_execution_time: float = 0.0
    estimated_cpu_usage: float = 0.0
    estimated_memory_mb: int = 0
    estimated_disk_mb: int = 0
    estimated_gpu_usage: float = 0.0
    rendering_complexity: float = 0.0
    expected_output_size_mb: int = 0
    potential_bottlenecks: list[str] = Field(default_factory=list)
    optimization_suggestions: list[str] = Field(default_factory=list)
    scene_render_order: list[str] = Field(default_factory=list)
    parallelizable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Render Metrics
# ---------------------------------------------------------------------------
class RenderMetrics(BaseModel):
    """Metrics collected during rendering."""

    render_time_seconds: float = 0.0
    encoding_time_seconds: float = 0.0
    total_frames: int = 0
    dropped_frames: int = 0
    average_fps: float = 0.0
    peak_memory_mb: int = 0
    cpu_usage: float = 0.0
    gpu_usage: float = 0.0
    output_size_bytes: int = 0
    output_duration_seconds: float = 0.0
    output_resolution: str = ""
    output_fps: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Quality Report
# ---------------------------------------------------------------------------
class QualityReport(BaseModel):
    """Quality validation report for a rendered video."""

    resolution_valid: bool = True
    duration_valid: bool = True
    subtitle_sync_valid: bool = True
    audio_sync_valid: bool = True
    no_dropped_frames: bool = True
    all_assets_present: bool = True
    encoding_success: bool = True
    output_integrity: bool = True
    overall_pass: bool = True
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Render Job
# ---------------------------------------------------------------------------
class RenderJob(BaseModel):
    """A render job in the render queue."""

    id: UUID = Field(default_factory=uuid4)
    composition_id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    status: RenderStatus = RenderStatus.QUEUED
    priority: RenderPriority = RenderPriority.NORMAL
    output_path: str = ""
    retry_count: int = 0
    max_retries: int = 2
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metrics: RenderMetrics = Field(default_factory=RenderMetrics)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if the job is in a terminal state."""
        return self.status in (RenderStatus.COMPLETED, RenderStatus.FAILED, RenderStatus.CANCELLED)

    @property
    def execution_time_seconds(self) -> float:
        """Calculate execution time if the job has started."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


# ---------------------------------------------------------------------------
# Render Progress
# ---------------------------------------------------------------------------
class RenderProgress(BaseModel):
    """Progress tracking for a render job."""

    job_id: UUID = Field(default_factory=uuid4)
    status: RenderStatus = RenderStatus.QUEUED
    progress_percentage: float = 0.0
    current_stage: str = ""
    stages_completed: list[str] = Field(default_factory=list)
    estimated_time_remaining: float = 0.0
    frames_processed: int = 0
    total_frames: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Render Cache Entry
# ---------------------------------------------------------------------------
class RenderCacheEntry(BaseModel):
    """A cached render result."""

    composition_hash: str = ""
    output_path: str = ""
    output_size_bytes: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Project Package
# ---------------------------------------------------------------------------
class ProjectPackage(BaseModel):
    """The final output package for a video project.

    This is the contract for future Publishing modules (Phase 12).
    Contains everything needed to publish a video.
    """

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    composition_document: CompositionDocument = Field(default_factory=CompositionDocument)
    final_video_path: str = ""
    final_video_uri: str = ""
    thumbnail_path: str = ""
    thumbnail_uri: str = ""
    subtitle_files: list[str] = Field(default_factory=list)
    timeline: Timeline = Field(default_factory=Timeline)
    waveforms: dict[str, str] = Field(default_factory=dict)  # track_id -> waveform URI
    metadata: dict[str, Any] = Field(default_factory=dict)
    render_report: RenderMetrics = Field(default_factory=RenderMetrics)
    quality_report: QualityReport = Field(default_factory=QualityReport)
    performance_metrics: RenderMetrics = Field(default_factory=RenderMetrics)
    cost_summary: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @property
    def is_complete(self) -> bool:
        """Check if the project package is complete."""
        return bool(self.final_video_path) and self.quality_report.overall_pass


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
class PreviewResult(BaseModel):
    """Result of a preview generation."""

    preview_path: str = ""
    preview_uri: str = ""
    resolution: str = "640x360"
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
