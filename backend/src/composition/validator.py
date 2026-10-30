"""Composition Validator.

Validates a ``CompositionDocument`` before rendering.

Checks:
- Timeline integrity
- Missing assets
- Broken references
- Track overlaps
- Subtitle timing
- Audio synchronization
- Transition conflicts
- Animation conflicts
- Scene ordering
- Export settings
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.composition.events import CompositionEventEmitter
from src.composition.schema import (
    CompositionDocument,
    TrackType,
    ValidationMetadata,
)
from src.core.logging import get_logger


class CompositionValidator:
    """Validates a composition document before rendering.

    Only valid compositions should proceed to rendering.
    """

    def __init__(self, event_emitter: CompositionEventEmitter | None = None) -> None:
        self._logger = get_logger(__name__)
        self._events = event_emitter or CompositionEventEmitter()

    async def validate(self, composition: CompositionDocument) -> ValidationMetadata:
        """Validate a composition document.

        Args:
            composition: The composition to validate.

        Returns:
            ``ValidationMetadata`` with results.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Timeline integrity
        self._validate_timeline_integrity(composition, errors, warnings)

        # 2. Missing assets
        self._validate_assets(composition, errors, warnings)

        # 3. Broken references
        self._validate_references(composition, errors, warnings)

        # 4. Track overlaps
        self._validate_track_overlaps(composition, errors, warnings)

        # 5. Subtitle timing
        self._validate_subtitle_timing(composition, errors, warnings)

        # 6. Audio synchronization
        self._validate_audio_sync(composition, errors, warnings)

        # 7. Transition conflicts
        self._validate_transitions(composition, errors, warnings)

        # 8. Animation conflicts
        self._validate_animations(composition, errors, warnings)

        # 9. Scene ordering
        self._validate_scene_ordering(composition, errors, warnings)

        # 10. Export settings
        self._validate_export_settings(composition, errors, warnings)

        valid = len(errors) == 0
        validation_meta = ValidationMetadata(
            valid=valid,
            errors=errors,
            warnings=warnings,
            validated_at=datetime.now(timezone.utc),
        )

        composition.validation_metadata = validation_meta

        await self._events.emit_composition_validated(
            composition.id, valid, len(errors),
        )

        self._logger.info(
            "composition_validated",
            composition_id=str(composition.id),
            valid=valid,
            errors=len(errors),
            warnings=len(warnings),
        )

        return validation_meta

    def _validate_timeline_integrity(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate timeline has tracks and duration > 0."""
        if not doc.timeline.tracks:
            errors.append("Timeline has no tracks")
        if doc.timeline.total_duration <= 0:
            errors.append("Timeline total duration is 0")
        if doc.timeline.fps <= 0:
            errors.append("Timeline FPS must be positive")
        if doc.timeline.width <= 0 or doc.timeline.height <= 0:
            errors.append("Timeline dimensions must be positive")

    def _validate_assets(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate all asset URIs are non-empty."""
        for track in doc.timeline.tracks:
            for clip in track.clips:
                if not clip.asset_uri:
                    errors.append(f"Clip {clip.id} on track '{track.name}' has no asset URI")

    def _validate_references(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate all track references are valid."""
        track_ids = {t.id for t in doc.timeline.tracks}
        for track in doc.timeline.tracks:
            for clip in track.clips:
                if clip.track_id and clip.track_id not in track_ids:
                    errors.append(f"Clip {clip.id} references unknown track {clip.track_id}")

        # Validate transition references
        scene_ids = {s.scene_id for s in doc.scenes}
        for trans in doc.transitions:
            if trans.from_scene_id and trans.from_scene_id not in scene_ids:
                warnings.append(f"Transition from unknown scene {trans.from_scene_id}")
            if trans.to_scene_id and trans.to_scene_id not in scene_ids:
                warnings.append(f"Transition to unknown scene {trans.to_scene_id}")

    def _validate_track_overlaps(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate no overlapping clips on the same track."""
        for track in doc.timeline.tracks:
            clips = sorted(track.clips, key=lambda c: c.start_time)
            for i in range(len(clips) - 1):
                if clips[i].start_time + clips[i].duration > clips[i + 1].start_time:
                    errors.append(
                        f"Overlap on track '{track.name}': clip {clips[i].id} ends at "
                        f"{clips[i].start_time + clips[i].duration:.1f}s but next clip starts at "
                        f"{clips[i + 1].start_time:.1f}s"
                    )

    def _validate_subtitle_timing(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate subtitle timing aligns with scenes."""
        sub_tracks = doc.timeline.get_tracks_by_type(TrackType.SUBTITLE)
        if not sub_tracks:
            return

        for sub_track in sub_tracks:
            for clip in sub_track.clips:
                if clip.duration <= 0:
                    warnings.append(f"Subtitle clip {clip.id} has zero or negative duration")

    def _validate_audio_sync(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate audio tracks are synchronized."""
        voice_tracks = doc.timeline.get_tracks_by_type(TrackType.VOICE)
        video_tracks = doc.timeline.get_tracks_by_type(TrackType.VIDEO) + doc.timeline.get_tracks_by_type(TrackType.IMAGE)

        if voice_tracks and video_tracks:
            voice_dur = max(t.total_duration for t in voice_tracks)
            visual_dur = max(t.total_duration for t in video_tracks)
            if abs(voice_dur - visual_dur) > 1.0:
                warnings.append(
                    f"Voice ({voice_dur:.1f}s) and visual ({visual_dur:.1f}s) duration mismatch > 1s"
                )

    def _validate_transitions(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate transitions don't conflict."""
        seen_pairs: set[tuple[str, str]] = set()
        for trans in doc.transitions:
            pair = (trans.from_scene_id, trans.to_scene_id)
            if pair in seen_pairs:
                warnings.append(f"Duplicate transition between {trans.from_scene_id} and {trans.to_scene_id}")
            seen_pairs.add(pair)

            if trans.duration <= 0:
                errors.append(f"Transition has non-positive duration: {trans.duration}")

    def _validate_animations(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate animation configurations."""
        for clip_id, anim in doc.image_animations.items():
            if anim.duration <= 0:
                errors.append(f"Animation for clip {clip_id} has non-positive duration")
            if anim.animation_type.value == "scale" and anim.end_value <= 0:
                errors.append(f"Scale animation for clip {clip_id} has non-positive end value")

    def _validate_scene_ordering(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate scenes are properly ordered."""
        for i in range(len(doc.scenes) - 1):
            if doc.scenes[i].end_time > doc.scenes[i + 1].start_time + 0.01:
                errors.append(
                    f"Scene {doc.scenes[i].scene_number} ends at {doc.scenes[i].end_time:.1f}s "
                    f"but scene {doc.scenes[i + 1].scene_number} starts at {doc.scenes[i + 1].start_time:.1f}s"
                )

    def _validate_export_settings(self, doc: CompositionDocument, errors: list[str], warnings: list[str]) -> None:
        """Validate export profile settings."""
        ep = doc.export_profile
        if ep.width <= 0 or ep.height <= 0:
            errors.append("Export profile has invalid dimensions")
        if ep.fps <= 0:
            errors.append("Export profile FPS must be positive")
        if not ep.codec:
            warnings.append("Export profile has no codec specified")
        if not ep.audio_codec:
            warnings.append("Export profile has no audio codec specified")
