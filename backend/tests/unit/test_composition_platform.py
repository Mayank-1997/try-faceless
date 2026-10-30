"""Comprehensive tests for the Video Composition Platform (Phase 10).

Covers:
- Schema tests (all models, enums, defaults, computed properties)
- Track system tests
- Camera motion engine tests
- Image animation engine tests
- Transition engine tests
- Video effects engine tests
- Text engine tests
- Subtitle engine tests
- Audio mixer tests
- Media synchronizer tests
- Composition builder tests
- Composition validator tests
- Render planner tests
- Composition optimizer tests
- Timeline compiler tests
- FFmpeg renderer tests
- Rendering pipeline tests
- Export engine tests
- Quality validator tests
- Render cache tests
- Preview engine tests
- Render queue tests
- Progress tracker tests
- Events tests
- Integration test (full pipeline)
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

import pytest


def run_async(coro):
    """Run an async coroutine synchronously (Python 3.12+ compatible)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("Cannot run in a running event loop")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

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
from src.composition.events import CompositionEventEmitter, CompositionEvents
from src.composition.tracks import TrackSystem
from src.composition.camera import CameraMotionEngine
from src.composition.animation import ImageAnimationEngine
from src.composition.transitions import TransitionEngine
from src.composition.effects import VideoEffectsEngine
from src.composition.text import TextEngine
from src.composition.subtitles import SubtitleEngine
from src.composition.audio import AudioMixer
from src.composition.synchronizer import MediaSynchronizer
from src.composition.builder import CompositionBuilder
from src.composition.validator import CompositionValidator
from src.composition.planner import RenderPlanner
from src.composition.optimizer import CompositionOptimizer
from src.composition.timeline_compiler import TimelineCompiler
from src.composition.renderer import CompositionRenderer
from src.composition.ffmpeg_renderer import FFmpegCompositionRenderer
from src.composition.pipeline import RenderingPipeline
from src.composition.export import ExportEngine
from src.composition.quality import QualityValidator
from src.composition.render_cache import RenderCache
from src.composition.preview import PreviewEngine
from src.composition.render_queue import RenderQueue
from src.composition.progress import ProgressTracker
from src.generation.schema import (
    AssetManifest,
    GeneratedAsset,
    JobStatus,
    SceneAssetManifest,
)


# ===========================================================================
# Schema Tests
# ===========================================================================
class TestSchema:
    def test_track_type_values(self):
        assert TrackType.VIDEO == "video"
        assert TrackType.SUBTITLE == "subtitle"
        assert TrackType.CUSTOM == "custom"

    def test_transition_type_values(self):
        assert TransitionType.FADE == "fade"
        assert TransitionType.CROSSFADE == "crossfade"
        assert TransitionType.CUSTOM == "custom"

    def test_easing_type_values(self):
        assert EasingType.LINEAR == "linear"
        assert EasingType.EASE_IN_OUT == "ease_in_out"

    def test_camera_motion_type_values(self):
        assert CameraMotionType.KEN_BURNS == "ken_burns"
        assert CameraMotionType.PARALLAX == "parallax"

    def test_image_animation_type_values(self):
        assert ImageAnimationType.SCALE == "scale"
        assert ImageAnimationType.OPACITY == "opacity"

    def test_video_effect_type_values(self):
        assert VideoEffectType.BLUR == "blur"
        assert VideoEffectType.VIGNETTE == "vignette"
        assert VideoEffectType.LUT == "lut"

    def test_text_type_values(self):
        assert TextType.TITLE == "title"
        assert TextType.WATERMARK == "watermark"

    def test_subtitle_format_values(self):
        assert SubtitleFormat.SRT == "srt"
        assert SubtitleFormat.VTT == "vtt"

    def test_export_format_values(self):
        assert ExportFormat.MP4 == "mp4"
        assert ExportFormat.MOV == "mov"
        assert ExportFormat.MKV == "mkv"

    def test_export_resolution_values(self):
        assert ExportResolution.P1080 == "1920x1080"
        assert ExportResolution.P2160 == "3840x2160"

    def test_render_status_values(self):
        assert RenderStatus.QUEUED == "queued"
        assert RenderStatus.COMPLETED == "completed"
        assert RenderStatus.FAILED == "failed"

    def test_render_priority_ordering(self):
        assert RenderPriority.CRITICAL < RenderPriority.HIGH
        assert RenderPriority.HIGH < RenderPriority.NORMAL
        assert RenderPriority.NORMAL < RenderPriority.LOW

    def test_timeline_clip_defaults(self):
        clip = TimelineClip()
        assert clip.duration == 0.0
        assert clip.opacity == 1.0
        assert clip.scale == 1.0
        assert clip.speed == 1.0

    def test_track_defaults(self):
        track = Track()
        assert track.track_type == TrackType.VIDEO
        assert track.visible is True
        assert track.locked is False
        assert track.clips == []

    def test_track_total_duration(self):
        track = Track()
        track.clips = [
            TimelineClip(start_time=0.0, duration=5.0),
            TimelineClip(start_time=5.0, duration=3.0),
        ]
        assert track.total_duration == 8.0

    def test_track_total_duration_empty(self):
        track = Track()
        assert track.total_duration == 0.0

    def test_timeline_get_track(self):
        t = Track(id="t1", name="Video")
        timeline = Timeline(tracks=[t])
        assert timeline.get_track("t1") is t
        assert timeline.get_track("nonexistent") is None

    def test_timeline_get_tracks_by_type(self):
        v1 = Track(id="v1", track_type=TrackType.VIDEO)
        v2 = Track(id="v2", track_type=TrackType.VIDEO)
        a1 = Track(id="a1", track_type=TrackType.VOICE)
        timeline = Timeline(tracks=[v1, v2, a1])
        video_tracks = timeline.get_tracks_by_type(TrackType.VIDEO)
        assert len(video_tracks) == 2
        audio_tracks = timeline.get_tracks_by_type(TrackType.VOICE)
        assert len(audio_tracks) == 1

    def test_timeline_add_track(self):
        timeline = Timeline()
        track = Track(id="t1")
        timeline.add_track(track)
        assert len(timeline.tracks) == 1
        assert timeline.total_duration == 0.0

    def test_composition_scene_end_time(self):
        scene = CompositionScene(start_time=5.0, duration=10.0)
        assert scene.end_time == 15.0

    def test_composition_document_defaults(self):
        doc = CompositionDocument()
        assert doc.version == 1
        assert doc.scene_count == 0
        assert doc.track_count == 0
        assert doc.total_duration == 0.0
        assert doc.is_valid is True

    def test_composition_document_to_hash(self):
        doc1 = CompositionDocument(project_id="p1")
        doc2 = CompositionDocument(project_id="p1")
        # Same content -> same hash
        assert doc1.to_hash() == doc2.to_hash()
        doc3 = CompositionDocument(project_id="p2")
        # Different content -> different hash
        assert doc1.to_hash() != doc3.to_hash()

    def test_export_profile_defaults(self):
        ep = ExportProfile()
        assert ep.format == ExportFormat.MP4
        assert ep.width == 1920
        assert ep.height == 1080
        assert ep.fps == 30
        assert ep.codec == "libx264"

    def test_render_job_is_terminal(self):
        job = RenderJob(status=RenderStatus.COMPLETED)
        assert job.is_terminal is True
        job2 = RenderJob(status=RenderStatus.QUEUED)
        assert job2.is_terminal is False

    def test_render_job_execution_time(self):
        job = RenderJob()
        assert job.execution_time_seconds == 0.0
        job.started_at = datetime.now(timezone.utc)
        assert job.execution_time_seconds > 0.0

    def test_project_package_is_complete(self):
        pkg = ProjectPackage()
        assert pkg.is_complete is False
        pkg.final_video_path = "/tmp/video.mp4"
        pkg.quality_report.overall_pass = True
        assert pkg.is_complete is True

    def test_render_cache_entry_defaults(self):
        entry = RenderCacheEntry()
        assert entry.hit_count == 0
        assert entry.composition_hash == ""

    def test_quality_report_defaults(self):
        report = QualityReport()
        assert report.overall_pass is True
        assert report.issues == []

    def test_render_metrics_defaults(self):
        metrics = RenderMetrics()
        assert metrics.render_time_seconds == 0.0
        assert metrics.total_frames == 0


