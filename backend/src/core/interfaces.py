"""Abstract base interfaces for all providers, gateways, and services.

Every concrete implementation (Gemini, Imagen, Veo, Google TTS, FFmpeg,
Local Storage, etc.) must inherit the corresponding interface defined
here.  This ensures:

- **Swappability**: providers can be changed via configuration only.
- **Testability**: mocks can implement the same interface.
- **Consistency**: all providers expose the same method signatures.
- **Dependency inversion**: high-level modules depend on abstractions,
  not concrete implementations.

Usage::

    from src.core.interfaces import LLMProvider

    class GeminiProvider(LLMProvider):
        async def generate(self, request: LLMRequest) -> LLMResponse:
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from src.core.enums import AIProvider


# ---------------------------------------------------------------------------
# Generic type variables for response models
# ---------------------------------------------------------------------------
T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared dataclasses for request/response contracts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ProviderConfig:
    """Configuration passed to a provider at initialization time.

    Providers receive this object instead of reading environment variables
    directly, ensuring they remain decoupled from the configuration system.
    """

    api_key: str
    model: str
    max_retries: int = 3
    request_timeout: int = 120
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthStatus:
    """Result of a provider health check."""

    healthy: bool
    provider: str
    latency_ms: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoGenerationPayload:
    """Downloaded video bytes plus an optional provider-side video resource.

    Veo extension requests must reference the original provider-side video,
    not a downloaded local copy.  Providers that do not support extension can
    continue returning raw bytes through ``VideoProvider.generate_video``.
    """

    video_bytes: bytes
    remote_video: Any | None = None


# ---------------------------------------------------------------------------
# LLM Provider Interface
# ---------------------------------------------------------------------------
class LLMProvider(ABC):
    """Abstract interface for Large Language Model providers.

    Implementations: Gemini (current), OpenAI, Claude, OpenRouter,
    Local Models (future).
    """

    @property
    @abstractmethod
    def provider_name(self) -> AIProvider:
        """Return the provider identifier from the ``AIProvider`` enum."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the provider with configuration (API keys, model, etc.)."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion from a prompt.

        Args:
            prompt: The input prompt string.
            **kwargs: Provider-specific options (temperature, max_tokens, etc.).

        Returns:
            The generated text response.
        """

    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Generate a completion and parse it as JSON.

        Args:
            prompt: The input prompt string.
            **kwargs: Provider-specific options.

        Returns:
            Parsed JSON dictionary.

        Raises:
            AIProviderError: If the response cannot be parsed as JSON.
        """

    @abstractmethod
    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream a completion token-by-token.

        Args:
            prompt: The input prompt string.
            **kwargs: Provider-specific options.

        Yields:
            Chunks of generated text as they arrive.
        """

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text.

        Args:
            text: The text to count tokens for.

        Returns:
            The token count.
        """

    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the USD cost for a request.

        Args:
            input_tokens: Number of input (prompt) tokens.
            output_tokens: Number of output (completion) tokens.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check if the provider is reachable and operational.

        Returns:
            A ``HealthStatus`` indicating provider health.
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources held by the provider."""


# ---------------------------------------------------------------------------
# Image Provider Interface
# ---------------------------------------------------------------------------
class ImageProvider(ABC):
    """Abstract interface for AI image generation providers.

    Implementations: Imagen (current), GPT Image, Flux, Stable Diffusion,
    Ideogram (future).
    """

    @property
    @abstractmethod
    def provider_name(self) -> AIProvider:
        """Return the provider identifier."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the provider."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1920,
        height: int = 1080,
        negative_prompt: str | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the desired image.
            width: Output image width in pixels.
            height: Output image height in pixels.
            negative_prompt: Elements to avoid in the generated image.
            seed: Random seed for reproducibility.
            **kwargs: Provider-specific options.

        Returns:
            Raw image bytes (PNG format).
        """

    @abstractmethod
    def calculate_cost(self, width: int, height: int) -> float:
        """Calculate the USD cost for generating an image at the given resolution.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# Video Provider Interface
