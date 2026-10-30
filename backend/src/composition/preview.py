"""Preview Engine.

Initial implementation:
- Low-resolution preview generation

Architecture supports future:
- Timeline previews
- Scene previews
- Audio previews
- Storyboard previews
"""

from __future__ import annotations

from typing import Any

from src.composition.schema import CompositionDocument, ExportProfile, PreviewResult
from src.core.logging import get_logger


class PreviewEngine:
    """Generates low-resolution previews of compositions.

    The preview is a reduced-quality, reduced-resolution version of
    the final video.  Useful for quick review without full rendering.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def create_preview_profile(self, composition: CompositionDocument) -> ExportProfile:
        """Create a preview export profile from a composition.

        Args:
            composition: The composition to preview.

        Returns:
            A low-resolution ``ExportProfile``.
        """
        ep = composition.export_profile
        preview_w = 640
        preview_h = int(preview_w * ep.height / ep.width)
        # Ensure even dimensions (required by some codecs)
        preview_h = preview_h if preview_h % 2 == 0 else preview_h + 1

        return ExportProfile(
            width=preview_w,
            height=preview_h,
            fps=min(ep.fps, 24),
            codec="libx264",
            audio_codec="aac",
            video_bitrate="800k",
            audio_bitrate="96k",
            preset="ultrafast",
            crf=30,
        )

    def create_preview_result(
        self,
        preview_path: str,
        *,
        resolution: str = "640x360",
        duration: float = 0.0,
        file_size: int = 0,
    ) -> PreviewResult:
        """Create a preview result object.

        Args:
            preview_path: Path to the preview file.
            resolution: Preview resolution.
            duration: Preview duration in seconds.
            file_size: Preview file size in bytes.

        Returns:
            A ``PreviewResult``.
        """
        return PreviewResult(
            preview_path=preview_path,
            resolution=resolution,
            duration_seconds=duration,
            file_size_bytes=file_size,
        )

    def estimate_preview_time(self, composition: CompositionDocument) -> float:
        """Estimate preview generation time.

        Args:
            composition: The composition to preview.

        Returns:
            Estimated time in seconds.
        """
        # Preview is ~5x faster than full render
        return composition.total_duration * 0.3

    def estimate_preview_size(self, composition: CompositionDocument) -> int:
        """Estimate preview file size in bytes.

        Args:
            composition: The composition to preview.

        Returns:
            Estimated file size in bytes.
        """
        # ~100KB/s for 640x360 at 800kbps
        return int(composition.total_duration * 100_000)
