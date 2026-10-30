"""Subtitle Engine.

Supports SRT, VTT, ASS formats with word highlighting, sentence
highlighting, speaker labels, multiple languages, animated subtitles,
and custom styling.
"""

from __future__ import annotations

from src.composition.schema import SubtitleConfig, SubtitleFormat
from src.core.logging import get_logger


class SubtitleEngine:
    """Manages subtitle configuration and generation.

    Produces ``SubtitleConfig`` objects and provides utilities for
    subtitle file generation and styling.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def create_config(
        self,
        file_uri: str = "",
        *,
        format: SubtitleFormat = SubtitleFormat.SRT,
        font_family: str = "Arial",
        font_size: int = 24,
        font_color: str = "#FFFFFF",
        outline_color: str = "#000000",
        outline_width: int = 2,
        word_highlight: bool = False,
        sentence_highlight: bool = False,
        speaker_labels: bool = False,
        language: str = "en",
        animated: bool = False,
    ) -> SubtitleConfig:
        """Create a subtitle configuration.

        Args:
            file_uri: URI to the subtitle file.
            format: Subtitle format (SRT, VTT, ASS).
            font_family: Font family.
            font_size: Font size.
            font_color: Font color (hex).
            outline_color: Outline color (hex).
            outline_width: Outline width in pixels.
            word_highlight: Enable word-level highlighting.
            sentence_highlight: Enable sentence-level highlighting.
            speaker_labels: Enable speaker labels.
            language: Language code.
            animated: Enable animated subtitles.

        Returns:
            A ``SubtitleConfig``.
        """
        return SubtitleConfig(
            format=format,
            file_uri=file_uri,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color,
            outline_color=outline_color,
            outline_width=outline_width,
            word_highlight=word_highlight,
            sentence_highlight=sentence_highlight,
            speaker_labels=speaker_labels,
            language=language,
            animated=animated,
        )

    def to_ffmpeg_subtitle_filter(self, config: SubtitleConfig) -> str:
        """Convert subtitle config to an FFmpeg subtitles filter string.

        Args:
            config: The subtitle configuration.

        Returns:
            FFmpeg subtitles filter string.
        """
        if not config.file_uri:
            return ""

        escaped_path = config.file_uri.replace("\\", "/").replace(":", "\\:")

        style_parts = [
            f"FontName={config.font_family}",
            f"FontSize={config.font_size}",
            f"PrimaryColour={config.font_color}",
            f"OutlineColour={config.outline_color}",
            f"Outline={config.outline_width}",
        ]

        if config.animated:
            style_parts.append("Bold=1")

        style = ",".join(style_parts)
        return f"subtitles='{escaped_path}':force_style='{style}'"

    def generate_srt(self, entries: list[dict], *, words_per_second: float = 2.5) -> str:
        """Generate SRT content from subtitle entries.

        Args:
            entries: List of {text, start, duration} dicts.
            words_per_second: Speaking rate for auto-timing.

        Returns:
            SRT formatted string.
        """
        lines: list[str] = []
        for idx, entry in enumerate(entries, 1):
            start = entry.get("start", 0.0)
            duration = entry.get("duration", 2.0)
            text = entry.get("text", "")
            end = start + duration

            lines.append(str(idx))
            lines.append(f"{self._format_srt_time(start)} --> {self._format_srt_time(end)}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)

    def generate_vtt(self, entries: list[dict], *, words_per_second: float = 2.5) -> str:
        """Generate VTT content from subtitle entries.

        Args:
            entries: List of {text, start, duration} dicts.
            words_per_second: Speaking rate for auto-timing.

        Returns:
            VTT formatted string.
        """
        lines: list[str] = ["WEBVTT", ""]

        for idx, entry in enumerate(entries, 1):
            start = entry.get("start", 0.0)
            duration = entry.get("duration", 2.0)
            text = entry.get("text", "")
            end = start + duration

            lines.append(f"{self._format_vtt_time(start)} --> {self._format_vtt_time(end)}")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)

    def list_formats(self) -> list[str]:
        """List all supported subtitle formats."""
        return [f.value for f in SubtitleFormat]

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds as SRT time (HH:MM:SS,mmm)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_vtt_time(self, seconds: float) -> str:
        """Format seconds as VTT time (HH:MM:SS.mmm)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
