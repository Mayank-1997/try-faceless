"""Export Engine.

Supports MP4, MOV, MKV, and future formats.
Generates preview, final video, thumbnail, and metadata.
"""

from __future__ import annotations

import os
from typing import Any

from src.composition.schema import (
    CompositionDocument,
    ExportFormat,
    ExportProfile,
    ExportResolution,
    PreviewResult,
)
from src.core.logging import get_logger


class ExportEngine:
    """Handles video export in multiple formats and resolutions.

    Generates:
    - Final video (MP4, MOV, MKV)
    - Low-resolution preview
    - Thumbnail image
    - Metadata file
    """

    # Encoding presets
    _PRESETS: dict[str, ExportProfile] = {
        "1080p": ExportProfile(
            format=ExportFormat.MP4,
            resolution="1920x1080",
            width=1920, height=1080,
            fps=30, codec="libx264",
            video_bitrate="5M", audio_bitrate="192k",
            preset="medium", crf=23,
        ),
        "1440p": ExportProfile(
            format=ExportFormat.MP4,
            resolution="2560x1440",
            width=2560, height=1440,
            fps=30, codec="libx264",
            video_bitrate="10M", audio_bitrate="192k",
            preset="medium", crf=23,
        ),
        "4k": ExportProfile(
            format=ExportFormat.MP4,
            resolution="3840x2160",
            width=3840, height=2160,
            fps=30, codec="libx264",
            video_bitrate="25M", audio_bitrate="256k",
            preset="slow", crf=23,
        ),
        "square": ExportProfile(
            format=ExportFormat.MP4,
            resolution="1080x1080",
            width=1080, height=1080,
            fps=30, codec="libx264",
            video_bitrate="4M", audio_bitrate="192k",
            preset="medium", crf=23,
        ),
        "portrait": ExportProfile(
            format=ExportFormat.MP4,
            resolution="1080x1920",
            width=1080, height=1920,
            fps=30, codec="libx264",
            video_bitrate="4M", audio_bitrate="192k",
            preset="medium", crf=23,
        ),
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def get_preset(self, name: str) -> ExportProfile | None:
        """Get an encoding preset by name.

        Args:
            name: Preset name (1080p, 1440p, 4k, square, portrait).

        Returns:
            The preset ``ExportProfile``, or ``None``.
        """
        return self._PRESETS.get(name)

    def list_presets(self) -> list[str]:
        """List all available preset names."""
        return list(self._PRESETS.keys())

    def create_profile(
        self,
        format: ExportFormat = ExportFormat.MP4,
        resolution: ExportResolution = ExportResolution.P1080,
        *,
        fps: int = 30,
        codec: str = "libx264",
        audio_codec: str = "aac",
        video_bitrate: str = "5M",
        audio_bitrate: str = "192k",
        preset: str = "medium",
        crf: int = 23,
        hardware_acceleration: bool = False,
    ) -> ExportProfile:
        """Create a custom export profile.

        Args:
            format: Output format.
            resolution: Output resolution.
            fps: Frames per second.
            codec: Video codec.
            audio_codec: Audio codec.
            video_bitrate: Video bitrate.
            audio_bitrate: Audio bitrate.
            preset: Encoding preset.
            crf: Constant Rate Factor.
            hardware_acceleration: Enable hardware acceleration.

        Returns:
            An ``ExportProfile``.
        """
        w, h = (int(x) for x in resolution.value.split("x"))
        return ExportProfile(
            format=format,
            resolution=resolution.value,
            width=w, height=h,
            fps=fps,
            codec=codec,
            audio_codec=audio_codec,
            video_bitrate=video_bitrate,
            audio_bitrate=audio_bitrate,
            preset=preset,
            crf=crf,
            hardware_acceleration=hardware_acceleration,
        )

    def get_preview_profile(self, full_profile: ExportProfile) -> ExportProfile:
        """Create a low-resolution preview profile from a full profile.

        Args:
            full_profile: The full export profile.

        Returns:
            A low-resolution ``ExportProfile`` for preview.
        """
        preview_w = 640
        preview_h = int(preview_w * full_profile.height / full_profile.width)
        return ExportProfile(
            format=ExportFormat.MP4,
            resolution=f"{preview_w}x{preview_h}",
            width=preview_w,
            height=preview_h,
            fps=min(full_profile.fps, 24),
            codec="libx264",
            audio_codec="aac",
            video_bitrate="1M",
            audio_bitrate="128k",
            preset="fast",
            crf=28,
        )

    def generate_thumbnail_path(self, output_dir: str, project_id: str) -> str:
        """Generate the thumbnail file path.

        Args:
            output_dir: Output directory.
            project_id: Project identifier.

        Returns:
            Thumbnail file path.
        """
        return os.path.join(output_dir, f"{project_id}_thumbnail.png")

    def generate_metadata(self, composition: CompositionDocument, output_path: str) -> dict[str, Any]:
        """Generate metadata for the exported video.

        Args:
            composition: The composition document.
            output_path: Path to the rendered video.

        Returns:
            Metadata dict.
        """
        ep = composition.export_profile
        return {
            "title": composition.metadata.get("title", ""),
            "project_id": composition.project_id,
            "duration_seconds": composition.total_duration,
            "resolution": f"{ep.width}x{ep.height}",
            "fps": ep.fps,
            "codec": ep.codec,
            "audio_codec": ep.audio_codec,
            "format": ep.format.value,
            "video_bitrate": ep.video_bitrate,
            "audio_bitrate": ep.audio_bitrate,
            "scene_count": composition.scene_count,
            "track_count": composition.track_count,
            "output_path": output_path,
            "composition_id": str(composition.id),
            "version": composition.version,
        }

    def list_formats(self) -> list[str]:
        """List all supported export formats."""
        return [f.value for f in ExportFormat]

    def list_resolutions(self) -> list[str]:
        """List all supported export resolutions."""
        return [r.value for r in ExportResolution]
