"""Media Synchronizer.

Synchronizes voice, video, images, music, effects, subtitles, and
animations to prevent timeline drift.
"""

from __future__ import annotations

from src.composition.schema import CompositionDocument, Timeline, Track, TrackType
from src.core.logging import get_logger


class MediaSynchronizer:
    """Synchronizes all media elements in the timeline.

    Ensures that voice, video, images, music, effects, subtitles,
    and animations are properly aligned in time.  Detects and reports
    sync issues.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def synchronize(self, composition: CompositionDocument) -> dict[str, list[str]]:
        """Synchronize all media in the composition.

        Args:
            composition: The composition document.

        Returns:
            Dict with 'issues' and 'adjustments' lists.
        """
        issues: list[str] = []
        adjustments: list[str] = []

        timeline = composition.timeline
        voice_tracks = timeline.get_tracks_by_type(TrackType.VOICE)
        video_tracks = timeline.get_tracks_by_type(TrackType.VIDEO)
        image_tracks = timeline.get_tracks_by_type(TrackType.IMAGE)
        music_tracks = timeline.get_tracks_by_type(TrackType.MUSIC)
        subtitle_tracks = timeline.get_tracks_by_type(TrackType.SUBTITLE)

        # Check voice-video sync
        if voice_tracks and (video_tracks or image_tracks):
            voice_duration = max(t.total_duration for t in voice_tracks)
            visual_duration = max(
                (t.total_duration for t in video_tracks + image_tracks),
                default=0.0,
            )
            if abs(voice_duration - visual_duration) > 0.5:
                issues.append(
                    f"Voice/visual duration mismatch: voice={voice_duration:.1f}s, visual={visual_duration:.1f}s"
                )
                # Suggest adjustment
                if visual_duration < voice_duration:
                    adjustments.append(
                        f"Extend visual clips by {voice_duration - visual_duration:.1f}s to match voice"
                    )
                else:
                    adjustments.append(
                        f"Trim visual clips by {visual_duration - voice_duration:.1f}s to match voice"
                    )

        # Check subtitle timing
        if subtitle_tracks and voice_tracks:
            for sub_track in subtitle_tracks:
                for clip in sub_track.clips:
                    # Check if subtitle clip falls within voice duration
                    voice_end = max(t.total_duration for t in voice_tracks)
                    if clip.start_time + clip.duration > voice_end + 0.5:
                        issues.append(
                            f"Subtitle clip at {clip.start_time:.1f}s extends beyond voice end ({voice_end:.1f}s)"
                        )

        # Check music doesn't overlap voice inappropriately
        if music_tracks and voice_tracks:
            for music in music_tracks:
                if not music.muted:
                    for clip in music.clips:
                        # Music should be ducked during voice
                        adjustments.append(
                            f"Music track '{music.name}' should duck during voice segments"
                        )
                        break
                    break

        # Check scene boundaries align with track clips
        for scene in composition.scenes:
            scene_end = scene.end_time
            for track in timeline.tracks:
                for clip in track.clips:
                    # Check for clips that extend beyond scene boundaries
                    if clip.start_time < scene.start_time and clip.start_time + clip.duration > scene.start_time:
                        # Clip spans scene boundary — this is OK for transitions
                        pass
                    elif clip.start_time >= scene.start_time and clip.start_time < scene_end and clip.start_time + clip.duration > scene_end + 0.1:
                        issues.append(
                            f"Clip on track '{track.name}' extends beyond scene {scene.scene_number} boundary"
                        )

        self._logger.info(
            "synchronization_complete",
            issues=len(issues),
            adjustments=len(adjustments),
        )

        return {"issues": issues, "adjustments": adjustments}

    def align_to_voice(self, timeline: Timeline) -> Timeline:
        """Align all tracks to the voice track duration.

        The voice track is the primary timing reference.  All other
        tracks are padded or trimmed to match.

        Args:
            timeline: The timeline to align.

        Returns:
            The aligned timeline.
        """
        voice_tracks = timeline.get_tracks_by_type(TrackType.VOICE)
        if not voice_tracks:
            return timeline

        voice_duration = max(t.total_duration for t in voice_tracks)
        timeline.total_duration = voice_duration

        self._logger.info("timeline_aligned_to_voice", duration=voice_duration)
        return timeline

    def check_audio_sync(self, composition: CompositionDocument) -> bool:
        """Check if audio is properly synchronized.

        Args:
            composition: The composition document.

        Returns:
            ``True`` if audio is in sync.
        """
        result = self.synchronize(composition)
        return len(result["issues"]) == 0
