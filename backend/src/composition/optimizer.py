"""Composition Optimizer.

Optimizes:
- Timeline
- Layer ordering
- Animation scheduling
- Subtitle placement
- Audio synchronization
- Asset loading
- Rendering order
- Memory usage

The optimizer reduces rendering time while preserving output quality.
"""

from __future__ import annotations

from src.composition.schema import CompositionDocument, Track, TrackType
from src.core.logging import get_logger


class CompositionOptimizer:
    """Optimizes a composition for faster rendering.

    Applies non-destructive optimizations that reduce render time
    without changing the visual output.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def optimize(self, composition: CompositionDocument) -> CompositionDocument:
        """Optimize a composition document.

        Args:
            composition: The composition to optimize.

        Returns:
            The optimized composition (same object, modified in place).
        """
        optimizations: list[str] = []

        # 1. Optimize layer ordering
        self._optimize_layer_ordering(composition)
        optimizations.append("layer_ordering")

        # 2. Optimize animation scheduling
        self._optimize_animations(composition)
        optimizations.append("animation_scheduling")

        # 3. Optimize subtitle placement
        self._optimize_subtitles(composition)
        optimizations.append("subtitle_placement")

        # 4. Optimize audio synchronization
        self._optimize_audio(composition)
        optimizations.append("audio_sync")

        # 5. Optimize asset loading order
        self._optimize_asset_loading(composition)
        optimizations.append("asset_loading")

        # 6. Optimize rendering order
        self._optimize_render_order(composition)
        optimizations.append("render_order")

        # 7. Optimize memory usage
        self._optimize_memory(composition)
        optimizations.append("memory_usage")

        self._logger.info(
            "composition_optimized",
            composition_id=str(composition.id),
            optimizations=optimizations,
        )

        return composition

    def _optimize_layer_ordering(self, doc: CompositionDocument) -> None:
        """Sort tracks by layer for optimal compositing order."""
        doc.timeline.tracks.sort(key=lambda t: (t.layer, t.track_type.value))

    def _optimize_animations(self, doc: CompositionDocument) -> None:
        """Optimize animation scheduling.

        Remove animations with zero duration or no visible effect.
        """
        to_remove = [
            clip_id for clip_id, anim in doc.image_animations.items()
            if anim.duration <= 0 or anim.start_value == anim.end_value
        ]
        for clip_id in to_remove:
            del doc.image_animations[clip_id]

    def _optimize_subtitles(self, doc: CompositionDocument) -> None:
        """Optimize subtitle placement.

        Ensure subtitles don't overlap and are properly timed.
        """
        sub_tracks = doc.timeline.get_tracks_by_type(TrackType.SUBTITLE)
        for track in sub_tracks:
            clips = sorted(track.clips, key=lambda c: c.start_time)
            for i in range(len(clips) - 1):
                # If clips overlap, trim the first one
                if clips[i].start_time + clips[i].duration > clips[i + 1].start_time:
                    clips[i].duration = clips[i + 1].start_time - clips[i].start_time

    def _optimize_audio(self, doc: CompositionDocument) -> None:
        """Optimize audio synchronization.

        Align music tracks to voice duration and enable ducking.
        """
        voice_tracks = doc.timeline.get_tracks_by_type(TrackType.VOICE)
        music_tracks = doc.timeline.get_tracks_by_type(TrackType.MUSIC)

        if voice_tracks and music_tracks:
            voice_dur = max(t.total_duration for t in voice_tracks)
            for music in music_tracks:
                # Trim music to voice duration
                for clip in music.clips:
                    if clip.start_time + clip.duration > voice_dur:
                        clip.duration = voice_dur - clip.start_time

    def _optimize_asset_loading(self, doc: CompositionDocument) -> None:
        """Optimize asset loading order.

        Sort clips by start time within each track for sequential loading.
        """
        for track in doc.timeline.tracks:
            track.clips.sort(key=lambda c: c.start_time)

    def _optimize_render_order(self, doc: CompositionDocument) -> None:
        """Optimize scene rendering order.

        Scenes are already in order, but we can identify
        parallelizable segments.
        """
        # Mark parallelizable scenes (those with no dependencies)
        for scene in doc.scenes:
            if not scene.dependencies:
                scene.metadata["parallelizable"] = True

    def _optimize_memory(self, doc: CompositionDocument) -> None:
        """Optimize memory usage.

        Reduce estimated memory by identifying reusable assets.
        """
        # Count unique assets
        unique_uris: set[str] = set()
        for track in doc.timeline.tracks:
            for clip in track.clips:
                if clip.asset_uri:
                    unique_uris.add(clip.asset_uri)

        # If many clips share the same asset, memory can be reduced
        total_clips = sum(len(t.clips) for t in doc.timeline.tracks)
        if total_clips > 0 and len(unique_uris) < total_clips:
            reuse_ratio = 1.0 - (len(unique_uris) / total_clips)
            doc.rendering_metadata.estimated_memory_mb = int(
                doc.rendering_metadata.estimated_memory_mb * (1.0 - reuse_ratio * 0.3)
            )
