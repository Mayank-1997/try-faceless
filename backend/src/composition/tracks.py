"""Track System — unlimited track management for the timeline.

Supports video, image, voice, music, sound effect, subtitle, overlay,
animation, and future custom tracks.
"""

from __future__ import annotations

from src.composition.schema import Track, TrackType
from src.core.logging import get_logger


class TrackSystem:
    """Manages tracks in the timeline.

    Supports unlimited tracks of any type.  Tracks are layered by
    their ``layer`` property (lower = behind, higher = in front).
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._tracks: dict[str, Track] = {}

    def add_track(self, track: Track) -> Track:
        """Add a track to the system.

        Args:
            track: The track to add.

        Returns:
            The added track.
        """
        self._tracks[track.id] = track
        self._logger.info("track_added", track_id=track.id, track_type=track.track_type.value, name=track.name)
        return track

    def create_track(self, name: str, track_type: TrackType, layer: int = 0) -> Track:
        """Create and add a new track.

        Args:
            name: Track name.
            track_type: Type of track (video, audio, subtitle, etc.).
            layer: Layer index (lower = behind).

        Returns:
            The created track.
        """
        track = Track(name=name, track_type=track_type, layer=layer)
        return self.add_track(track)

    def remove_track(self, track_id: str) -> bool:
        """Remove a track.

        Args:
            track_id: The track ID to remove.

        Returns:
            ``True`` if the track was removed.
        """
        if track_id in self._tracks:
            del self._tracks[track_id]
            self._logger.info("track_removed", track_id=track_id)
            return True
        return False

    def get_track(self, track_id: str) -> Track | None:
        """Get a track by ID."""
        return self._tracks.get(track_id)

    def get_tracks_by_type(self, track_type: TrackType) -> list[Track]:
        """Get all tracks of a given type, ordered by layer."""
        tracks = [t for t in self._tracks.values() if t.track_type == track_type]
        tracks.sort(key=lambda t: t.layer)
        return tracks

    def get_all_tracks(self) -> list[Track]:
        """Get all tracks ordered by layer."""
        tracks = list(self._tracks.values())
        tracks.sort(key=lambda t: t.layer)
        return tracks

    @property
    def track_count(self) -> int:
        """Number of tracks."""
        return len(self._tracks)

    def get_video_tracks(self) -> list[Track]:
        """Get all video tracks."""
        return self.get_tracks_by_type(TrackType.VIDEO)

    def get_audio_tracks(self) -> list[Track]:
        """Get all audio tracks (voice + music + SFX)."""
        return (
            self.get_tracks_by_type(TrackType.VOICE)
            + self.get_tracks_by_type(TrackType.MUSIC)
            + self.get_tracks_by_type(TrackType.SOUND_EFFECT)
        )

    def get_subtitle_tracks(self) -> list[Track]:
        """Get all subtitle tracks."""
        return self.get_tracks_by_type(TrackType.SUBTITLE)

    def get_overlay_tracks(self) -> list[Track]:
        """Get all overlay tracks."""
        return self.get_tracks_by_type(TrackType.OVERLAY)

    def clear(self) -> None:
        """Remove all tracks."""
        self._tracks.clear()
