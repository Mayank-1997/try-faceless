"""Audio Mixer.

Supports voice normalization, music ducking, fade in/out, crossfade,
volume balancing, and future audio effects.
"""

from __future__ import annotations

from src.composition.schema import AudioMixConfig, AudioTrack, TrackType
from src.core.logging import get_logger


class AudioMixer:
    """Manages audio mixing for the composition.

    Produces ``AudioMixConfig`` and ``AudioTrack`` configurations
    that the renderer translates into FFmpeg audio filter expressions.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def create_voice_track(
        self,
        file_uri: str,
        *,
        start_time: float = 0.0,
        duration: float = 0.0,
        volume: float = 1.0,
        normalized: bool = True,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> AudioTrack:
        """Create a voice audio track.

        Args:
            file_uri: Audio file URI.
            start_time: Start time in seconds.
            duration: Duration in seconds.
            volume: Volume (0.0 to 2.0).
            normalized: Apply voice normalization.
            fade_in: Fade in duration in seconds.
            fade_out: Fade out duration in seconds.

        Returns:
            A voice ``AudioTrack``.
        """
        return AudioTrack(
            track_type=TrackType.VOICE,
            file_uri=file_uri,
            start_time=start_time,
            duration=duration,
            volume=volume,
            normalized=normalized,
            fade_in_duration=fade_in,
            fade_out_duration=fade_out,
        )

    def create_music_track(
        self,
        file_uri: str,
        *,
        start_time: float = 0.0,
        duration: float = 0.0,
        volume: float = 0.3,
        ducking: bool = True,
        fade_in: float = 1.0,
        fade_out: float = 2.0,
    ) -> AudioTrack:
        """Create a music audio track.

        Args:
            file_uri: Audio file URI.
            start_time: Start time in seconds.
            duration: Duration in seconds.
            volume: Volume (0.0 to 2.0).
            ducking: Enable music ducking under voice.
            fade_in: Fade in duration in seconds.
            fade_out: Fade out duration in seconds.

        Returns:
            A music ``AudioTrack``.
        """
        return AudioTrack(
            track_type=TrackType.MUSIC,
            file_uri=file_uri,
            start_time=start_time,
            duration=duration,
            volume=volume,
            ducking=ducking,
            fade_in_duration=fade_in,
            fade_out_duration=fade_out,
        )

    def create_sfx_track(
        self,
        file_uri: str,
        *,
        start_time: float = 0.0,
        duration: float = 1.0,
        volume: float = 0.8,
    ) -> AudioTrack:
        """Create a sound effect audio track.

        Args:
            file_uri: Audio file URI.
            start_time: Start time in seconds.
            duration: Duration in seconds.
            volume: Volume (0.0 to 2.0).

        Returns:
            An SFX ``AudioTrack``.
        """
        return AudioTrack(
            track_type=TrackType.SOUND_EFFECT,
            file_uri=file_uri,
            start_time=start_time,
            duration=duration,
            volume=volume,
        )

    def create_mix_config(
        self,
        voice_tracks: list[AudioTrack] | None = None,
        music_tracks: list[AudioTrack] | None = None,
        sfx_tracks: list[AudioTrack] | None = None,
        *,
        master_volume: float = 1.0,
        voice_normalization: bool = True,
        music_ducking: bool = True,
    ) -> AudioMixConfig:
        """Create an audio mix configuration.

        Args:
            voice_tracks: Voice audio tracks.
            music_tracks: Music audio tracks.
            sfx_tracks: Sound effect tracks.
            master_volume: Master output volume.
            voice_normalization: Enable voice normalization.
            music_ducking: Enable music ducking.

        Returns:
            An ``AudioMixConfig``.
        """
        return AudioMixConfig(
            voice_tracks=voice_tracks or [],
            music_tracks=music_tracks or [],
            sfx_tracks=sfx_tracks or [],
            master_volume=master_volume,
            voice_normalization=voice_normalization,
            music_ducking=music_ducking,
        )

    def to_ffmpeg_audio_filter(self, track: AudioTrack) -> str:
        """Convert an audio track to FFmpeg audio filter expressions.

        Args:
            track: The audio track.

        Returns:
            FFmpeg audio filter string.
        """
        filters: list[str] = []

        # Volume adjustment
        if track.volume != 1.0:
            filters.append(f"volume={track.volume}")

        # Voice normalization
        if track.normalized and track.track_type == TrackType.VOICE:
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        # Fade in
        if track.fade_in_duration > 0:
            filters.append(f"afade=t=in:st={track.start_time}:d={track.fade_in_duration}")

        # Fade out
        if track.fade_out_duration > 0:
            fade_out_start = track.start_time + track.duration - track.fade_out_duration
            filters.append(f"afade=t=out:st={fade_out_start}:d={track.fade_out_duration}")

        # Music ducking (sidechain compress)
        if track.ducking and track.track_type == TrackType.MUSIC:
            filters.append("sidechaincompress=threshold=0.1:ratio=8:attack=5:release=300")

        return ",".join(filters) if filters else "anull"

    def to_ffmpeg_mix_filter(self, config: AudioMixConfig) -> str:
        """Convert the full audio mix config to an FFmpeg amix filter.

        Args:
            config: The audio mix configuration.

        Returns:
            FFmpeg amix filter string.
        """
        all_tracks = config.voice_tracks + config.music_tracks + config.sfx_tracks
        if not all_tracks:
            return "anull"

        # amix with normalized weights
        inputs = len(all_tracks)
        return f"amix=inputs={inputs}:duration=longest:normalize=1"
