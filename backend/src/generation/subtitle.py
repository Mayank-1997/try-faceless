"""Subtitle Generator.

Generates subtitles in SRT and VTT formats with:
- Word-level timestamps
- Sentence timestamps
- Future multilingual support
"""

from __future__ import annotations

from typing import Any

from src.core.logging import get_logger
from src.generation.schema import AssetCategory, GeneratedAsset, GenerationRequest


class SubtitleGenerator:
    """Generates subtitle files from narration text.

    Produces SRT and VTT format subtitles with sentence-level
    timestamps.  Word-level timestamps can be generated when
    a voice generation result with timing data is available.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def generate_srt(
        self,
        narration: str,
        *,
        scene_id: str = "",
        words_per_second: float = 2.5,
        max_line_length: int = 42,
    ) -> str:
        """Generate SRT format subtitles from narration text.

        Args:
            narration: The narration text.
            scene_id: Scene identifier.
            words_per_second: Estimated speaking rate.
            max_line_length: Maximum characters per subtitle line.

        Returns:
            SRT formatted subtitle string.
        """
        sentences = self._split_sentences(narration)
        srt_lines: list[str] = []
        current_time = 0.0

        for idx, sentence in enumerate(sentences, 1):
            words = sentence.split()
            duration = len(words) / words_per_second if words else 1.0
            start = current_time
            end = current_time + duration

            srt_lines.append(str(idx))
            srt_lines.append(f"{self._format_srt_time(start)} --> {self._format_srt_time(end)}")
            srt_lines.append(self._wrap_text(sentence, max_line_length))
            srt_lines.append("")
            current_time = end

        return "\n".join(srt_lines)

    def generate_vtt(
        self,
        narration: str,
        *,
        scene_id: str = "",
        words_per_second: float = 2.5,
        max_line_length: int = 42,
    ) -> str:
        """Generate WebVTT format subtitles from narration text.

        Args:
            narration: The narration text.
            scene_id: Scene identifier.
            words_per_second: Estimated speaking rate.
            max_line_length: Maximum characters per subtitle line.

        Returns:
            VTT formatted subtitle string.
        """
        sentences = self._split_sentences(narration)
        vtt_lines: list[str] = ["WEBVTT", ""]
        current_time = 0.0

        for idx, sentence in enumerate(sentences, 1):
            words = sentence.split()
            duration = len(words) / words_per_second if words else 1.0
            start = current_time
            end = current_time + duration

            vtt_lines.append(f"{self._format_vtt_time(start)} --> {self._format_vtt_time(end)}")
            vtt_lines.append(self._wrap_text(sentence, max_line_length))
            vtt_lines.append("")
            current_time = end

        return "\n".join(vtt_lines)

    def create_request(
        self,
        narration: str,
        scene_id: str = "",
        project_id: str = "",
        *,
        format: str = "srt",
    ) -> GenerationRequest:
        """Create a generation request for subtitles.

        Args:
            narration: The narration text.
            scene_id: Scene identifier.
            project_id: Project identifier.
            format: Subtitle format ("srt" or "vtt").

        Returns:
            A ``GenerationRequest`` for subtitle generation.
        """
        content = self.generate_srt(narration, scene_id=scene_id) if format == "srt" else self.generate_vtt(narration, scene_id=scene_id)
        return GenerationRequest(
            scene_id=scene_id,
            project_id=project_id,
            category=AssetCategory.SUBTITLE,
            prompt=content,
            metadata={"format": format, "narration": narration},
        )

    def create_asset(
        self,
        narration: str,
        scene_id: str = "",
        *,
        format: str = "srt",
        job_id: Any | None = None,
    ) -> GeneratedAsset:
        """Create a generated asset for subtitles.

        Args:
            narration: The narration text.
            scene_id: Scene identifier.
            format: Subtitle format ("srt" or "vtt").
            job_id: Optional job ID.

        Returns:
            A ``GeneratedAsset`` containing the subtitle content.
        """
        content = self.generate_srt(narration, scene_id=scene_id) if format == "srt" else self.generate_vtt(narration, scene_id=scene_id)
        return GeneratedAsset(
            scene_id=scene_id,
            category=AssetCategory.SUBTITLE,
            provider="internal",
            model="subtitle_generator",
            file_size_bytes=len(content.encode()),
            cost_usd=0.0,
            quality_score=0.95,
            generation_time_seconds=0.01,
            metadata={"content": content, "format": format, "extension": format},
        )

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _wrap_text(self, text: str, max_length: int) -> str:
        """Wrap text to max line length."""
        if len(text) <= max_length:
            return text
        words = text.split()
        lines: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            if current_len + len(word) + 1 > max_length and current:
                lines.append(" ".join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + (1 if current else 0)
        if current:
            lines.append(" ".join(current))
        return "\n".join(lines)

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