# ---------------------------------------------------------------------------
class VideoProvider(ABC):
    """Abstract interface for AI video generation providers.

    Implementations: Google Veo (current), Runway, Fal, Minimax, Pika,
    Luma (future).
    """

    @property
    @abstractmethod
    def provider_name(self) -> AIProvider:
        """Return the provider identifier."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the provider."""

    @abstractmethod
    async def generate_video(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate a video from a text prompt.

        Args:
            prompt: Text description of the desired video.
            duration_seconds: Desired video length in seconds.
            width: Output video width in pixels.
            height: Output video height in pixels.
            fps: Frames per second.
            negative_prompt: Elements to avoid.
            seed: Random seed for reproducibility.
            **kwargs: Provider-specific options.

        Returns:
            Raw video bytes (MP4 format).
        """

    @abstractmethod
    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate the USD cost for generating a video.

        Args:
            duration_seconds: Video duration in seconds.
            resolution: Resolution string (e.g. "1920x1080").

        Returns:
            Cost in USD.
        """

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# Voice Provider Interface
# ---------------------------------------------------------------------------
class VoiceProvider(ABC):
    """Abstract interface for text-to-speech providers.

    Implementations: Google TTS (current), ElevenLabs, Azure, PlayHT,
    Cartesia (future).
    """

    @property
    @abstractmethod
    def provider_name(self) -> AIProvider:
        """Return the provider identifier."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the provider."""

    @abstractmethod
    async def generate_speech(
        self,
        text: str,
        *,
        language: str = "en-US",
        voice_name: str | None = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        **kwargs: Any,
    ) -> bytes:
        """Generate speech audio from text.

        Args:
            text: The text to synthesise.
            language: BCP-47 language code (e.g. "en-US").
            voice_name: Specific voice identifier (provider-dependent).
            speaking_rate: Speed multiplier (1.0 = normal).
            pitch: Pitch adjustment in semitones (0.0 = normal).
            **kwargs: Provider-specific options.

        Returns:
            Raw audio bytes (MP3 or WAV format).
        """

    @abstractmethod
    def calculate_cost(self, character_count: int) -> float:
        """Calculate the USD cost for generating speech.

        Args:
            character_count: Number of characters in the input text.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# Renderer Interface
# ---------------------------------------------------------------------------
class Renderer(ABC):
    """Abstract interface for video rendering engines.

    Implementations: FFmpeg (current), Cloud Rendering, GPU Rendering,
    MoviePy (future).
    """

    @property
    @abstractmethod
    def renderer_name(self) -> str:
        """Return the renderer name (e.g. "ffmpeg", "moviepy")."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the renderer."""

    @abstractmethod
    async def render(
        self,
        scenes: list[dict[str, Any]],
        output_path: str,
        *,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        **kwargs: Any,
    ) -> str:
        """Render a complete video from a list of scene definitions.

        Args:
            scenes: Ordered list of scene dictionaries containing asset
                paths, timings, transitions, and effects.
            output_path: Destination file path for the rendered video.
            width: Output video width.
            height: Output video height.
            fps: Frames per second.
            **kwargs: Renderer-specific options.

        Returns:
            Path to the rendered video file.
        """

    @abstractmethod
    async def merge(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Merge a video track with an audio track.

        Args:
            video_path: Path to the input video file.
            audio_path: Path to the input audio file.
            output_path: Destination for the merged output.
            **kwargs: Renderer-specific options.

        Returns:
            Path to the merged file.
        """

    @abstractmethod
    async def concatenate(self, video_paths: list[str], output_path: str, **kwargs: Any) -> str:
        """Concatenate multiple video clips into a single video.

        Args:
            video_paths: Ordered list of video file paths to concatenate.
            output_path: Destination for the concatenated output.
            **kwargs: Renderer-specific options.

        Returns:
            Path to the concatenated file.
        """

    @abstractmethod
    async def burn_subtitles(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        **kwargs: Any,
    ) -> str:
        """Burn subtitle file into a video (hardcode subtitles).

        Args:
            video_path: Path to the input video.
            subtitle_path: Path to the subtitle file (SRT or VTT).
            output_path: Destination for the output.
            **kwargs: Renderer-specific options (font, size, color, etc.).

        Returns:
            Path to the video with burned subtitles.
        """

    @abstractmethod
    async def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        *,
        timestamp: float = 0.0,
        width: int = 1280,
        height: int = 720,
        **kwargs: Any,
    ) -> str:
        """Extract a thumbnail frame from a video.

        Args:
            video_path: Path to the source video.
            output_path: Destination for the thumbnail image.
            timestamp: Time in seconds to extract the frame at.
            width: Thumbnail width.
            height: Thumbnail height.
            **kwargs: Renderer-specific options.

        Returns:
            Path to the generated thumbnail.
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# Storage Provider Interface
# ---------------------------------------------------------------------------
class StorageProvider(ABC):
    """Abstract interface for file storage backends.

    Implementations: Local filesystem (current), AWS S3, Google Cloud
    Storage, Azure Blob, MinIO (future).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the storage provider name (e.g. "local", "s3", "gcs")."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the storage provider."""

    @abstractmethod
    async def upload(self, data: bytes, key: str, *, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to storage and return the storage URI.

        Args:
            data: Raw bytes to store.
            key: Storage key / path (e.g. "projects/abc/images/scene1.png").
            content_type: MIME type of the content.

        Returns:
            The storage URI (e.g. "local:///app/storage/projects/abc/..." or
            "s3://bucket/key").
        """

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download bytes from storage.

        Args:
            key: Storage key / path.

        Returns:
            The raw bytes stored at the given key.

        Raises:
            StorageError: If the key does not exist or download fails.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a file from storage.

        Args:
            key: Storage key / path.

        Returns:
            ``True`` if the file was deleted, ``False`` if it did not exist.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            key: Storage key / path.

        Returns:
            ``True`` if the file exists.
        """

    @abstractmethod
    async def get_url(self, key: str, *, expires_in: int = 3600) -> str:
        """Get a accessible URL for a stored file.

        Args:
            key: Storage key / path.
            expires_in: URL validity duration in seconds (for presigned URLs).

        Returns:
            A URL that can be used to access the file.
        """

    @abstractmethod
    async def list_files(self, prefix: str, *, limit: int = 100) -> list[str]:
        """List files under a given prefix.

        Args:
            prefix: Path prefix to search under.
            limit: Maximum number of results.

        Returns:
            List of storage keys matching the prefix.
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources."""


# ---------------------------------------------------------------------------
# Prompt Loader Interface
# ---------------------------------------------------------------------------
class PromptLoader(ABC):
    """Abstract interface for prompt template loading and rendering.

    Implementations: File-based prompt loader (current), database-backed
    prompt loader (future).
    """

    @abstractmethod
    async def load(self, agent_type: str, prompt_name: str, version: str | None = None) -> str:
        """Load a prompt template by agent type, name, and optional version.

        Args:
            agent_type: The agent category (e.g. "research", "script").
            prompt_name: The specific prompt name (e.g. "web_search").
            version: Semantic version string. If ``None``, loads the latest.

        Returns:
            The raw prompt template string with placeholders.

        Raises:
            PromptException: If the prompt cannot be found.
        """

    @abstractmethod
    def render(self, template: str, variables: dict[str, Any]) -> str:
        """Render a prompt template by substituting variables.

        Args:
            template: The raw template string with ``{{variable}}`` placeholders.
            variables: Dictionary of variable names to values.

        Returns:
            The rendered prompt string with all variables substituted.

        Raises:
            PromptException: If required variables are missing.
        """

    @abstractmethod
    async def get_metadata(self, agent_type: str, prompt_name: str, version: str | None = None) -> dict[str, Any]:
        """Get metadata for a prompt template.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.
            version: Semantic version. If ``None``, uses the latest.

        Returns:
            Dictionary containing metadata (author, description, variables,
            model_compatibility, etc.).
        """

    @abstractmethod
    async def list_versions(self, agent_type: str, prompt_name: str) -> list[str]:
        """List all available versions of a prompt.

        Args:
            agent_type: The agent category.
            prompt_name: The specific prompt name.

        Returns:
            List of version strings, sorted from newest to oldest.
        """

    @abstractmethod
    async def list_prompts(self, agent_type: str) -> list[str]:
        """List all prompt names available for an agent type.

        Args:
            agent_type: The agent category.

        Returns:
            List of prompt names.
        """


# ---------------------------------------------------------------------------
# Cost Calculator Interface
# ---------------------------------------------------------------------------
class CostCalculator(ABC):
    """Abstract interface for calculating operation costs.

    This interface allows different cost models to be plugged in
    (e.g. flat-rate, tiered, dynamic pricing).
    """

    @abstractmethod
    def calculate_llm_cost(self, provider: AIProvider, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of an LLM request.

        Args:
            provider: The AI provider used.
            model: The specific model identifier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    def calculate_image_cost(self, provider: AIProvider, width: int, height: int) -> float:
        """Calculate the cost of an image generation request.

        Args:
            provider: The AI provider used.
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    def calculate_video_cost(self, provider: AIProvider, duration_seconds: float, resolution: str) -> float:
        """Calculate the cost of a video generation request.

        Args:
            provider: The AI provider used.
            duration_seconds: Video duration in seconds.
            resolution: Resolution string (e.g. "1920x1080").

        Returns:
            Cost in USD.
        """

    @abstractmethod
    def calculate_voice_cost(self, provider: AIProvider, character_count: int) -> float:
        """Calculate the cost of a voice generation request.

        Args:
            provider: The AI provider used.
            character_count: Number of characters synthesised.

        Returns:
            Cost in USD.
        """

    @abstractmethod
    def calculate_render_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate the cost of a rendering operation.

        Args:
            duration_seconds: Video duration in seconds.
            resolution: Resolution string.

        Returns:
            Cost in USD.
        """
