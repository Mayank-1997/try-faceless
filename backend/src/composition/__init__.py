"""Video Composition Platform — Phase 10.

Transforms generated assets into finished videos.

Pipeline:
    AssetManifest → CompositionBuilder → CompositionDocument
    → CompositionValidator → RenderPlanner → CompositionOptimizer
    → TimelineCompiler → RenderingPipeline → CompositionRenderer
    → FFmpegCompositionRenderer → QualityValidation → ProjectPackage

The renderer consumes ONLY the CompositionDocument.
"""

from __future__ import annotations

# Schema
from src.composition.schema import (
    AudioMixConfig,
    AudioTrack,
    CameraMotion,
    CameraMotionType,
    CompositionDocument,
    CompositionScene,
    EasingType,
    EncodingProfile,
    ExportFormat,
    ExportProfile,
    ExportResolution,
    ImageAnimation,
    ImageAnimationType,
    LayerType,
    PreviewResult,
    ProjectPackage,
    QualityReport,
    RenderCacheEntry,
    RenderJob,
    RenderMetrics,
    RenderPlan,
    RenderPriority,
    RenderProgress,
    RenderStatus,
    RenderingMetadata,
    SubtitleConfig,
    SubtitleFormat,
    TextOverlay,
    TextType,
    Timeline,
    TimelineClip,
    Track,
    TrackType,
    Transition,
    TransitionType,
    ValidationMetadata,
    VideoEffect,
    VideoEffectType,
)

# Events
from src.composition.events import CompositionEventEmitter, CompositionEvents

# Engines
from src.composition.tracks import TrackSystem
from src.composition.camera import CameraMotionEngine
from src.composition.animation import ImageAnimationEngine
from src.composition.transitions import TransitionEngine
from src.composition.effects import VideoEffectsEngine
from src.composition.text import TextEngine
from src.composition.subtitles import SubtitleEngine
from src.composition.audio import AudioMixer
from src.composition.synchronizer import MediaSynchronizer

# Core pipeline
from src.composition.builder import CompositionBuilder
from src.composition.validator import CompositionValidator
from src.composition.planner import RenderPlanner
from src.composition.optimizer import CompositionOptimizer
from src.composition.timeline_compiler import TimelineCompiler

# Renderer
from src.composition.renderer import CompositionRenderer
from src.composition.ffmpeg_renderer import FFmpegCompositionRenderer

# Pipeline
from src.composition.pipeline import RenderingPipeline

# Export & quality
from src.composition.export import ExportEngine
from src.composition.quality import QualityValidator
from src.composition.render_cache import RenderCache
from src.composition.preview import PreviewEngine

# Queue & progress
from src.composition.render_queue import RenderQueue
from src.composition.progress import ProgressTracker

__all__ = [
    # Schema
    "AudioMixConfig",
    "AudioTrack",
    "CameraMotion",
    "CameraMotionType",
    "CompositionDocument",
    "CompositionScene",
    "EasingType",
    "EncodingProfile",
    "ExportFormat",
    "ExportProfile",
    "ExportResolution",
    "ImageAnimation",
    "ImageAnimationType",
    "LayerType",
    "PreviewResult",
    "ProjectPackage",
    "QualityReport",
    "RenderCacheEntry",
    "RenderJob",
    "RenderMetrics",
    "RenderPlan",
    "RenderPriority",
    "RenderProgress",
    "RenderStatus",
    "RenderingMetadata",
    "SubtitleConfig",
    "SubtitleFormat",
    "TextOverlay",
    "TextType",
    "Timeline",
    "TimelineClip",
    "Track",
    "TrackType",
    "Transition",
    "TransitionType",
    "ValidationMetadata",
    "VideoEffect",
    "VideoEffectType",
    # Events
    "CompositionEventEmitter",
    "CompositionEvents",
    # Engines
    "TrackSystem",
    "CameraMotionEngine",
    "ImageAnimationEngine",
    "TransitionEngine",
    "VideoEffectsEngine",
    "TextEngine",
    "SubtitleEngine",
    "AudioMixer",
    "MediaSynchronizer",
    # Core pipeline
    "CompositionBuilder",
    "CompositionValidator",
    "RenderPlanner",
    "CompositionOptimizer",
    "TimelineCompiler",
    # Renderer
    "CompositionRenderer",
    "FFmpegCompositionRenderer",
    # Pipeline
    "RenderingPipeline",
    # Export & quality
    "ExportEngine",
    "QualityValidator",
    "RenderCache",
    "PreviewEngine",
    # Queue & progress
    "RenderQueue",
    "ProgressTracker",
]
