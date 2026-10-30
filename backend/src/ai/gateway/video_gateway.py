"""Video Gateway — unified interface for AI video generation.

Agents call the Video Gateway instead of provider-specific APIs. The
gateway handles provider selection, fallback, retries, cost calculation,
and structured logging.

Architecture::

    Agent → VideoGateway → ProviderRegistry → VeoProvider (or fallback)
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from src.application.dto.responses import GenerationResult
from src.core.config_service import ConfigService
from src.core.exceptions import (
    AllProvidersFailedError,
    ProviderException,
    VideoGatewayError,
)
from src.core.interfaces import HealthStatus, VideoGenerationPayload, VideoProvider
from src.core.logging import get_logger


class VideoGateway:
    """Unified gateway for AI video generation operations."""

    def __init__(
        self,
        registry: Any,
        config: ConfigService,
        langfuse_client: Any = None,
    ) -> None:
        self._registry = registry
        self._config = config
        self._langfuse_client = langfuse_client
        self._logger = get_logger(__name__)
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True
        providers = self._registry.get_provider_names_by_type(VideoProvider)
        self._logger.info("video_gateway_initialized", providers=providers)

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
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "video_generation",
        allow_fallback: bool = True,
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        """Generate a video from a text prompt.

        Args:
            prompt: Text description of the desired video.
            duration_seconds: Desired video length in seconds.
            width: Output width in pixels.
            height: Output height in pixels.
            fps: Frames per second.
            negative_prompt: Elements to avoid.
            seed: Random seed for reproducibility.
            correlation_id: Optional correlation ID for tracing.
            trace_id: Optional Langfuse trace ID to attach the generation to.
            generation_name: Name for the Langfuse generation observation.
            **kwargs: Provider-specific options.

        Returns:
            ``GenerationResult`` containing raw video bytes, cost, and metadata.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"vid-{str(hash(prompt))[-8:]}"

        provider = self._get_primary_provider()
        start = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        try:
            video_bytes = await self._call_with_retry(
                provider.generate_video,
                prompt,
                duration_seconds=duration_seconds,
                width=width,
                height=height,
                fps=fps,
                negative_prompt=negative_prompt,
                seed=seed,
                **kwargs,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            resolution = f"{width}x{height}"
            cost = provider.calculate_cost(duration_seconds, resolution)

            self._logger.info(
                "video_generate_success",
                correlation_id=corr_id,
                provider=provider.provider_name.value,
                duration_seconds=duration_seconds,
                resolution=resolution,
                cost_usd=cost,
                latency_ms=latency_ms,
                video_size_bytes=len(video_bytes),
            )

            # Langfuse trace — record as a generation observation
            if self._langfuse_client is not None:
                self._langfuse_client.generation(
                    trace_id=trace_id or corr_id,
                    name=generation_name,
                    provider=provider.provider_name.value,
                    model=self._provider_model(provider),
                    input_content=prompt,
                    output_content={
                        "video_bytes": len(video_bytes),
                        "duration_seconds": duration_seconds,
                        "width": width,
                        "height": height,
                    },
                    cost_usd=cost,
                    start_time=start_dt,
                    end_time=datetime.now(timezone.utc),
                    metadata={
                        "correlation_id": corr_id,
                        "negative_prompt": negative_prompt,
                        "seed": seed,
                        "fps": fps,
                        "resolution": resolution,
                        "video_size_bytes": len(video_bytes),
                        "type": "video_generation",
                    },
                )

            return GenerationResult(
                success=True,
                provider=provider.provider_name.value,
                model=self._provider_model(provider),
                output=video_bytes,
                cost_usd=cost,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                metadata={
                    "duration_seconds": duration_seconds,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "resolution": resolution,
                    "negative_prompt": negative_prompt,
                    "seed": seed,
                },
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "video_generate_failed",
                correlation_id=corr_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            if allow_fallback and self._config.is_feature_enabled("provider_fallback"):
                fallback = await self._try_fallback(
                    prompt,
                    duration_seconds=duration_seconds,
                    width=width,
                    height=height,
                    fps=fps,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    correlation_id=corr_id,
                    trace_id=trace_id,
                    generation_name=generation_name,
                    **kwargs,
                )
                if fallback is not None:
                    return fallback
            raise VideoGatewayError(f"Video generation failed: {exc}")

    async def generate_video_with_resource(
        self,
        prompt: str,
        *,
        duration_seconds: float = 8.0,
        width: int = 720,
        height: int = 1280,
        fps: int = 24,
        resolution: str | None = None,
        negative_prompt: str | None = None,
        seed: int | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "video_generation",
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        """Generate video while retaining a provider-side continuation resource."""
        return await self._resource_generation(
            "generate_video_with_resource",
            prompt,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            resolution=resolution,
            negative_prompt=negative_prompt,
            seed=seed,
            correlation_id=correlation_id,
            trace_id=trace_id,
            generation_name=generation_name,
            **kwargs,
        )

    async def extend_video(
        self,
        video_resource: Any,
        prompt: str,
        *,
        duration_seconds: float = 7.0,
        width: int = 720,
        height: int = 1280,
        fps: int = 24,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "video_extension",
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        """Extend a provider-side video resource without local re-upload."""
        return await self._resource_generation(
            "extend_video",
            prompt,
            method_args=(video_resource,),
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            correlation_id=correlation_id,
            trace_id=trace_id,
            generation_name=generation_name,
            extension=True,
            **kwargs,
        )

    async def _resource_generation(
        self,
        method_name: str,
        prompt: str,
        *,
        method_args: tuple[Any, ...] = (),
        duration_seconds: float,
        width: int,
        height: int,
        fps: int,
        negative_prompt: str | None = None,
        seed: int | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str,
        extension: bool = False,
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        self._ensure_initialized()
        corr_id = correlation_id or f"vid-{str(hash(prompt))[-8:]}"
        provider = self._get_primary_provider()
        method = getattr(provider, method_name, None)
        if method is None:
            raise VideoGatewayError(
                f"Provider '{provider.provider_name.value}' does not support {method_name}"
            )

        start = time.monotonic()
        start_dt = datetime.now(timezone.utc)
        call_kwargs: dict[str, Any] = {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration_seconds,
            **kwargs,
        }
        if not extension:
            call_kwargs.update(
                negative_prompt=negative_prompt,
                seed=seed,
            )
        try:
            payload = await self._call_with_retry(
                method,
                *method_args,
                prompt,
                **call_kwargs,
            )
            if not isinstance(payload, VideoGenerationPayload):
                raise VideoGatewayError(
                    f"Provider '{provider.provider_name.value}' returned an invalid resource payload"
                )
            latency_ms = int((time.monotonic() - start) * 1000)
            resolution = f"{width}x{height}"
            cost = (
                provider.calculate_extension_cost(duration_seconds)
                if extension
                else provider.calculate_cost(duration_seconds, resolution)
            )
            event = "video_extend_success" if extension else "video_generate_success"
            self._logger.info(
                event,
                correlation_id=corr_id,
                provider=provider.provider_name.value,
                duration_seconds=duration_seconds,
                resolution=resolution,
                cost_usd=cost,
                latency_ms=latency_ms,
                video_size_bytes=len(payload.video_bytes),
                remote_video_retained=payload.remote_video is not None,
            )
            if self._langfuse_client is not None:
                self._langfuse_client.generation(
                    trace_id=trace_id or corr_id,
                    name=generation_name,
                    provider=provider.provider_name.value,
                    model=self._provider_model(provider),
                    input_content=prompt,
                    output_content={
                        "video_bytes": len(payload.video_bytes),
                        "duration_seconds": duration_seconds,
                        "width": width,
                        "height": height,
                        "extension": extension,
                    },
                    cost_usd=cost,
                    start_time=start_dt,
                    end_time=datetime.now(timezone.utc),
                    metadata={
                        "correlation_id": corr_id,
                        "fps": fps,
                        "resolution": resolution,
                        "extension": extension,
                        "remote_video_retained": payload.remote_video is not None,
                    },
                )
            return GenerationResult(
                success=True,
                provider=provider.provider_name.value,
                model=self._provider_model(provider),
                output=payload.video_bytes,
                cost_usd=cost,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                metadata={
                    "duration_seconds": duration_seconds,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "resolution": resolution,
                    "extension": extension,
                    "remote_video": payload.remote_video,
                    "remote_video_retained": payload.remote_video is not None,
                },
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "video_extension_failed" if extension else "video_generate_failed",
                correlation_id=corr_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            raise VideoGatewayError(f"Video generation failed: {exc}")

    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate the USD cost for generating a video."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return provider.calculate_cost(duration_seconds, resolution)

    async def health_check(self) -> HealthStatus:
        """Check the health of the primary video provider."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return await provider.health_check()

    async def shutdown(self) -> None:
        self._initialized = False
        self._logger.info("video_gateway_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise VideoGatewayError("Video Gateway is not initialised")

    def _get_primary_provider(self) -> VideoProvider:
        providers = self._registry.get_providers_by_type(VideoProvider)
        if not providers:
            raise VideoGatewayError("No video providers registered")
        return providers[0]

    def _provider_model(self, provider: VideoProvider) -> str:
        return getattr(provider, "model_name", None) or self._config.veo.model

    async def _call_with_retry(self, func: Any, *args: Any, max_retries: int | None = None, **kwargs: Any) -> bytes:
        retries = max_retries or (self._config.veo.max_retries if self._config else 2)
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except (ProviderException, Exception) as exc:
                last_exc = exc
                if attempt < retries:
                    backoff = min(2**attempt, 60)
                    self._logger.warning(
                        "video_retry",
                        attempt=attempt,
                        max_retries=retries,
                        backoff_seconds=backoff,
                        error=str(exc),
                    )
                    await asyncio.sleep(backoff)
        raise last_exc  # type: ignore[misc]

    async def _try_fallback(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "video_generation",
        **kwargs: Any,
    ) -> GenerationResult[bytes] | None:
        providers = self._registry.get_providers_by_type(VideoProvider)
        failed: list[str] = []

        for provider in providers[1:]:
            try:
                self._logger.info(
                    "video_fallback_attempt",
                    provider=provider.provider_name.value,
                    correlation_id=correlation_id,
                )
                start = time.monotonic()
                start_dt = datetime.now(timezone.utc)
                video_bytes = await provider.generate_video(
                    prompt,
                    duration_seconds=duration_seconds,
                    width=width,
                    height=height,
                    fps=fps,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    **kwargs,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                resolution = f"{width}x{height}"
                cost = provider.calculate_cost(duration_seconds, resolution)

                # Langfuse trace for fallback provider
                if self._langfuse_client is not None:
                    self._langfuse_client.generation(
                        trace_id=trace_id or correlation_id or "",
                        name=f"{generation_name}_fallback",
                        provider=provider.provider_name.value,
                        model=self._provider_model(provider),
                        input_content=prompt,
                        output_content={
                            "video_bytes": len(video_bytes),
                            "duration_seconds": duration_seconds,
                            "width": width,
                            "height": height,
                        },
                        cost_usd=cost,
                        start_time=start_dt,
                        end_time=datetime.now(timezone.utc),
                        metadata={
                            "correlation_id": correlation_id,
                            "fallback": True,
                            "resolution": resolution,
                            "type": "video_generation",
                        },
                    )

                return GenerationResult(
                    success=True,
                    provider=provider.provider_name.value,
                    model=self._provider_model(provider),
                    output=video_bytes,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id or "",
                    metadata={"fallback": True, "duration_seconds": duration_seconds, "resolution": resolution},
                )
            except Exception as exc:
                failed.append(provider.provider_name.value)
                self._logger.warning(
                    "video_fallback_failed",
                    provider=provider.provider_name.value,
                    error=str(exc),
                )

        if failed:
            raise AllProvidersFailedError("video", [self._get_primary_provider().provider_name.value] + failed)
        return None