# ===========================================================================
# Track System Tests
# ===========================================================================
class TestTrackSystem:
    def test_create_track(self):
        ts = TrackSystem()
        track = ts.create_track("Video", TrackType.VIDEO, layer=0)
        assert track.name == "Video"
        assert track.track_type == TrackType.VIDEO
        assert ts.track_count == 1

    def test_add_track(self):
        ts = TrackSystem()
        track = Track(name="Audio", track_type=TrackType.VOICE)
        ts.add_track(track)
        assert ts.track_count == 1

    def test_remove_track(self):
        ts = TrackSystem()
        track = ts.create_track("Video", TrackType.VIDEO)
        assert ts.remove_track(track.id) is True
        assert ts.track_count == 0
        assert ts.remove_track("nonexistent") is False

    def test_get_track(self):
        ts = TrackSystem()
        track = ts.create_track("Video", TrackType.VIDEO)
        assert ts.get_track(track.id) is track
        assert ts.get_track("nonexistent") is None

    def test_get_tracks_by_type(self):
        ts = TrackSystem()
        ts.create_track("V1", TrackType.VIDEO, layer=0)
        ts.create_track("V2", TrackType.VIDEO, layer=1)
        ts.create_track("A1", TrackType.VOICE, layer=0)
        video_tracks = ts.get_tracks_by_type(TrackType.VIDEO)
        assert len(video_tracks) == 2
        # Should be ordered by layer
        assert video_tracks[0].layer <= video_tracks[1].layer

    def test_get_all_tracks_ordered(self):
        ts = TrackSystem()
        ts.create_track("High", TrackType.VIDEO, layer=5)
        ts.create_track("Low", TrackType.VIDEO, layer=0)
        all_tracks = ts.get_all_tracks()
        assert all_tracks[0].layer <= all_tracks[1].layer

    def test_get_video_tracks(self):
        ts = TrackSystem()
        ts.create_track("V1", TrackType.VIDEO)
        ts.create_track("A1", TrackType.VOICE)
        assert len(ts.get_video_tracks()) == 1

    def test_get_audio_tracks(self):
        ts = TrackSystem()
        ts.create_track("V1", TrackType.VIDEO)
        ts.create_track("Voice", TrackType.VOICE)
        ts.create_track("Music", TrackType.MUSIC)
        ts.create_track("SFX", TrackType.SOUND_EFFECT)
        audio = ts.get_audio_tracks()
        assert len(audio) == 3

    def test_clear(self):
        ts = TrackSystem()
        ts.create_track("V1", TrackType.VIDEO)
        ts.create_track("A1", TrackType.VOICE)
        ts.clear()
        assert ts.track_count == 0


# ===========================================================================
# Camera Motion Engine Tests
# ===========================================================================
class TestCameraMotionEngine:
    def test_ken_burns(self):
        engine = CameraMotionEngine()
        motion = engine.ken_burns(duration=5.0, start_zoom=1.0, end_zoom=1.2)
        assert motion.motion_type == CameraMotionType.KEN_BURNS
        assert motion.duration == 5.0
        assert motion.start_zoom == 1.0
        assert motion.end_zoom == 1.2

    def test_pan(self):
        engine = CameraMotionEngine()
        motion = engine.pan(duration=3.0, start_x=0.0, end_x=0.1)
        assert motion.motion_type == CameraMotionType.PAN
        assert motion.duration == 3.0

    def test_zoom(self):
        engine = CameraMotionEngine()
        motion = engine.zoom(duration=4.0, start_zoom=1.0, end_zoom=1.5)
        assert motion.motion_type == CameraMotionType.ZOOM
        assert motion.end_zoom == 1.5

    def test_tilt(self):
        engine = CameraMotionEngine()
        motion = engine.tilt(duration=3.0, start_y=0.0, end_y=0.1)
        assert motion.motion_type == CameraMotionType.TILT

    def test_orbit(self):
        engine = CameraMotionEngine()
        motion = engine.orbit(duration=5.0, radius=0.1)
        assert motion.motion_type == CameraMotionType.ORBIT

    def test_parallax(self):
        engine = CameraMotionEngine()
        motion = engine.parallax(duration=5.0, depth=0.05)
        assert motion.motion_type == CameraMotionType.PARALLAX

    def test_custom_path(self):
        engine = CameraMotionEngine()
        points = [{"x": 0.0, "y": 0.0, "zoom": 1.0}, {"x": 0.1, "y": 0.1, "zoom": 1.2}]
        motion = engine.custom_path(points, duration=5.0)
        assert motion.motion_type == CameraMotionType.CUSTOM
        assert len(motion.custom_path) == 2

    def test_to_ffmpeg_filter_zoom(self):
        engine = CameraMotionEngine()
        motion = engine.zoom(duration=5.0)
        filt = engine.to_ffmpeg_filter(motion, width=1920, height=1080, fps=30)
        assert "zoompan" in filt

    def test_to_ffmpeg_filter_pan(self):
        engine = CameraMotionEngine()
        motion = engine.pan(duration=5.0)
        filt = engine.to_ffmpeg_filter(motion, width=1920, height=1080, fps=30)
        assert "crop" in filt


# ===========================================================================
# Image Animation Engine Tests
# ===========================================================================
class TestImageAnimationEngine:
    def test_scale(self):
        engine = ImageAnimationEngine()
        anim = engine.scale(duration=5.0, start=1.0, end=1.1)
        assert anim.animation_type == ImageAnimationType.SCALE
        assert anim.start_value == 1.0
        assert anim.end_value == 1.1

    def test_translate(self):
        engine = ImageAnimationEngine()
        anim = engine.translate(duration=3.0, direction="right")
        assert anim.animation_type == ImageAnimationType.TRANSLATE
        assert anim.direction == "right"

    def test_rotate(self):
        engine = ImageAnimationEngine()
        anim = engine.rotate(duration=5.0, start=0.0, end=5.0)
        assert anim.animation_type == ImageAnimationType.ROTATE

    def test_opacity(self):
        engine = ImageAnimationEngine()
        anim = engine.opacity(duration=2.0, start=0.0, end=1.0)
        assert anim.animation_type == ImageAnimationType.OPACITY

    def test_crop(self):
        engine = ImageAnimationEngine()
        anim = engine.crop(duration=5.0)
        assert anim.animation_type == ImageAnimationType.CROP

    def test_depth_illusion(self):
        engine = ImageAnimationEngine()
        anim = engine.depth_illusion(duration=5.0, depth=0.05)
        assert anim.animation_type == ImageAnimationType.DEPTH_ILLUSION

    def test_parallax(self):
        engine = ImageAnimationEngine()
        anim = engine.parallax(duration=5.0)
        assert anim.animation_type == ImageAnimationType.PARALLAX

    def test_preset_zoom_in(self):
        engine = ImageAnimationEngine()
        anim = engine.preset("zoom_in", duration=5.0)
        assert anim.animation_type == ImageAnimationType.SCALE

    def test_preset_fade_in(self):
        engine = ImageAnimationEngine()
        anim = engine.preset("fade_in", duration=3.0)
        assert anim.animation_type == ImageAnimationType.OPACITY

    def test_preset_invalid(self):
        engine = ImageAnimationEngine()
        with pytest.raises(ValueError):
            engine.preset("nonexistent")

    def test_list_presets(self):
        engine = ImageAnimationEngine()
        presets = engine.list_presets()
        assert "zoom_in" in presets
        assert "fade_in" in presets

    def test_to_ffmpeg_filter_scale(self):
        engine = ImageAnimationEngine()
        anim = engine.scale(duration=5.0)
        filt = engine.to_ffmpeg_filter(anim, width=1920, height=1080)
        assert "scale" in filt


