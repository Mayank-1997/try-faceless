"""Asset entities — generated or fetched media assets for scenes.

Uses inheritance to model different asset types while sharing a common
base. Each asset tracks its provider, generation cost, storage location,
quality, and lifecycle status.

Inheritance hierarchy::

    BaseAsset
    ├── ImageAsset
    ├── VideoAsset
    ├── VoiceAsset
    ├── SubtitleAsset
    └── ThumbnailAsset
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from typing import Any
from uuid import UUID, uuid4

from src.core.enums import (
    AIProvider,
    AssetGenerationStatus,
    AssetType,
    StorageType,
)


class BaseAsset:
    """Base class for all generated or fetched assets.

    Attributes:
        id: UUID primary key.
        project_id: UUID of the owning project.
        scene_id: UUID of the scene this asset belongs to (optional).
        asset_type: Discriminator for the asset subtype.
        provider: AI provider that generated the asset.
        prompt_version: Version of the prompt used.
        generation_cost_usd: Cost of generation in USD.
        generation_time_seconds: Wall-clock generation time.
        generation_status: Asset generation lifecycle.
        storage_type: Where the asset is stored.
        storage_ref: Path or URI to the stored asset.
        metadata: Arbitrary key-value metadata.
        quality_score: Quality assessment score (0.0–1.0).
        created_by: UUID of the user or agent that created this asset.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        project_id: UUID,
        scene_id: UUID | None = None,
        asset_type: AssetType = AssetType.IMAGE,
        provider: AIProvider | str = "",
        prompt_version: str = "",
        generation_cost_usd: float = 0.0,
        generation_time_seconds: float = 0.0,
        generation_status: AssetGenerationStatus = AssetGenerationStatus.PLANNED,
        storage_type: StorageType = StorageType.LOCAL,
        storage_ref: str = "",
        metadata: dict[str, Any] | None = None,
        quality_score: float | None = None,
        created_by: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.project_id = project_id
        self.scene_id = scene_id
        self.asset_type = asset_type
        self.provider = provider
        self.prompt_version = prompt_version
        self.generation_cost_usd = generation_cost_usd
        self.generation_time_seconds = generation_time_seconds
        self.generation_status = generation_status
        self.storage_type = storage_type
        self.storage_ref = storage_ref
        self.metadata = metadata or {}
        self.quality_score = quality_score
        self.created_by = created_by
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = updated_at or datetime.now(dt_timezone.utc)

    def mark_ready(self) -> None:
        """Mark the asset as ready for use."""
        self.generation_status = AssetGenerationStatus.READY
        self.updated_at = datetime.now(dt_timezone.utc)

    def mark_failed(self) -> None:
        """Mark the asset generation as failed."""
        self.generation_status = AssetGenerationStatus.FAILED
        self.updated_at = datetime.now(dt_timezone.utc)

    def reject(self) -> None:
        """Mark the asset as rejected in review."""
        self.generation_status = AssetGenerationStatus.REJECTED
        self.updated_at = datetime.now(dt_timezone.utc)

    @property
    def is_ready(self) -> bool:
        """Check if the asset is ready for use."""
        return self.generation_status == AssetGenerationStatus.READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "scene_id": str(self.scene_id) if self.scene_id else None,
            "asset_type": self.asset_type.value,
            "provider": self.provider.value if hasattr(self.provider, "value") else str(self.provider),
            "prompt_version": self.prompt_version,
            "generation_cost_usd": self.generation_cost_usd,
            "generation_time_seconds": self.generation_time_seconds,
            "generation_status": self.generation_status.value,
            "storage_type": self.storage_type.value,
            "storage_ref": self.storage_ref,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ImageAsset(BaseAsset):
    """A generated or fetched image asset.

    Attributes:
        width: Image width in pixels.
        height: Image height in pixels.
        format: Image format (png, jpg, webp).
        prompt: The rendered prompt used for generation.
        negative_prompt: Negative prompt for exclusion.
    """

    def __init__(
        self,
        *,
        width: int = 0,
        height: int = 0,
        format: str = "png",
        prompt: str = "",
        negative_prompt: str = "",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("asset_type", AssetType.IMAGE)
        super().__init__(**kwargs)
        self.width = width
        self.height = height
        self.format = format
        self.prompt = prompt
        self.negative_prompt = negative_prompt

    @property
    def dimensions(self) -> str:
        """Return dimensions as 'WxH' string."""
        return f"{self.width}x{self.height}"

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
        })
        return d


