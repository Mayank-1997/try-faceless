"""Timeline Compiler.

Responsibilities:
- Compile timeline
- Resolve overlaps
- Generate timestamps
- Calculate scene durations
- Resolve dependencies
- Generate rendering instructions
- Produce optimized timeline
"""

from __future__ import annotations

from typing import Any

from src.composition.schema import (
    CompositionDocument,
    CompositionScene,
    Timeline,
    TimelineClip,
    Track,
    TrackType,
)
from src.core.logging import get_logger


class TimelineCompiler:
    """Compiles a timeline into rendering instructions.

    Takes a ``CompositionDocument`` and produces an optimized timeline
    with resolved overlaps, calculated timestamps, and rendering
    instructions for each clip.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def compile(self, composition: CompositionDocument) -> dict[str, Any]:
        """Compile the timeline into rendering instructions.

        Args:
            composition: The composition document.

        Returns:
            A dict with:
            - ``timeline``: The optimized timeline
            - ``scenes``: Compiled scene data
            - ``instructions``: Per-clip rendering instructions
            - ``total_duration``: Total duration
            - ``total_frames``: Total frame count
        """
        timeline = composition.timeline

        # Resolve overlaps
        self._resolve_overlaps(timeline)

        # Generate timestamps
        self._generate_timestamps(timeline, timeline.fps)

        # Calculate scene durations
        scene_data = self._compile_scenes(composition)

        # Generate rendering instructions
        instructions = self._generate_instructions(timeline, composition)

        total_duration = timeline.total_duration
        total_frames = int(total_duration * timeline.fps)

        self._logger.info(
            "timeline_compiled",
            composition_id=str(composition.id),
            total_duration=total_duration,
            total_frames=total_frames,
            instructions=len(instructions),
        )

        return {
            "timeline": timeline,
            "scenes": scene_data,
            "instructions": instructions,
            "total_duration": total_duration,
            "total_frames": total_frames,
        }

    def _resolve_overlaps(self, timeline: Timeline) -> None:
        """Resolve overlapping clips on the same track.

        Clips that overlap are trimmed so the first clip ends where
        the second begins.
        """
        for track in timeline.tracks:
            clips = sorted(track.clips, key=lambda c: c.start_time)
            for i in range(len(clips) - 1):
                end = clips[i].start_time + clips[i].duration
                if end > clips[i + 1].start_time:
                    clips[i].duration = clips[i + 1].start_time - clips[i].start_time
                    if clips[i].duration < 0:
                        clips[i].duration = 0.0

    def _generate_timestamps(self, timeline: Timeline, fps: int) -> None:
        """Generate frame-accurate timestamps for all clips."""
        for track in timeline.tracks:
            for clip in track.clips:
                clip.metadata["start_frame"] = int(clip.start_time * fps)
                clip.metadata["end_frame"] = int((clip.start_time + clip.duration) * fps)
                clip.metadata["frame_count"] = int(clip.duration * fps)

    def _compile_scenes(self, composition: CompositionDocument) -> list[dict[str, Any]]:
        """Compile scene data with resolved durations and dependencies."""
        compiled: list[dict[str, Any]] = []

        for scene in composition.scenes:
            entry: dict[str, Any] = {
                "scene_id": scene.scene_id,
                "scene_number": scene.scene_number,
                "start_time": scene.start_time,
                "duration": scene.duration,
                "end_time": scene.end_time,
                "start_frame": int(scene.start_time * composition.timeline.fps),
                "end_frame": int(scene.end_time * composition.timeline.fps),
                "assets": scene.asset_uris,
                "dependencies": scene.dependencies,
                "camera_motion": composition.camera_motions.get(scene.scene_id),
                "transitions": [
                    t for t in composition.transitions
                    if t.from_scene_id == scene.scene_id or t.to_scene_id == scene.scene_id
                ],
            }
            compiled.append(entry)

        return compiled

    def _generate_instructions(self, timeline: Timeline, composition: CompositionDocument) -> list[dict[str, Any]]:
        """Generate rendering instructions for each clip.

        Each instruction contains:
        - Clip ID
        - Track type
        - Asset URI
        - Start/end times
        - Filters to apply (camera, animation, effects)
        - Layer/z-index
        """
        instructions: list[dict[str, Any]] = []

        for track in timeline.tracks:
            for clip in track.clips:
                instruction: dict[str, Any] = {
                    "clip_id": str(clip.id),
                    "track_id": track.id,
                    "track_type": track.track_type.value,
                    "track_name": track.name,
                    "asset_uri": clip.asset_uri,
                    "start_time": clip.start_time,
                    "duration": clip.duration,
                    "end_time": clip.start_time + clip.duration,
                    "layer": track.layer,
                    "z_index": clip.z_index,
                    "volume": clip.volume,
                    "opacity": clip.opacity,
                    "scale": clip.scale,
                    "position": {"x": clip.position_x, "y": clip.position_y},
                    "speed": clip.speed,
                }

                # Add camera motion if available
                for scene in composition.scenes:
                    if scene.start_time <= clip.start_time < scene.end_time:
                        motion = composition.camera_motions.get(scene.scene_id)
                        if motion:
                            instruction["camera_motion"] = motion.motion_type.value
                        break

                # Add animation if available
                anim = composition.image_animations.get(str(clip.id))
                if anim:
                    instruction["animation"] = anim.animation_type.value
                    instruction["animation_params"] = {
                        "start": anim.start_value,
                        "end": anim.end_value,
                        "duration": anim.duration,
                        "easing": anim.easing.value,
                    }

                # Add effects targeting this clip
                clip_effects = [
                    {"type": e.effect_type.value, "intensity": e.intensity, "params": e.params}
                    for e in composition.effects
                    if e.target_clip_id == str(clip.id)
                ]
                if clip_effects:
                    instruction["effects"] = clip_effects

                instructions.append(instruction)

        # Sort by start time and layer
        instructions.sort(key=lambda i: (i["start_time"], i["layer"]))

        return instructions