# ===========================================================================
# Transition Engine Tests
# ===========================================================================
class TestTransitionEngine:
    def test_fade(self):
        engine = TransitionEngine()
        trans = engine.fade(duration=1.0, from_scene="s1", to_scene="s2")
        assert trans.transition_type == TransitionType.FADE
        assert trans.duration == 1.0
        assert trans.from_scene_id == "s1"

    def test_crossfade(self):
        engine = TransitionEngine()
        trans = engine.crossfade(duration=0.5)
        assert trans.transition_type == TransitionType.CROSSFADE

    def test_slide(self):
        engine = TransitionEngine()
        trans = engine.slide(duration=0.5, direction="left")
        assert trans.transition_type == TransitionType.SLIDE
        assert trans.params["direction"] == "left"

    def test_push(self):
        engine = TransitionEngine()
        trans = engine.push(direction="right")
        assert trans.transition_type == TransitionType.PUSH

    def test_zoom(self):
        engine = TransitionEngine()
        trans = engine.zoom()
        assert trans.transition_type == TransitionType.ZOOM

    def test_blur(self):
        engine = TransitionEngine()
        trans = engine.blur()
        assert trans.transition_type == TransitionType.BLUR

    def test_dissolve(self):
        engine = TransitionEngine()
        trans = engine.dissolve()
        assert trans.transition_type == TransitionType.DISSOLVE

    def test_custom(self):
        engine = TransitionEngine()
        trans = engine.custom("my_effect", duration=0.8, params={"intensity": 0.5})
        assert trans.transition_type == TransitionType.CUSTOM
        assert trans.params["name"] == "my_effect"

    def test_to_ffmpeg_xfade(self):
        engine = TransitionEngine()
        trans = engine.fade(duration=1.0)
        filt = engine.to_ffmpeg_xfade(trans, offset=5.0)
        assert "xfade" in filt
        assert "duration=1.0" in filt
        assert "offset=5.0" in filt

    def test_to_ffmpeg_xfade_slide(self):
        engine = TransitionEngine()
        trans = engine.slide(direction="right")
        filt = engine.to_ffmpeg_xfade(trans)
        assert "slideright" in filt

    def test_list_transition_types(self):
        engine = TransitionEngine()
        types = engine.list_transition_types()
        assert "fade" in types
        assert "custom" in types


# ===========================================================================
# Video Effects Engine Tests
# ===========================================================================
class TestVideoEffectsEngine:
    def test_brightness(self):
        engine = VideoEffectsEngine()
        effect = engine.brightness(intensity=0.1)
        assert effect.effect_type == VideoEffectType.BRIGHTNESS

    def test_contrast(self):
        engine = VideoEffectsEngine()
        effect = engine.contrast(intensity=1.2)
        assert effect.effect_type == VideoEffectType.CONTRAST

    def test_color_correction(self):
        engine = VideoEffectsEngine()
        effect = engine.color_correction(saturation=1.1, gamma=0.9)
        assert effect.effect_type == VideoEffectType.COLOR_CORRECTION

    def test_blur(self):
        engine = VideoEffectsEngine()
        effect = engine.blur(radius=3.0)
        assert effect.effect_type == VideoEffectType.BLUR

    def test_sharpen(self):
        engine = VideoEffectsEngine()
        effect = engine.sharpen(intensity=1.5)
        assert effect.effect_type == VideoEffectType.SHARPEN

    def test_glow(self):
        engine = VideoEffectsEngine()
        effect = engine.glow(intensity=0.5)
        assert effect.effect_type == VideoEffectType.GLOW

    def test_noise_reduction(self):
        engine = VideoEffectsEngine()
        effect = engine.noise_reduction(intensity=0.5)
        assert effect.effect_type == VideoEffectType.NOISE_REDUCTION

    def test_vignette(self):
        engine = VideoEffectsEngine()
        effect = engine.vignette(intensity=0.5)
        assert effect.effect_type == VideoEffectType.VIGNETTE

    def test_lut(self):
        engine = VideoEffectsEngine()
        effect = engine.lut("path/to/lut.cube")
        assert effect.effect_type == VideoEffectType.LUT
        assert effect.params["lut_file"] == "path/to/lut.cube"

    def test_to_ffmpeg_filter_brightness(self):
        engine = VideoEffectsEngine()
        effect = engine.brightness(intensity=0.1)
        filt = engine.to_ffmpeg_filter(effect)
        assert "eq=brightness" in filt

    def test_to_ffmpeg_filter_blur(self):
        engine = VideoEffectsEngine()
        effect = engine.blur(radius=3.0)
        filt = engine.to_ffmpeg_filter(effect)
        assert "boxblur" in filt

    def test_to_ffmpeg_filter_vignette(self):
        engine = VideoEffectsEngine()
        effect = engine.vignette()
        filt = engine.to_ffmpeg_filter(effect)
        assert "vignette" in filt

    def test_list_effect_types(self):
        engine = VideoEffectsEngine()
        types = engine.list_effect_types()
        assert "brightness" in types
        assert "blur" in types


# ===========================================================================
# Text Engine Tests
# ===========================================================================
class TestTextEngine:
    def test_title(self):
        engine = TextEngine()
        overlay = engine.title("Hello World", duration=3.0)
        assert overlay.text_type == TextType.TITLE
        assert overlay.content == "Hello World"
        assert overlay.font_size == 72

    def test_lower_third(self):
        engine = TextEngine()
        overlay = engine.lower_third("John Doe")
        assert overlay.text_type == TextType.LOWER_THIRD
        assert overlay.background_color is not None

    def test_caption(self):
        engine = TextEngine()
        overlay = engine.caption("Caption text", start_time=1.0, duration=2.0)
        assert overlay.text_type == TextType.CAPTION
        assert overlay.start_time == 1.0

    def test_credits(self):
        engine = TextEngine()
        overlay = engine.credits("Credits here")
        assert overlay.text_type == TextType.CREDITS

    def test_watermark(self):
        engine = TextEngine()
        overlay = engine.watermark("© 2024")
        assert overlay.text_type == TextType.WATERMARK
        assert overlay.opacity == 0.5

    def test_callout(self):
        engine = TextEngine()
        overlay = engine.callout("Important!")
        assert overlay.text_type == TextType.CALLOUT

    def test_animated_text(self):
        engine = TextEngine()
        overlay = engine.animated_text("Animated", animation="fade_in")
        assert overlay.text_type == TextType.ANIMATED_TEXT
        assert overlay.animation == "fade_in"

    def test_to_ffmpeg_drawtext(self):
        engine = TextEngine()
        overlay = engine.title("Test")
        filt = engine.to_ffmpeg_drawtext(overlay, width=1920, height=1080)
        assert "drawtext" in filt
        assert "Test" in filt

    def test_list_text_types(self):
        engine = TextEngine()
        types = engine.list_text_types()
        assert "title" in types
        assert "watermark" in types