class VideoAsset(BaseAsset):
    """A generated or fetched video asset.

    Attributes:
        width: Video width in pixels.
        height: Video height in pixels.
        duration_seconds: Video duration in seconds.
        fps: Frames per second.
        format: Video format (mp4, webm).
        prompt: The rendered prompt used for generation.
    """

    def __init__(
        self,
        *,
        width: int = 0,
        height: int = 0,
        duration_seconds: float = 0.0,
        fps: int = 30,
        format: str = "mp4",
        prompt: str = "",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("asset_type", AssetType.VIDEO)
        super().__init__(**kwargs)
        self.width = width
        self.height = height
        self.duration_seconds = duration_seconds
        self.fps = fps
        self.format = format
        self.prompt = prompt

    @property
    def dimensions(self) -> str:
        """Return dimensions as 'WxH' string."""
        return f"{self.width}x{self.height}"

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "width": self.width,
            "height": self.height,
            "duration_seconds": self.duration_seconds,
            "fps": self.fps,
            "format": self.format,
            "prompt": self.prompt,
        })
        return d


class VoiceAsset(BaseAsset):
    """A generated voice/narration audio asset.

    Attributes:
        duration_seconds: Audio duration in seconds.
        language: Language code for the voice.
        voice_name: Name of the voice used.
        speaking_rate: Speech rate multiplier.
        pitch: Pitch adjustment.
        format: Audio format (mp3, wav).
    """

    def __init__(
        self,
        *,
        duration_seconds: float = 0.0,
        language: str = "en-US",
        voice_name: str | None = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        format: str = "mp3",
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("asset_type", AssetType.VOICE)
        super().__init__(**kwargs)
        self.duration_seconds = duration_seconds
        self.language = language
        self.voice_name = voice_name
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.format = format

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "voice_name": self.voice_name,
            "speaking_rate": self.speaking_rate,
            "pitch": self.pitch,
            "format": self.format,
        })
        return d


class SubtitleAsset(BaseAsset):
    """A generated subtitle file asset.

    Attributes:
        language: Subtitle language code.
        format: Subtitle format (srt, vtt).
        word_count: Number of words in the subtitle.
    """

    def __init__(
        self,
        *,
        language: str = "en",
        format: str = "srt",
        word_count: int = 0,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("asset_type", AssetType.SUBTITLE)
        super().__init__(**kwargs)
        self.language = language
        self.format = format
        self.word_count = word_count

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "language": self.language,
            "format": self.format,
            "word_count": self.word_count,
        })
        return d


class ThumbnailAsset(BaseAsset):
    """A generated thumbnail image asset.

    Attributes:
        width: Thumbnail width in pixels.
        height: Thumbnail height in pixels.
        format: Image format (png, jpg).
        is_default: Whether this is the default thumbnail.
    """

    def __init__(
        self,
        *,
        width: int = 1280,
        height: int = 720,
        format: str = "jpg",
        is_default: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("asset_type", AssetType.THUMBNAIL)
        super().__init__(**kwargs)
        self.width = width
        self.height = height
        self.format = format
        self.is_default = is_default

    @property
    def dimensions(self) -> str:
        """Return dimensions as 'WxH' string."""
        return f"{self.width}x{self.height}"

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d.update({
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "is_default": self.is_default,
        })
        return d
