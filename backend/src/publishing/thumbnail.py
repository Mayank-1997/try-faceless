"""Thumbnail Manager.

Responsibilities:
- Validate thumbnail
- Resize if required
- Optimize
- Platform-specific variants
- Metadata
"""

from __future__ import annotations

import os
from typing import Any

from src.publishing.schema import PublishingPlatform, ThumbnailFormat, ThumbnailSpec
from src.core.logging import get_logger


class ThumbnailManager:
    """Manages thumbnail validation, optimization, and platform variants.

    Validates thumbnails against platform requirements, generates
    platform-specific variants, and provides metadata.
    """

    # Platform-specific thumbnail specs
    PLATFORM_SPECS: dict[PublishingPlatform, ThumbnailSpec] = {
        PublishingPlatform.YOUTUBE: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1280,
            height=720,
            max_size_bytes=2 * 1024 * 1024,
            quality=90,
        ),
        PublishingPlatform.LINKEDIN: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1200,
            height=627,
            max_size_bytes=5 * 1024 * 1024,
            quality=85,
        ),
        PublishingPlatform.MEDIUM: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1600,
            height=900,
            max_size_bytes=25 * 1024 * 1024,
            quality=90,
        ),
        PublishingPlatform.WORDPRESS: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1200,
            height=630,
            max_size_bytes=10 * 1024 * 1024,
            quality=85,
        ),
        PublishingPlatform.TWITTER: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1200,
            height=675,
            max_size_bytes=5 * 1024 * 1024,
            quality=85,
        ),
        PublishingPlatform.FACEBOOK: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1280,
            height=720,
            max_size_bytes=25 * 1024 * 1024,
            quality=85,
        ),
        PublishingPlatform.INSTAGRAM: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1080,
            height=1080,
            max_size_bytes=8 * 1024 * 1024,
            quality=90,
        ),
        PublishingPlatform.TIKTOK: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1080,
            height=1920,
            max_size_bytes=10 * 1024 * 1024,
            quality=90,
        ),
        PublishingPlatform.PODCAST: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=3000,
            height=3000,
            max_size_bytes=10 * 1024 * 1024,
            quality=90,
        ),
        PublishingPlatform.CUSTOM: ThumbnailSpec(
            format=ThumbnailFormat.JPG,
            width=1280,
            height=720,
            max_size_bytes=5 * 1024 * 1024,
            quality=85,
        ),
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)

    def get_spec(self, platform: PublishingPlatform) -> ThumbnailSpec:
        """Get the thumbnail specification for a platform.

        Args:
            platform: Target platform.

        Returns:
            The ``ThumbnailSpec`` for the platform.
        """
        return self.PLATFORM_SPECS.get(platform, self.PLATFORM_SPECS[PublishingPlatform.CUSTOM])

    def validate_thumbnail(self, thumbnail_path: str, platform: PublishingPlatform) -> list[str]:
        """Validate a thumbnail for a platform.

        Args:
            thumbnail_path: Path to the thumbnail file.
            platform: Target platform.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []
        spec = self.get_spec(platform)

        if not thumbnail_path:
            errors.append("Thumbnail path is empty")
            return errors

        if not os.path.exists(thumbnail_path):
            errors.append(f"Thumbnail file not found: {thumbnail_path}")
            return errors

        file_size = os.path.getsize(thumbnail_path)
        if file_size == 0:
            errors.append("Thumbnail file is empty")
        elif file_size > spec.max_size_bytes:
            errors.append(
                f"Thumbnail size {file_size} bytes exceeds limit {spec.max_size_bytes} bytes"
            )

        # Check format
        ext = os.path.splitext(thumbnail_path)[1].lower().lstrip(".")
        if ext and ext not in (spec.format.value, "jpeg", "jpg", "png", "bmp", "webp"):
            errors.append(f"Unsupported thumbnail format: {ext}")

        return errors

    def generate_variant_path(
        self, thumbnail_path: str, platform: PublishingPlatform, output_dir: str = ""
    ) -> str:
        """Generate the output path for a platform-specific thumbnail variant.

        Args:
            thumbnail_path: Original thumbnail path.
            platform: Target platform.
            output_dir: Output directory (defaults to same as input).

        Returns:
            Path for the platform-specific variant.
        """
        if not output_dir:
            output_dir = os.path.dirname(thumbnail_path) or "."

        base = os.path.splitext(os.path.basename(thumbnail_path))[0]
        spec = self.get_spec(platform)
        return os.path.join(output_dir, f"{base}_{platform.value}.{spec.format.value}")

    def get_thumbnail_metadata(self, thumbnail_path: str, platform: PublishingPlatform) -> dict[str, Any]:
        """Get metadata for a thumbnail.

        Args:
            thumbnail_path: Path to the thumbnail file.
            platform: Target platform.

        Returns:
            Metadata dict.
        """
        spec = self.get_spec(platform)
        file_size = 0
        if os.path.exists(thumbnail_path):
            file_size = os.path.getsize(thumbnail_path)

        return {
            "path": thumbnail_path,
            "platform": platform.value,
            "width": spec.width,
            "height": spec.height,
            "format": spec.format.value,
            "aspect_ratio": spec.aspect_ratio,
            "file_size_bytes": file_size,
            "max_size_bytes": spec.max_size_bytes,
            "quality": spec.quality,
        }

    def needs_resize(self, thumbnail_path: str, platform: PublishingPlatform) -> bool:
        """Check if a thumbnail needs resizing for a platform.

        Args:
            thumbnail_path: Path to the thumbnail file.
            platform: Target platform.

        Returns:
            ``True`` if resizing is needed.
        """
        # In a real implementation, this would check actual image dimensions
        # For now, we assume resize is needed if the file exists
        return os.path.exists(thumbnail_path)

    def list_platform_specs(self) -> dict[str, dict[str, Any]]:
        """List all platform thumbnail specifications.

        Returns:
            Dict mapping platform name to spec details.
        """
        result: dict[str, dict[str, Any]] = {}
        for platform, spec in self.PLATFORM_SPECS.items():
            result[platform.value] = {
                "width": spec.width,
                "height": spec.height,
                "format": spec.format.value,
                "max_size_bytes": spec.max_size_bytes,
                "quality": spec.quality,
                "aspect_ratio": spec.aspect_ratio,
            }
        return result