# ===========================================================================
# Subtitle Engine Tests
# ===========================================================================
class TestSubtitleEngine:
    def test_create_config(self):
        engine = SubtitleEngine()
        config = engine.create_config("file:///subs.srt", format=SubtitleFormat.SRT)
        assert config.format == SubtitleFormat.SRT
        assert config.file_uri == "file:///subs.srt"

    def test_create_config_with_options(self):
        engine = SubtitleEngine()
        config = engine.create_config(
            "file:///subs.vtt",
            format=SubtitleFormat.VTT,
            word_highlight=True,
            language="es",
        )
        assert config.word_highlight is True
        assert config.language == "es"

    def test_to_ffmpeg_subtitle_filter(self):
        engine = SubtitleEngine()
        config = engine.create_config("/tmp/subs.srt")
        filt = engine.to_ffmpeg_subtitle_filter(config)
        assert "subtitles" in filt
        assert "FontName" in filt

    def test_to_ffmpeg_subtitle_filter_empty(self):
        engine = SubtitleEngine()
        config = engine.create_config("")
        filt = engine.to_ffmpeg_subtitle_filter(config)
        assert filt == ""

    def test_generate_srt(self):
        engine = SubtitleEngine()
        entries = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
            {"text": "World", "start": 2.0, "duration": 2.0},
        ]
        srt = engine.generate_srt(entries)
        assert "1" in srt
        assert "Hello" in srt
        assert "00:00:00,000" in srt
        assert "00:00:02,000" in srt

    def test_generate_vtt(self):
        engine = SubtitleEngine()
        entries = [
            {"text": "Hello", "start": 0.0, "duration": 2.0},
        ]
        vtt = engine.generate_vtt(entries)
        assert "WEBVTT" in vtt
        assert "Hello" in vtt
        assert "00:00:00.000" in vtt

    def test_list_formats(self):
        engine = SubtitleEngine()
        formats = engine.list_formats()
        assert "srt" in formats
        assert "vtt" in formats


# ===========================================================================
# Audio Mixer Tests
# ===========================================================================
class TestAudioMixer:
    def test_create_voice_track(self):
        mixer = AudioMixer()
        track = mixer.create_voice_track("file:///voice.mp3", duration=10.0)
        assert track.track_type == TrackType.VOICE
        assert track.normalized is True

    def test_create_music_track(self):
        mixer = AudioMixer()
        track = mixer.create_music_track("file:///music.mp3", duration=30.0)
        assert track.track_type == TrackType.MUSIC
        assert track.ducking is True
        assert track.volume == 0.3

    def test_create_sfx_track(self):
        mixer = AudioMixer()
        track = mixer.create_sfx_track("file:///sfx.wav", duration=1.0)
        assert track.track_type == TrackType.SOUND_EFFECT

    def test_create_mix_config(self):
        mixer = AudioMixer()
        voice = mixer.create_voice_track("file:///voice.mp3")
        music = mixer.create_music_track("file:///music.mp3")
        config = mixer.create_mix_config([voice], [music])
        assert len(config.voice_tracks) == 1
        assert len(config.music_tracks) == 1

    def test_to_ffmpeg_audio_filter_volume(self):
        mixer = AudioMixer()
        track = mixer.create_voice_track("file:///voice.mp3", volume=0.8)
        filt = mixer.to_ffmpeg_audio_filter(track)
        assert "volume=0.8" in filt

    def test_to_ffmpeg_audio_filter_normalization(self):
        mixer = AudioMixer()
        track = mixer.create_voice_track("file:///voice.mp3", normalized=True)
        filt = mixer.to_ffmpeg_audio_filter(track)
        assert "loudnorm" in filt

    def test_to_ffmpeg_audio_filter_fade(self):
        mixer = AudioMixer()
        track = mixer.create_music_track("file:///music.mp3", duration=10.0, fade_in=2.0, fade_out=3.0)
        filt = mixer.to_ffmpeg_audio_filter(track)
        assert "afade" in filt

    def test_to_ffmpeg_mix_filter(self):
        mixer = AudioMixer()
        v1 = mixer.create_voice_track("file:///v1.mp3")
        m1 = mixer.create_music_track("file:///m1.mp3")
        config = mixer.create_mix_config([v1], [m1])
        filt = mixer.to_ffmpeg_mix_filter(config)
        assert "amix" in filt
        assert "inputs=2" in filt

    def test_to_ffmpeg_mix_filter_empty(self):
        mixer = AudioMixer()
        config = AudioMixConfig()
        filt = mixer.to_ffmpeg_mix_filter(config)
        assert filt == "anull"


# ===========================================================================
# Media Synchronizer Tests
# ===========================================================================
class TestMediaSynchronizer:
    def test_synchronize_no_issues(self):
        sync = MediaSynchronizer()
        doc = CompositionDocument()
        result = sync.synchronize(doc)
        assert len(result["issues"]) == 0

    def test_synchronize_voice_visual_mismatch(self):
        sync = MediaSynchronizer()
        voice_track = Track(track_type=TrackType.VOICE, clips=[
            TimelineClip(start_time=0, duration=10.0)
        ])
        video_track = Track(track_type=TrackType.VIDEO, clips=[
            TimelineClip(start_time=0, duration=5.0)
        ])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[voice_track, video_track], total_duration=10.0)
        )
        result = sync.synchronize(doc)
        assert len(result["issues"]) > 0

    def test_align_to_voice(self):
        sync = MediaSynchronizer()
        voice_track = Track(track_type=TrackType.VOICE, clips=[
            TimelineClip(start_time=0, duration=15.0)
        ])
        timeline = Timeline(tracks=[voice_track], total_duration=20.0)
        aligned = sync.align_to_voice(timeline)
        assert aligned.total_duration == 15.0

    def test_check_audio_sync(self):
        sync = MediaSynchronizer()
        doc = CompositionDocument()
        assert sync.check_audio_sync(doc) is True


