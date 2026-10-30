"""Composition Builder.

Transforms an ``AssetManifest`` into a ``CompositionDocument``.

Responsibilities:
- Build timeline
- Assign tracks
- Assign layers
- Scene sequencing
- Asset placement
- Subtitle mapping
- Audio mapping
- Music mapping
- Transition mapping
- Animation mapping
- Camera motion mapping
- Export settings
- Rendering metadata

The CompositionBuilder NEVER invokes FFmpeg.
"""

from __future__ import annotations

from typing import Any

from src.composition.audio import AudioMixer
from src.composition.camera import CameraMotionEngine
from src.composition.events import CompositionEventEmitter
from src.composition.animation import ImageAnimationEngine
from src.composition.schema import (
    AudioMixConfig,
    CameraMotion,
    CompositionDocument,
    CompositionScene,
    EasingType,
    ExportProfile,
    ImageAnimation,
    RenderingMetadata,
    SubtitleConfig,
    Timeline,
    TimelineClip,
    Track,
    TrackType,
    Transition,
)
from src.composition.transitions import TransitionEngine
from src.composition.tracks import TrackSystem
from src.core.logging import get_logger
from src.generation.schema import AssetManifest, JobStatus


class CompositionBuilder:
    """Transforms an ``AssetManifest`` into a ``CompositionDocument``.

    The builder creates a complete composition with:
    - Timeline with tracks for each media type
    - Scenes sequenced by time
    - Camera motions for each scene
    - Image animations for static images
    - Transitions between scenes
    - Audio mixing configuration
    - Subtitle configuration
    - Export profile
    """

    def __init__(
        self,
        event_emitter: CompositionEventEmitter | None = None,
        *,
        camera_engine: CameraMotionEngine | None = None,
        animation_engine: ImageAnimationEngine | None = None,
        transition_engine: TransitionEngine | None = None,
        audio_mixer: AudioMixer | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or CompositionEventEmitter()
        self._camera = camera_engine or CameraMotionEngine()
        self._animation = animation_engine or ImageAnimationEngine()
        self._transitions = transition_engine or TransitionEngine()
        self._audio = audio_mixer or AudioMixer()

    def build(
        self,
        manifest: AssetManifest,
        *,
        export_profile: ExportProfile | None = None,
        scene_durations: dict[str, float] | None = None,
        camera_plans: dict[str, dict[str, Any]] | None = None,
        animation_plans: dict[str, dict[str, Any]] | None = None,
        transition_config: dict[str, Any] | None = None,
        subtitle_config: SubtitleConfig | None = None,
    ) -> CompositionDocument:
        """Build a composition document from an asset manifest.

        Args:
            manifest: The asset manifest from the Generation Platform.
            export_profile: Export profile override.
            scene_durations: Per-scene duration overrides.
            camera_plans: Per-scene camera plan overrides.
            animation_plans: Per-scene animation plan overrides.
            transition_config: Transition configuration.
            subtitle_config: Subtitle configuration override.

        Returns:
            A complete ``CompositionDocument``.
        """
        if not manifest.is_complete:
            self._logger.warning(
                "building_incomplete_manifest",
                project_id=manifest.project_id,
                scenes=manifest.scene_count,
            )

        # Create track system
        track_system = TrackSystem()

        # Build scenes and timeline
        scenes: list[CompositionScene] = []
        current_time = 0.0
        camera_motions: dict[str, CameraMotion] = {}
        image_animations: dict[str, ImageAnimation] = {}
        transitions: list[Transition] = []

        # Create tracks
        video_track = track_system.create_track("Video", TrackType.VIDEO, layer=0)
        image_track = track_system.create_track("Images", TrackType.IMAGE, layer=1)
        voice_track = track_system.create_track("Voice", TrackType.VOICE, layer=0)
        music_track = track_system.create_track("Music", TrackType.MUSIC, layer=0)
        subtitle_track = track_system.create_track("Subtitles", TrackType.SUBTITLE, layer=2)
        overlay_track = track_system.create_track("Overlays", TrackType.OVERLAY, layer=3)

        # Audio tracks
        voice_audio_tracks = []
        music_audio_tracks = []

        for sm in manifest.scene_manifests:
            scene_id = sm.scene_id
            duration = scene_durations.get(scene_id, sm.estimated_render_time_seconds * 2) if scene_durations else sm.estimated_render_time_seconds * 2
            if duration <= 0:
                duration = 5.0  # default 5 seconds

            # Create scene
            scene = CompositionScene(
                scene_id=scene_id,
                scene_number=sm.scene_number,
                start_time=current_time,
                duration=duration,
                asset_uris={},
            )

            # Place video asset
            if sm.video and sm.video.storage_uri:
                clip = TimelineClip(
                    track_id=video_track.id,
                    asset_uri=sm.video.storage_uri,
                    asset_type="video",
                    start_time=current_time,
                    duration=duration,
                )
                video_track.clips.append(clip)
                scene.asset_uris["video"] = sm.video.storage_uri

            # Place image asset (if no video)
            if sm.image and sm.image.storage_uri and not sm.video:
                clip = TimelineClip(
                    track_id=image_track.id,
                    asset_uri=sm.image.storage_uri,
                    asset_type="image",
                    start_time=current_time,
                    duration=duration,
                )
                image_track.clips.append(clip)
                scene.asset_uris["image"] = sm.image.storage_uri

                # Add image animation — use camera plan movement if
                # available, otherwise alternate between zoom-in and
                # pan-right for visual variety.
                cam_plan = camera_plans.get(scene_id, {}) if camera_plans else {}
                movement = (cam_plan.get("movement") or "").lower() if cam_plan else ""

                if movement in ("zoom_in", "dolly_in", "push"):
                    anim = self._animation.scale(duration, start=1.0, end=1.2)
                elif movement in ("zoom_out", "dolly_out", "pull"):
                    anim = self._animation.scale(duration, start=1.2, end=1.0)
                elif movement in ("pan_left", "pan_right", "tracking"):
                    anim = self._animation.translate(
                        duration, start=0.0, end=0.15,
                        direction="right" if "right" in movement else "left",
                    )
                elif movement in ("tilt_up", "tilt_down"):
                    anim = self._animation.translate(
                        duration, start=0.0, end=0.15,
                        direction="down" if "down" in movement else "up",
                    )
                elif movement in ("orbit", "arc"):
                    anim = self._animation.scale(duration, start=1.0, end=1.15)
                else:
                    # Default: alternate zoom-in / pan-right for variety
                    if sm.scene_number % 2 == 0:
                        anim = self._animation.scale(duration, start=1.0, end=1.2)
                    else:
                        anim = self._animation.translate(
                            duration, start=0.0, end=0.15, direction="right",
                        )
                image_animations[str(clip.id)] = anim

            # Place voice asset
            if sm.voice and sm.voice.storage_uri:
                clip = TimelineClip(
                    track_id=voice_track.id,
                    asset_uri=sm.voice.storage_uri,
                    asset_type="audio",
                    start_time=current_time,
                    duration=duration,
                )
                voice_track.clips.append(clip)
                scene.asset_uris["voice"] = sm.voice.storage_uri

                voice_audio = self._audio.create_voice_track(
                    sm.voice.storage_uri,
                    start_time=current_time,
                    duration=duration,
                )
                voice_audio_tracks.append(voice_audio)

            # Place music asset
            if sm.music and sm.music.storage_uri:
                clip = TimelineClip(
                    track_id=music_track.id,
                    asset_uri=sm.music.storage_uri,
                    asset_type="audio",
                    start_time=current_time,
                    duration=duration,
                    volume=0.3,
                )
                music_track.clips.append(clip)
                scene.asset_uris["music"] = sm.music.storage_uri

                music_audio = self._audio.create_music_track(
                    sm.music.storage_uri,
                    start_time=current_time,
                    duration=duration,
                )
                music_audio_tracks.append(music_audio)

            # Place subtitle asset
            if sm.subtitles and sm.subtitles.storage_uri:
                clip = TimelineClip(
                    track_id=subtitle_track.id,
                    asset_uri=sm.subtitles.storage_uri,
                    asset_type="subtitle",
                    start_time=current_time,
                    duration=duration,
                )
                subtitle_track.clips.append(clip)
                scene.asset_uris["subtitle"] = sm.subtitles.storage_uri

            # Camera motion
            cam_plan = camera_plans.get(scene_id, {}) if camera_plans else {}
            if cam_plan:
                motion = self._camera.ken_burns(duration)
            else:
                motion = self._camera.ken_burns(duration)
            camera_motions[scene_id] = motion

            # Transition to next scene
            if transitions and transition_config is not False:
                trans = self._transitions.fade(duration=1.0, from_scene=scene_id)
                transitions.append(trans)

            scenes.append(scene)
            current_time += duration

        # Add transition between scenes
        if transition_config is not False:
            for i in range(len(scenes) - 1):
                trans = self._transitions.fade(
                    duration=0.5,
                    from_scene=scenes[i].scene_id,
                    to_scene=scenes[i + 1].scene_id,
                )
                transitions.append(trans)

        # Build timeline
        timeline = Timeline(
            tracks=track_system.get_all_tracks(),
            total_duration=current_time,
            fps=export_profile.fps if export_profile else 30,
            width=export_profile.width if export_profile else 1920,
            height=export_profile.height if export_profile else 1080,
        )

        # Build audio config
        audio_config = self._audio.create_mix_config(
            voice_tracks=voice_audio_tracks,
            music_tracks=music_audio_tracks,
        )

        # Rendering metadata
        render_meta = RenderingMetadata(
            estimated_duration=current_time,
            estimated_render_time=current_time * 2,  # rough estimate
            estimated_memory_mb=512,
            estimated_output_size_mb=int(current_time * 2.5),  # ~2.5MB/s for 1080p
            rendering_complexity=len(scenes) * 0.1,
        )

        # Build composition document
        doc = CompositionDocument(
            project_id=manifest.project_id,
            timeline=timeline,
            scenes=scenes,
            camera_motions=camera_motions,
            image_animations=image_animations,
            transitions=transitions,
            audio_config=audio_config,
            subtitle_config=subtitle_config,
            export_profile=export_profile or ExportProfile(),
            rendering_metadata=render_meta,
            metadata={
                "manifest_id": str(manifest.id),
                "total_cost": manifest.total_cost,
                "total_assets": manifest.total_assets,
            },
        )

        self._logger.info(
            "composition_built",
            composition_id=str(doc.id),
            project_id=manifest.project_id,
            scenes=len(scenes),
            tracks=len(timeline.tracks),
            duration=current_time,
        )

        return doc
