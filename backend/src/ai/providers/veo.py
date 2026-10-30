"""Veo video generation provider — concrete implementation of ``VideoProvider``.

Wraps the Google Veo video generation API behind the common
``VideoProvider`` interface.

Uses the ``google-genai`` SDK (Gemini API), which exposes Veo as a
long-running operation:

    client = genai.Client(api_key=...)
    op = client.models.generate_videos(model=..., prompt=..., config=...)
    while not op.done:
        op = client.operations.get(op)
    video = op.response.generated_videos[0].video
    client.files.download(file=video)
    data = video.video_bytes

The provider accepts ``GOOGLE_VEO_API_KEY`` if set, but falls back to
``GEMINI_API_KEY`` (passed via ``extra["gemini_api_key"]``) so video
generation works out-of-the-box in environments that only have the
Gemini key configured — the Gemini API serves Veo under the same key.

Model constraints (Veo 3.1 Fast via Gemini API):
- Initial ``duration_seconds`` values are quantised to 4, 6, or 8 seconds.
- Video extension is supported by the Fast/standard models, adds 7 seconds,
  and requires the original provider-side Veo video resource at 720p.
- Aspect ratio is ``16:9`` or ``9:16``; output is MP4 at 24 fps with audio.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.enums import AIProvider
from src.core.exceptions import (
    AIProviderError,
    AIProviderTimeoutError,
    ProviderNotInitializedError,
)
from src.core.interfaces import (
    HealthStatus,
    ProviderConfig,
    VideoGenerationPayload,
    VideoProvider,
)
from src.core.logging import get_logger

_VEO_ALLOWED_DURATIONS = (4, 6, 8)
_VEO_EXTENSION_SECONDS = 7

# How often to poll the long-running generate_videos operation.
_POLL_INTERVAL_SECONDS = 10


def quantize_veo_duration(seconds: float) -> int:
    """Round a requested duration up to a duration Veo supports (4/6/8s)."""
    for allowed in _VEO_ALLOWED_DURATIONS:
        if seconds <= allowed:
            return allowed
    return _VEO_ALLOWED_DURATIONS[-1]


class VeoProvider(VideoProvider):
    """Google Veo implementation of the ``VideoProvider`` interface."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._logger = get_logger(__name__)
        self._initialized = False
        self._cost_per_second: float = 0.05
        self._api_key: str = ""
        self._model_name: str = "veo-3.1-fast-generate-preview"

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.VEO

    @property
    def model_name(self) -> str:
        return self._model_name

    async def initialize(self, config: ProviderConfig) -> None:
        self._config = config
        self._cost_per_second = config.extra.get("cost_per_second", 0.05)

        # Prefer the dedicated Veo key; fall back to the Gemini key —
        # the Gemini API serves Veo models under the same credential.
        self._api_key = config.api_key or config.extra.get("gemini_api_key", "")
        if not self._api_key:
            self._logger.warning(
                "veo_provider_no_api_key",
                message="No GOOGLE_VEO_API_KEY or GEMINI_API_KEY — provider disabled",
            )
            return  # stay uninitialised

        self._model_name = config.model or "veo-3.1-fast-generate-preview"
        self._initialized = True
        self._logger.info(
            "veo_provider_initialized",
            model=self._model_name,
            cost_per_second=self._cost_per_second,
            using_gemini_key=not bool(config.api_key),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise ProviderNotInitializedError(self.provider_name.value)

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
        image: bytes | None = None,
        resolution: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate a video and return only its downloaded bytes."""
        payload = await self.generate_video_with_resource(
            prompt,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            negative_prompt=negative_prompt,
            seed=seed,
            image=image,
            resolution=resolution,
            **kwargs,
        )
        return payload.video_bytes

    async def generate_video_with_resource(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        image: bytes | None = None,
        resolution: str | None = None,
        **kwargs: Any,
    ) -> VideoGenerationPayload:
        """Generate a video while retaining Veo's remote video resource."""
        self._ensure_initialized()
        assert self._config is not None

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._generate_video_sync,
                    prompt,
                    duration_seconds,
                    width,
                    height,
                    fps,
                    negative_prompt,
                    seed,
                    image,
                    resolution,
                ),
                timeout=self._config.request_timeout,
            )
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(self.provider_name.value, self._config.request_timeout)
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("veo_generate_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    async def extend_video(
        self,
        video: Any,
        prompt: str,
        *,
        width: int = 720,
        height: int = 1280,
        fps: int = 24,
        **kwargs: Any,
    ) -> VideoGenerationPayload:
        """Extend a Veo-generated video by the model's fixed extension length."""
        self._ensure_initialized()
        assert self._config is not None
        if "lite" in self._model_name.lower():
            raise AIProviderError(
                self.provider_name.value,
                "Veo video extension is not supported by the Lite model",
            )

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._extend_video_sync,
                    video,
                    prompt,
                    width,
                    height,
                    fps,
                ),
                timeout=self._config.request_timeout,
            )
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(self.provider_name.value, self._config.request_timeout)
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("veo_extension_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    def _generate_video_sync(
        self,
        prompt: str,
        duration_seconds: float,
        width: int,
        height: int,
        fps: int,
        negative_prompt: str | None,
        seed: int | None,
        image: bytes | None,
        requested_resolution: str | None = None,
    ) -> VideoGenerationPayload:
        """Synchronous video generation via the Veo API (``google-genai``).

        ``generate_videos`` returns a long-running operation which must be
        polled until ``done``; the generated video is then downloaded via
        the Files API.  Bounded by ``request_timeout`` — the outer async
        wrapper applies the same deadline via ``asyncio.wait_for``.
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIProviderError(
                self.provider_name.value,
                "google-genai package is required for Veo video generation",
            ) from exc

        client = genai.Client(api_key=self._api_key)

        duration = quantize_veo_duration(duration_seconds)
        resolution = requested_resolution or (
            "1080p" if height >= 1080 and duration == 8 else "720p"
        )
        if resolution not in {"720p", "1080p", "4k"}:
            raise AIProviderError(
                self.provider_name.value,
                f"Unsupported Veo resolution: {resolution}",
            )
        config_kwargs: dict[str, Any] = {
            "aspect_ratio": "16:9" if width >= height else "9:16",
            "duration_seconds": duration,
            "resolution": resolution,
            "number_of_videos": 1,
            # Veo 3.x generates native audio by default on the Gemini API.
        }
        if negative_prompt:
            config_kwargs["negative_prompt"] = negative_prompt
        if seed is not None:
            config_kwargs["seed"] = seed

        self._logger.info(
            "veo_generate_started",
            model=self._model_name,
            duration_seconds=duration,
            resolution=resolution,
            prompt_chars=len(prompt),
        )

        gen_kwargs: dict[str, Any] = {
            "model": self._model_name,
            "prompt": prompt,
            "config": types.GenerateVideosConfig(**config_kwargs),
        }
        if image:
            gen_kwargs["image"] = types.Image(
                image_bytes=image, mime_type="image/png"
            )

        operation = client.models.generate_videos(**gen_kwargs)

        timeout = self._config.request_timeout if self._config else 300
        deadline = time.monotonic() + timeout
        while not operation.done:
            if time.monotonic() > deadline:
                raise AIProviderTimeoutError(self.provider_name.value, timeout)
            time.sleep(_POLL_INTERVAL_SECONDS)
            operation = client.operations.get(operation)

        op_error = getattr(operation, "error", None)
        if op_error:
            raise AIProviderError(self.provider_name.value, str(op_error))

        videos = getattr(getattr(operation, "response", None), "generated_videos", None) or []
        if not videos:
            raise AIProviderError(
                self.provider_name.value,
                "Veo generation completed but returned no video",
            )

        video = videos[0].video
        client.files.download(file=video)
        data = getattr(video, "video_bytes", None)
        if not data:
            raise AIProviderError(
                self.provider_name.value,
                "Veo generation returned no video bytes",
            )

        self._logger.info(
            "veo_generate_completed",
            model=self._model_name,
            duration_seconds=duration,
            video_size_bytes=len(data),
        )
        return VideoGenerationPayload(video_bytes=bytes(data), remote_video=video)

    def _extend_video_sync(
        self,
        video: Any,
        prompt: str,
        width: int,
        height: int,
        fps: int,
    ) -> VideoGenerationPayload:
        """Extend an existing Veo-generated video using its remote resource."""
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise AIProviderError(
                self.provider_name.value,
                "google-genai package is required for Veo video extension",
            ) from exc

        client = genai.Client(api_key=self._api_key)
        config_kwargs: dict[str, Any] = {
            "aspect_ratio": "16:9" if width >= height else "9:16",
            "resolution": "720p",
            "number_of_videos": 1,
        }
        self._logger.info(
            "veo_extension_started",
            model=self._model_name,
            extension_seconds=_VEO_EXTENSION_SECONDS,
            resolution="720p",
            prompt_chars=len(prompt),
        )
        operation = client.models.generate_videos(
            model=self._model_name,
            video=video,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_kwargs),
        )

        timeout = self._config.request_timeout if self._config else 300
        deadline = time.monotonic() + timeout
        while not operation.done:
            if time.monotonic() > deadline:
                raise AIProviderTimeoutError(self.provider_name.value, timeout)
            time.sleep(_POLL_INTERVAL_SECONDS)
            operation = client.operations.get(operation)

        op_error = getattr(operation, "error", None)
        if op_error:
            raise AIProviderError(self.provider_name.value, str(op_error))
        videos = getattr(getattr(operation, "response", None), "generated_videos", None) or []
        if not videos:
            raise AIProviderError(
                self.provider_name.value,
                "Veo extension completed but returned no video",
            )

        extended_video = videos[0].video
        client.files.download(file=extended_video)
        data = getattr(extended_video, "video_bytes", None)
        if not data:
            raise AIProviderError(
                self.provider_name.value,
                "Veo extension returned no video bytes",
            )
        self._logger.info(
            "veo_extension_completed",
            model=self._model_name,
            extension_seconds=_VEO_EXTENSION_SECONDS,
            video_size_bytes=len(data),
        )
        return VideoGenerationPayload(video_bytes=bytes(data), remote_video=extended_video)

    def calculate_extension_cost(self, duration_seconds: float | None = None) -> float:
        # Veo extensions are a fixed 7 seconds; ``duration_seconds`` is
        # accepted for interface parity with providers that bill per
        # requested extension length (e.g. Kling).
        return round(self._cost_per_second * _VEO_EXTENSION_SECONDS, 6)

    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate cost based on per-second pricing.

        Uses the quantised duration — that is what the API actually bills.
        """
        billed = quantize_veo_duration(duration_seconds)
        return round(self._cost_per_second * billed, 6)

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name.value,
                details={"reason": "not initialized"},
            )
        return HealthStatus(
            healthy=True,
            provider=self.provider_name.value,
            details={"model": self._model_name},
        )

    async def shutdown(self) -> None:
        self._initialized = False
        self._logger.info("veo_provider_shutdown")