# ===========================================================================
# Composition Builder Tests
# ===========================================================================
class TestCompositionBuilder:
    def _make_manifest(self, scene_count: int = 3) -> AssetManifest:
        manifests = []
        for i in range(scene_count):
            sm = SceneAssetManifest(
                scene_id=f"scene_{i}",
                scene_number=i + 1,
                image=GeneratedAsset(storage_uri=f"local:///img_{i}.png"),
                voice=GeneratedAsset(storage_uri=f"local:///voice_{i}.mp3"),
                generation_status=JobStatus.COMPLETED,
                estimated_render_time_seconds=5.0,
            )
            manifests.append(sm)
        return AssetManifest(
            project_id="proj1",
            scene_manifests=manifests,
            total_duration_seconds=15.0,
            total_cost=0.5,
            total_assets=6,
        )

    def test_build_basic(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        assert doc.project_id == "proj1"
        assert doc.scene_count == 3
        assert doc.track_count > 0
        assert doc.total_duration > 0

    def test_build_has_video_track(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        video_tracks = doc.timeline.get_tracks_by_type(TrackType.VIDEO)
        assert len(video_tracks) == 1

    def test_build_has_voice_track(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        voice_tracks = doc.timeline.get_tracks_by_type(TrackType.VOICE)
        assert len(voice_tracks) == 1

    def test_build_has_image_track(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        image_tracks = doc.timeline.get_tracks_by_type(TrackType.IMAGE)
        assert len(image_tracks) == 1

    def test_build_has_transitions(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest(3)
        doc = builder.build(manifest)
        # 3 scenes -> 2 transitions between them
        assert len(doc.transitions) >= 2

    def test_build_has_camera_motions(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        assert len(doc.camera_motions) == 3

    def test_build_has_image_animations(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        # Images are placed when no video, so animations should exist
        assert len(doc.image_animations) > 0

    def test_build_with_export_profile(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        ep = ExportProfile(width=3840, height=2160, fps=60)
        doc = builder.build(manifest, export_profile=ep)
        assert doc.export_profile.width == 3840
        assert doc.export_profile.fps == 60

    def test_build_with_scene_durations(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest, scene_durations={"scene_0": 10.0, "scene_1": 8.0, "scene_2": 5.0})
        assert doc.scenes[0].duration == 10.0
        assert doc.scenes[1].duration == 8.0

    def test_build_has_rendering_metadata(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        doc = builder.build(manifest)
        assert doc.rendering_metadata.estimated_duration > 0
        assert doc.rendering_metadata.estimated_render_time > 0

    def test_build_incomplete_manifest(self):
        builder = CompositionBuilder()
        manifest = self._make_manifest()
        manifest.scene_manifests[0].generation_status = JobStatus.QUEUED
        # Should still build, just with a warning
        doc = builder.build(manifest)
        assert doc.scene_count == 3


# ===========================================================================
# Composition Validator Tests
# ===========================================================================
class TestCompositionValidator:
    def test_valid_composition(self):
        validator = CompositionValidator()
        doc = CompositionDocument(
            timeline=Timeline(
                tracks=[Track(id="t1", clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=5.0)])],
                total_duration=5.0,
            ),
            scenes=[CompositionScene(start_time=0, duration=5.0)],
            export_profile=ExportProfile(),
        )
        result = run_async(validator.validate(doc))
        assert result.valid is True
        assert len(result.errors) == 0

    def test_empty_timeline(self):
        validator = CompositionValidator()
        doc = CompositionDocument()
        result = run_async(validator.validate(doc))
        assert result.valid is False
        assert any("no tracks" in e for e in result.errors)

    def test_missing_asset_uri(self):
        validator = CompositionValidator()
        track = Track(id="t1", clips=[TimelineClip(asset_uri="", start_time=0, duration=5.0)])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=5.0),
            scenes=[CompositionScene(start_time=0, duration=5.0)],
        )
        result = run_async(validator.validate(doc))
        assert result.valid is False
        assert any("no asset URI" in e for e in result.errors)

    def test_track_overlaps(self):
        validator = CompositionValidator()
        track = Track(id="t1", clips=[
            TimelineClip(id=uuid4(), asset_uri="file:///a.mp4", start_time=0, duration=5.0),
            TimelineClip(id=uuid4(), asset_uri="file:///b.mp4", start_time=3, duration=5.0),
        ])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=10.0),
            scenes=[CompositionScene(start_time=0, duration=10.0)],
        )
        result = run_async(validator.validate(doc))
        assert result.valid is False
        assert any("Overlap" in e for e in result.errors)

    def test_scene_ordering(self):
        validator = CompositionValidator()
        doc = CompositionDocument(
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=10.0)])],
                total_duration=10.0,
            ),
            scenes=[
                CompositionScene(scene_id="s1", start_time=0, duration=8.0),
                CompositionScene(scene_id="s2", start_time=5, duration=5.0),
            ],
        )
        result = run_async(validator.validate(doc))
        assert result.valid is False
        assert any("Scene" in e for e in result.errors)

    def test_invalid_export_settings(self):
        validator = CompositionValidator()
        ep = ExportProfile(width=0, height=0, fps=0)
        doc = CompositionDocument(
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=5.0)])],
                total_duration=5.0,
            ),
            scenes=[CompositionScene(start_time=0, duration=5.0)],
            export_profile=ep,
        )
        result = run_async(validator.validate(doc))
        assert result.valid is False
        assert any("dimensions" in e or "FPS" in e for e in result.errors)

    def test_audio_sync_warning(self):
        validator = CompositionValidator()
        voice_track = Track(track_type=TrackType.VOICE, clips=[
            TimelineClip(asset_uri="file:///voice.mp3", start_time=0, duration=10.0)
        ])
        video_track = Track(track_type=TrackType.VIDEO, clips=[
            TimelineClip(asset_uri="file:///video.mp4", start_time=0, duration=5.0)
        ])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[voice_track, video_track], total_duration=10.0),
            scenes=[CompositionScene(start_time=0, duration=10.0)],
        )
        result = run_async(validator.validate(doc))
        assert any("duration mismatch" in w for w in result.warnings)


# ===========================================================================
# Render Planner Tests
# ===========================================================================
class TestRenderPlanner:
    def _make_doc(self, scenes: int = 3, duration: float = 15.0) -> CompositionDocument:
        scene_list = [CompositionScene(start_time=i * 5.0, duration=5.0) for i in range(scenes)]
        track = Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=duration)])
        return CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=duration),
            scenes=scene_list,
        )

    def test_plan_basic(self):
        planner = RenderPlanner()
        doc = self._make_doc()
        result = run_async(planner.plan(doc))
        assert result.estimated_execution_time > 0
        assert result.rendering_complexity > 0
        assert result.expected_output_size_mb > 0

    def test_plan_4k_complexity(self):
        planner = RenderPlanner()
        doc = self._make_doc()
        doc.export_profile.width = 3840
        doc.export_profile.height = 2160
        result = run_async(planner.plan(doc))
        # 4K should have higher memory estimate
        assert result.estimated_memory_mb > 512

    def test_plan_bottlenecks(self):
        planner = RenderPlanner()
        doc = self._make_doc(scenes=30, duration=700.0)
        result = run_async(planner.plan(doc))
        assert len(result.potential_bottlenecks) > 0

    def test_plan_optimization_suggestions(self):
        planner = RenderPlanner()
        doc = self._make_doc()
        doc.export_profile.preset = "slow"
        result = run_async(planner.plan(doc))
        assert len(result.optimization_suggestions) > 0

    def test_plan_scene_order(self):
        planner = RenderPlanner()
        doc = self._make_doc(scenes=5)
        result = run_async(planner.plan(doc))
        assert len(result.scene_render_order) == 5

    def test_plan_parallelizable(self):
        planner = RenderPlanner()
        doc = self._make_doc(scenes=10, duration=50.0)
        result = run_async(planner.plan(doc))
        assert result.parallelizable is True


# ===========================================================================
# Composition Optimizer Tests
# ===========================================================================
class TestCompositionOptimizer:
    def test_optimize_layer_ordering(self):
        opt = CompositionOptimizer()
        t_high = Track(id="h", name="High", layer=5)
        t_low = Track(id="l", name="Low", layer=0)
        doc = CompositionDocument(
            timeline=Timeline(tracks=[t_high, t_low]),
        )
        opt.optimize(doc)
        assert doc.timeline.tracks[0].layer == 0
        assert doc.timeline.tracks[1].layer == 5

    def test_optimize_animations_removes_no_op(self):
        opt = CompositionOptimizer()
        clip_id = "c1"
        doc = CompositionDocument(
            timeline=Timeline(tracks=[Track()]),
            image_animations={clip_id: ImageAnimation(start_value=1.0, end_value=1.0, duration=5.0)},
        )
        opt.optimize(doc)
        assert clip_id not in doc.image_animations

    def test_optimize_audio_trims_music(self):
        opt = CompositionOptimizer()
        voice_track = Track(track_type=TrackType.VOICE, clips=[
            TimelineClip(start_time=0, duration=10.0)
        ])
        music_track = Track(track_type=TrackType.MUSIC, clips=[
            TimelineClip(start_time=0, duration=15.0)
        ])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[voice_track, music_track], total_duration=10.0),
        )
        opt.optimize(doc)
        assert music_track.clips[0].duration == 10.0

    def test_optimize_asset_loading_sorts_clips(self):
        opt = CompositionOptimizer()
        track = Track(clips=[
            TimelineClip(start_time=5.0, duration=3.0),
            TimelineClip(start_time=0.0, duration=5.0),
        ])
        doc = CompositionDocument(timeline=Timeline(tracks=[track]))
        opt.optimize(doc)
        assert track.clips[0].start_time == 0.0
        assert track.clips[1].start_time == 5.0

    def test_optimize_memory_reuse(self):
        opt = CompositionOptimizer()
        # Two clips sharing the same asset
        track = Track(clips=[
            TimelineClip(asset_uri="same.mp4", start_time=0, duration=5.0),
            TimelineClip(asset_uri="same.mp4", start_time=5.0, duration=5.0),
        ])
        doc = CompositionDocument(timeline=Timeline(tracks=[track]))
        original_mem = doc.rendering_metadata.estimated_memory_mb
        opt.optimize(doc)
        # Memory should be reduced due to asset reuse
        assert doc.rendering_metadata.estimated_memory_mb <= original_mem


# ===========================================================================
# Timeline Compiler Tests
# ===========================================================================
class TestTimelineCompiler:
    def test_compile_basic(self):
        compiler = TimelineCompiler()
        track = Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=5.0)])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=5.0, fps=30),
            scenes=[CompositionScene(start_time=0, duration=5.0)],
        )
        result = compiler.compile(doc)
        assert result["total_duration"] == 5.0
        assert result["total_frames"] == 150

    def test_compile_resolves_overlaps(self):
        compiler = TimelineCompiler()
        track = Track(clips=[
            TimelineClip(id=uuid4(), asset_uri="file:///a.mp4", start_time=0, duration=5.0),
            TimelineClip(id=uuid4(), asset_uri="file:///b.mp4", start_time=3, duration=5.0),
        ])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=10.0, fps=30),
        )
        compiler.compile(doc)
        # First clip should be trimmed
        assert track.clips[0].duration == 3.0

    def test_compile_generates_timestamps(self):
        compiler = TimelineCompiler()
        clip = TimelineClip(asset_uri="file:///v.mp4", start_time=2.0, duration=5.0)
        track = Track(clips=[clip])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=7.0, fps=30),
        )
        compiler.compile(doc)
        assert clip.metadata.get("start_frame") == 60
        assert clip.metadata.get("end_frame") == 210

    def test_compile_generates_instructions(self):
        compiler = TimelineCompiler()
        clip = TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=5.0)
        track = Track(name="Video", track_type=TrackType.VIDEO, clips=[clip])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=5.0, fps=30),
            scenes=[CompositionScene(scene_id="s1", start_time=0, duration=5.0)],
        )
        result = compiler.compile(doc)
        assert len(result["instructions"]) == 1
        inst = result["instructions"][0]
        assert inst["track_type"] == "video"
        assert inst["asset_uri"] == "file:///v.mp4"

    def test_compile_scene_data(self):
        compiler = TimelineCompiler()
        doc = CompositionDocument(
            timeline=Timeline(tracks=[Track()], total_duration=15.0, fps=30),
            scenes=[
                CompositionScene(scene_id="s1", scene_number=1, start_time=0, duration=5.0),
                CompositionScene(scene_id="s2", scene_number=2, start_time=5.0, duration=10.0),
            ],
        )
        result = compiler.compile(doc)
        scenes = result["scenes"]
        assert len(scenes) == 2
        assert scenes[0]["start_frame"] == 0
        assert scenes[1]["start_frame"] == 150


# ===========================================================================
# FFmpeg Renderer Tests
# ===========================================================================
class TestFFmpegCompositionRenderer:
    def test_renderer_name(self):
        renderer = FFmpegCompositionRenderer()
        assert renderer.renderer_name == "ffmpeg"

    def test_load(self):
        renderer = FFmpegCompositionRenderer()
        doc = CompositionDocument()
        run_async(renderer.load(doc))
        # No exception means success

    def test_validate_no_composition(self):
        renderer = FFmpegCompositionRenderer()
        errors = run_async(renderer.validate())
        assert "No composition loaded" in errors[0]

    def test_validate_valid(self):
        renderer = FFmpegCompositionRenderer()
        doc = CompositionDocument(
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=5.0)])],
                total_duration=5.0,
            ),
            export_profile=ExportProfile(),
        )
        run_async(renderer.load(doc))
        errors = run_async(renderer.validate())
        # Should not have codec errors
        assert all("codec" not in e.lower() for e in errors)

    def test_validate_unsupported_codec(self):
        renderer = FFmpegCompositionRenderer()
        doc = CompositionDocument(
            export_profile=ExportProfile(codec="unsupported_codec"),
        )
        run_async(renderer.load(doc))
        errors = run_async(renderer.validate())
        assert any("Unsupported codec" in e for e in errors)

    def test_uri_to_path(self):
        renderer = FFmpegCompositionRenderer()
        assert renderer._uri_to_path("local:///tmp/video.mp4") == "/tmp/video.mp4"
        assert renderer._uri_to_path("file:///tmp/video.mp4") == "file:///tmp/video.mp4"

    def test_build_ffmpeg_command_has_inputs(self):
        renderer = FFmpegCompositionRenderer()
        track = Track(clips=[TimelineClip(asset_uri="local:///tmp/video.mp4", start_time=0, duration=5.0)])
        doc = CompositionDocument(
            timeline=Timeline(tracks=[track], total_duration=5.0),
            export_profile=ExportProfile(),
        )
        run_async(renderer.load(doc))
        args = renderer._build_ffmpeg_command()
        assert "-i" in args
        assert "/tmp/video.mp4" in args

    def test_build_ffmpeg_command_has_encoding(self):
        renderer = FFmpegCompositionRenderer()
        doc = CompositionDocument(
            timeline=Timeline(tracks=[Track()], total_duration=5.0),
            export_profile=ExportProfile(),
        )
        run_async(renderer.load(doc))
        args = renderer._build_ffmpeg_command()
        assert "-c:v" in args
        assert "libx264" in args

    def test_collect_metrics_default(self):
        renderer = FFmpegCompositionRenderer()
        metrics = run_async(renderer.collect_metrics())
        assert metrics.render_time_seconds == 0.0


# ===========================================================================
# Rendering Pipeline Tests
# ===========================================================================
class TestRenderingPipeline:
    def test_pipeline_progress(self):
        pipeline = RenderingPipeline()
        assert pipeline.progress.status == RenderStatus.QUEUED


# ===========================================================================
# Export Engine Tests
# ===========================================================================
class TestExportEngine:
    def test_get_preset_1080p(self):
        engine = ExportEngine()
        preset = engine.get_preset("1080p")
        assert preset is not None
        assert preset.width == 1920
        assert preset.height == 1080

    def test_get_preset_4k(self):
        engine = ExportEngine()
        preset = engine.get_preset("4k")
        assert preset is not None
        assert preset.width == 3840

    def test_get_preset_square(self):
        engine = ExportEngine()
        preset = engine.get_preset("square")
        assert preset is not None
        assert preset.width == 1080
        assert preset.height == 1080

    def test_get_preset_portrait(self):
        engine = ExportEngine()
        preset = engine.get_preset("portrait")
        assert preset is not None
        assert preset.height == 1920

    def test_get_preset_nonexistent(self):
        engine = ExportEngine()
        assert engine.get_preset("nonexistent") is None

    def test_list_presets(self):
        engine = ExportEngine()
        presets = engine.list_presets()
        assert "1080p" in presets
        assert "4k" in presets

    def test_create_profile(self):
        engine = ExportEngine()
        profile = engine.create_profile(
            format=ExportFormat.MOV,
            resolution=ExportResolution.P720,
            fps=24,
        )
        assert profile.format == ExportFormat.MOV
        assert profile.width == 1280
        assert profile.fps == 24

    def test_get_preview_profile(self):
        engine = ExportEngine()
        full = ExportProfile(width=1920, height=1080, fps=30)
        preview = engine.get_preview_profile(full)
        assert preview.width == 640
        assert preview.preset == "fast"
        assert preview.crf > full.crf

    def test_generate_thumbnail_path(self):
        engine = ExportEngine()
        path = engine.generate_thumbnail_path("/tmp", "proj1")
        assert "proj1_thumbnail.png" in path

    def test_generate_metadata(self):
        engine = ExportEngine()
        doc = CompositionDocument(project_id="p1")
        meta = engine.generate_metadata(doc, "/tmp/video.mp4")
        assert meta["project_id"] == "p1"
        assert meta["output_path"] == "/tmp/video.mp4"

    def test_list_formats(self):
        engine = ExportEngine()
        formats = engine.list_formats()
        assert "mp4" in formats
        assert "mov" in formats

    def test_list_resolutions(self):
        engine = ExportEngine()
        resolutions = engine.list_resolutions()
        assert "1920x1080" in resolutions


# ===========================================================================
# Quality Validator Tests
# ===========================================================================
class TestQualityValidator:
    def test_validate_success(self, tmp_path):
        validator = QualityValidator()
        output = tmp_path / "video.mp4"
        output.write_bytes(b"x" * 2048)
        doc = CompositionDocument(
            export_profile=ExportProfile(width=1920, height=1080),
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=15.0)])],
                total_duration=15.0,
            ),
        )
        metrics = RenderMetrics(
            output_resolution="1920x1080",
            output_duration_seconds=15.0,
            dropped_frames=0,
        )
        report = validator.validate(str(output), doc, metrics)
        assert report.overall_pass is True
        assert report.encoding_success is True

    def test_validate_missing_file(self):
        validator = QualityValidator()
        doc = CompositionDocument()
        metrics = RenderMetrics()
        report = validator.validate("/nonexistent/video.mp4", doc, metrics)
        assert report.overall_pass is False
        assert report.encoding_success is False

    def test_validate_empty_file(self, tmp_path):
        validator = QualityValidator()
        output = tmp_path / "empty.mp4"
        output.write_bytes(b"")
        doc = CompositionDocument()
        metrics = RenderMetrics()
        report = validator.validate(str(output), doc, metrics)
        assert report.overall_pass is False

    def test_validate_dropped_frames(self, tmp_path):
        validator = QualityValidator()
        output = tmp_path / "video.mp4"
        output.write_bytes(b"x" * 2048)
        doc = CompositionDocument(
            export_profile=ExportProfile(),
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=15.0)])],
                total_duration=15.0,
            ),
        )
        metrics = RenderMetrics(
            output_resolution="1920x1080",
            output_duration_seconds=15.0,
            dropped_frames=5,
        )
        report = validator.validate(str(output), doc, metrics)
        assert report.no_dropped_frames is False
        assert any("dropped frames" in i for i in report.issues)

    def test_validate_resolution_mismatch(self, tmp_path):
        validator = QualityValidator()
        output = tmp_path / "video.mp4"
        output.write_bytes(b"x" * 2048)
        doc = CompositionDocument(
            export_profile=ExportProfile(width=1920, height=1080),
            timeline=Timeline(
                tracks=[Track(clips=[TimelineClip(asset_uri="file:///v.mp4", start_time=0, duration=15.0)])],
                total_duration=15.0,
            ),
        )
        metrics = RenderMetrics(
            output_resolution="1280x720",
            output_duration_seconds=15.0,
        )
        report = validator.validate(str(output), doc, metrics)
        assert report.resolution_valid is False


# ===========================================================================
# Render Cache Tests
# ===========================================================================
class TestRenderCache:
    def test_compute_hash(self):
        cache = RenderCache()
        doc = CompositionDocument(project_id="p1")
        h = cache.compute_hash(doc)
        assert len(h) == 64  # SHA-256 hex

    def test_put_and_get(self):
        cache = RenderCache()
        doc = CompositionDocument(project_id="p1")
        cache.put(doc, "/tmp/video.mp4", 1024)
        result = cache.get(doc)
        assert result is not None
        assert result.output_path == "/tmp/video.mp4"

    def test_cache_miss(self):
        cache = RenderCache()
        doc = CompositionDocument(project_id="p1")
        result = cache.get(doc)
        assert result is None
        assert cache._misses == 1

    def test_hit_rate(self):
        cache = RenderCache()
        doc = CompositionDocument(project_id="p1")
        cache.put(doc, "/tmp/video.mp4")
        cache.get(doc)  # hit
        cache.get(CompositionDocument(project_id="p2"))  # miss
        assert cache.hit_rate == 0.5

    def test_invalidate(self):
        cache = RenderCache()
        doc = CompositionDocument(project_id="p1")
        cache.put(doc, "/tmp/video.mp4")
        assert cache.invalidate(doc) is True
        assert cache.size == 0

    def test_clear(self):
        cache = RenderCache()
        cache.put(CompositionDocument(project_id="p1"), "/tmp/v1.mp4")
        cache.put(CompositionDocument(project_id="p2"), "/tmp/v2.mp4")
        cache.clear()
        assert cache.size == 0

    def test_eviction(self):
        cache = RenderCache(max_entries=2)
        cache.put(CompositionDocument(project_id="p1"), "/tmp/v1.mp4")
        cache.put(CompositionDocument(project_id="p2"), "/tmp/v2.mp4")
        cache.put(CompositionDocument(project_id="p3"), "/tmp/v3.mp4")
        assert cache.size == 2


# ===========================================================================
# Preview Engine Tests
# ===========================================================================
class TestPreviewEngine:
    def test_create_preview_profile(self):
        engine = PreviewEngine()
        doc = CompositionDocument(export_profile=ExportProfile(width=1920, height=1080, fps=30))
        profile = engine.create_preview_profile(doc)
        assert profile.width == 640
        assert profile.preset == "ultrafast"
        assert profile.crf >= 28

    def test_create_preview_result(self):
        engine = PreviewEngine()
        result = engine.create_preview_result("/tmp/preview.mp4", duration=15.0, file_size=500_000)
        assert result.preview_path == "/tmp/preview.mp4"
        assert result.duration_seconds == 15.0

    def test_estimate_preview_time(self):
        engine = PreviewEngine()
        doc = CompositionDocument(
            timeline=Timeline(total_duration=30.0),
        )
        t = engine.estimate_preview_time(doc)
        assert t > 0

    def test_estimate_preview_size(self):
        engine = PreviewEngine()
        doc = CompositionDocument(
            timeline=Timeline(total_duration=30.0),
        )
        size = engine.estimate_preview_size(doc)
        assert size > 0


# ===========================================================================
# Render Queue Tests
# ===========================================================================
class TestRenderQueue:
    def test_submit_and_dequeue(self):
        q = RenderQueue()
        job = RenderJob(priority=RenderPriority.NORMAL)
        run_async(q.submit(job))
        assert q.queue_size == 1
        dequeued = run_async(q.dequeue())
        assert dequeued is not None
        assert dequeued.id == job.id

    def test_priority_ordering(self):
        q = RenderQueue()
        low = RenderJob(id=uuid4(), priority=RenderPriority.LOW)
        high = RenderJob(id=uuid4(), priority=RenderPriority.HIGH)
        run_async(q.submit(low))
        run_async(q.submit(high))
        first = run_async(q.dequeue())
        assert first.priority == RenderPriority.HIGH

    def test_complete(self):
        q = RenderQueue()
        job = RenderJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        assert run_async(q.complete(job.id)) is True
        assert q.completed_count == 1

    def test_fail_with_retry(self):
        q = RenderQueue()
        job = RenderJob(max_retries=2)
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.fail(job.id, "error"))
        assert q.queue_size == 1  # back in queue for retry

    def test_fail_dead_letter(self):
        q = RenderQueue()
        job = RenderJob(max_retries=0)
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.fail(job.id, "error"))
        assert q.dead_letter_count == 1

    def test_cancel_active(self):
        q = RenderQueue()
        job = RenderJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        assert run_async(q.cancel(job.id)) is True
        assert job.status == RenderStatus.CANCELLED

    def test_cancel_queued(self):
        q = RenderQueue()
        job = RenderJob()
        run_async(q.submit(job))
        assert run_async(q.cancel(job.id)) is True
        assert q.queue_size == 0

    def test_pause_resume(self):
        q = RenderQueue()
        q.pause()
        assert q.is_paused is True
        assert run_async(q.dequeue()) is None
        q.resume()
        assert q.is_paused is False

    def test_get_job(self):
        q = RenderQueue()
        job = RenderJob()
        run_async(q.submit(job))
        found = q.get_job(job.id)
        assert found is not None
        assert found.id == job.id

    def test_clear_completed(self):
        q = RenderQueue()
        job = RenderJob()
        run_async(q.submit(job))
        run_async(q.dequeue())
        run_async(q.complete(job.id))
        assert q.clear_completed() == 1
        assert q.completed_count == 0


# ===========================================================================
# Progress Tracker Tests
# ===========================================================================
class TestProgressTracker:
    def test_register(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        progress = tracker.register(job_id)
        assert progress.job_id == job_id
        assert progress.status == RenderStatus.QUEUED

    def test_update(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        tracker.register(job_id)
        progress = tracker.update(job_id, status=RenderStatus.RENDERING, percentage=50.0, stage="rendering")
        assert progress.status == RenderStatus.RENDERING
        assert progress.progress_percentage == 50.0
        assert "rendering" in progress.stages_completed

    def test_get(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        tracker.register(job_id)
        progress = tracker.get(job_id)
        assert progress is not None

    def test_subscribe(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        tracker.register(job_id)
        updates: list[RenderProgress] = []
        tracker.subscribe(job_id, lambda p: updates.append(p))
        tracker.update(job_id, percentage=25.0)
        assert len(updates) == 1
        assert updates[0].progress_percentage == 25.0

    def test_unsubscribe(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        tracker.register(job_id)
        updates: list[RenderProgress] = []
        cb = lambda p: updates.append(p)
        tracker.subscribe(job_id, cb)
        tracker.unsubscribe(job_id, cb)
        tracker.update(job_id, percentage=50.0)
        assert len(updates) == 0

    def test_remove(self):
        tracker = ProgressTracker()
        job_id = uuid4()
        tracker.register(job_id)
        tracker.remove(job_id)
        assert tracker.get(job_id) is None

    def test_active_jobs(self):
        tracker = ProgressTracker()
        tracker.register(uuid4())
        tracker.register(uuid4())
        assert tracker.active_jobs == 2

    def test_get_all_progress(self):
        tracker = ProgressTracker()
        j1 = uuid4()
        j2 = uuid4()
        tracker.register(j1)
        tracker.register(j2)
        all_progress = tracker.get_all_progress()
        assert len(all_progress) == 2


# ===========================================================================
# Events Tests
# ===========================================================================
class TestCompositionEvents:
    def test_event_constants(self):
        assert CompositionEvents.COMPOSITION_CREATED == "CompositionCreated"
        assert CompositionEvents.COMPOSITION_VALIDATED == "CompositionValidated"
        assert CompositionEvents.RENDER_PLANNED == "RenderPlanned"
        assert CompositionEvents.RENDERING_STARTED == "RenderingStarted"
        assert CompositionEvents.ENCODING_STARTED == "EncodingStarted"
        assert CompositionEvents.ENCODING_COMPLETED == "EncodingCompleted"
        assert CompositionEvents.RENDERING_COMPLETED == "RenderingCompleted"
        assert CompositionEvents.RENDERING_FAILED == "RenderingFailed"
        assert CompositionEvents.PROJECT_PACKAGE_GENERATED == "ProjectPackageGenerated"

    def test_emit_composition_created(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_composition_created(uuid4(), 3, 5)
        )

    def test_emit_composition_validated(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_composition_validated(uuid4(), True, 0)
        )

    def test_emit_render_planned(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_render_planned(uuid4(), 120.0, 3.5)
        )

    def test_emit_rendering_started(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_rendering_started(uuid4(), uuid4())
        )

    def test_emit_rendering_completed(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_rendering_completed(uuid4(), "/tmp/video.mp4", 120.0)
        )

    def test_emit_rendering_failed(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_rendering_failed(uuid4(), "FFmpeg error")
        )

    def test_emit_project_package_generated(self):
        emitter = CompositionEventEmitter()
        run_async(
            emitter.emit_project_package_generated(uuid4(), "proj1")
        )


# ===========================================================================
# Integration Test
# ===========================================================================
class TestIntegration:
    def test_full_pipeline_build_validate_optimize_compile(self):
        """Test the full pipeline from manifest to compiled timeline."""
        # 1. Create asset manifest
        manifests = []
        for i in range(3):
            sm = SceneAssetManifest(
                scene_id=f"scene_{i}",
                scene_number=i + 1,
                image=GeneratedAsset(storage_uri=f"local:///img_{i}.png"),
                voice=GeneratedAsset(storage_uri=f"local:///voice_{i}.mp3"),
                generation_status=JobStatus.COMPLETED,
                estimated_render_time_seconds=5.0,
            )
            manifests.append(sm)
        manifest = AssetManifest(
            project_id="proj1",
            scene_manifests=manifests,
            total_duration_seconds=15.0,
            total_cost=0.5,
            total_assets=6,
        )

        # 2. Build composition
        builder = CompositionBuilder()
        doc = builder.build(manifest)
        assert doc.scene_count == 3

        # 3. Validate
        validator = CompositionValidator()
        result = run_async(validator.validate(doc))
        assert result.valid is True

        # 4. Plan
        planner = RenderPlanner()
        plan = run_async(planner.plan(doc))
        assert plan.estimated_execution_time > 0

        # 5. Optimize
        optimizer = CompositionOptimizer()
        optimizer.optimize(doc)

        # 6. Compile timeline
        compiler = TimelineCompiler()
        compiled = compiler.compile(doc)
        assert compiled["total_duration"] > 0
        assert compiled["total_frames"] > 0
        assert len(compiled["instructions"]) > 0

    def test_build_validate_plan_optimize_compile_with_effects(self):
        """Test pipeline with effects, transitions, and text overlays."""
        manifests = []
        for i in range(5):
            sm = SceneAssetManifest(
                scene_id=f"scene_{i}",
                scene_number=i + 1,
                video=GeneratedAsset(storage_uri=f"local:///video_{i}.mp4"),
                voice=GeneratedAsset(storage_uri=f"local:///voice_{i}.mp3"),
                music=GeneratedAsset(storage_uri=f"local:///music_{i}.mp3"),
                subtitles=GeneratedAsset(storage_uri=f"local:///subs_{i}.srt"),
                generation_status=JobStatus.COMPLETED,
                estimated_render_time_seconds=5.0,
            )
            manifests.append(sm)
        manifest = AssetManifest(
            project_id="proj2",
            scene_manifests=manifests,
            total_duration_seconds=25.0,
            total_cost=1.0,
            total_assets=20,
        )

        # Build
        builder = CompositionBuilder()
        doc = builder.build(manifest)

        # Add text overlays
        text_engine = TextEngine()
        doc.text_overlays.append(text_engine.title("Video Title"))
        doc.text_overlays.append(text_engine.watermark("© 2024"))

        # Add effects
        effects_engine = VideoEffectsEngine()
        doc.effects.append(effects_engine.brightness(0.1))
        doc.effects.append(effects_engine.vignette(0.3))

        # Validate
        validator = CompositionValidator()
        result = run_async(validator.validate(doc))
        assert result.valid is True

        # Plan
        planner = RenderPlanner()
        plan = run_async(planner.plan(doc))
        assert plan.rendering_complexity > 0

        # Optimize
        optimizer = CompositionOptimizer()
        optimizer.optimize(doc)

        # Compile
        compiler = TimelineCompiler()
        compiled = compiler.compile(doc)
        assert len(compiled["instructions"]) > 0
