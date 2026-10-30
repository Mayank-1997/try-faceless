"""Image Gateway — unified interface for AI image generation.

Agents call the Image Gateway instead of provider-specific APIs. The
gateway handles provider selection, fallback, retries, cost calculation,
structured logging, and Langfuse tracing.

Architecture::

    Agent → ImageGateway → ProviderRegistry → ImagenProvider (or fallback)

Langfuse tracing:
    Each ``generate_image`` call is recorded as a Langfuse **generation**
    observation inside the supplied ``trace_id``.  This includes the
    prompt, provider, model, cost, latency, and image size — making
    image-generation costs visible alongside LLM costs in the Langfuse
    dashboard.
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
    ImageGatewayError,
    ProviderException,
)
from src.core.interfaces import HealthStatus, ImageProvider
from src.core.logging import get_logger


class ImageGateway:
    """Unified gateway for AI image generation operations."""

    def __init__(
        self,
        registry: Any,
        config: ConfigService,
        langfuse_client: Any = None,
    ) -> None:
        """Create the Image Gateway.

        Args:
            registry: The provider registry containing initialised providers.
            config: The application configuration service.
            langfuse_client: Optional Langfuse client for tracing image
                generation calls.  When ``None`` or disabled, tracing is
                silently skipped.
        """
        self._registry = registry
        self._config = config
        self._logger = get_logger(__name__)
        self._langfuse_client = langfuse_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialise the gateway."""
        self._initialized = True
        providers = self._registry.get_provider_names_by_type(ImageProvider)
        self._logger.info("image_gateway_initialized", providers=providers)

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1920,
        height: int = 1080,
        negative_prompt: str | None = None,
        seed: int | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "image_generation",
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        """Generate an image from a text prompt.

        Args:
            prompt: Text description of the desired image.
            width: Output width in pixels.
            height: Output height in pixels.
            negative_prompt: Elements to avoid.
            seed: Random seed for reproducibility.
            correlation_id: Optional correlation ID for tracing.
            trace_id: Optional Langfuse trace ID to attach the generation to.
            generation_name: Name for the Langfuse generation observation.
            **kwargs: Provider-specific options.

        Returns:
            ``GenerationResult`` containing raw image bytes, cost, and metadata.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"img-{str(hash(prompt))[-8:]}"

        provider = self._get_primary_provider()
        start = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        try:
            image_bytes = await self._call_with_retry(
                provider.generate_image,
                prompt,
                width=width,
                height=height,
                negative_prompt=negative_prompt,
                seed=seed,
                **kwargs,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            cost = provider.calculate_cost(width, height)
            model = self._config.imagen.model

            self._logger.info(
                "image_generate_success",
                correlation_id=corr_id,
                provider=provider.provider_name.value,
                width=width,
                height=height,
                cost_usd=cost,
                latency_ms=latency_ms,
                image_size_bytes=len(image_bytes),
            )

            # Langfuse trace — record as a generation observation
            if self._langfuse_client is not None:
                self._langfuse_client.generation(
                    trace_id=trace_id or corr_id,
                    name=generation_name,
                    provider=provider.provider_name.value,
                    model=model,
                    input_content=prompt,
                    output_content={
                        "image_bytes": len(image_bytes),
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
                        "image_size_bytes": len(image_bytes),
                        "type": "image_generation",
                    },
                )

            return GenerationResult(
                success=True,
                provider=provider.provider_name.value,
                model=model,
                output=image_bytes,
                cost_usd=cost,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                metadata={
                    "width": width,
                    "height": height,
                    "negative_prompt": negative_prompt,
                    "seed": seed,
                },
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "image_generate_failed",
                correlation_id=corr_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            if self._config.is_feature_enabled("provider_fallback"):
                fallback = await self._try_fallback(
                    prompt,
                    width=width,
                    height=height,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    correlation_id=corr_id,
                    trace_id=trace_id,
                    generation_name=generation_name,
                    **kwargs,
                )
                if fallback is not None:
                    return fallback
            raise ImageGatewayError(f"Image generation failed: {exc}")

    def calculate_cost(self, width: int, height: int) -> float:
        """Calculate the USD cost for generating an image at the given resolution."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return provider.calculate_cost(width, height)

    async def health_check(self) -> HealthStatus:
        """Check the health of the primary image provider."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return await provider.health_check()

    async def shutdown(self) -> None:
        """Release resources."""
        self._initialized = False
        self._logger.info("image_gateway_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise ImageGatewayError("Image Gateway is not initialised")

    def _get_primary_provider(self) -> ImageProvider:
        providers = self._registry.get_providers_by_type(ImageProvider)
        if not providers:
            raise ImageGatewayError("No image providers registered")
        return providers[0]

    async def _call_with_retry(self, func: Any, *args: Any, max_retries: int | None = None, **kwargs: Any) -> bytes:
        retries = max_retries or (self._config.imagen.max_retries if self._config else 3)
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except (ProviderException, Exception) as exc:
                last_exc = exc
                if attempt < retries:
                    backoff = min(2**attempt, 30)
                    self._logger.warning(
                        "image_retry",
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
        width: int = 1920,
        height: int = 1080,
        negative_prompt: str | None = None,
        seed: int | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "image_generation",
        **kwargs: Any,
    ) -> GenerationResult[bytes] | None:
        providers = self._registry.get_providers_by_type(ImageProvider)
        failed: list[str] = []

        for provider in providers[1:]:
            try:
                self._logger.info(
                    "image_fallback_attempt",
                    provider=provider.provider_name.value,
                    correlation_id=correlation_id,
                )
                start = time.monotonic()
                start_dt = datetime.now(timezone.utc)
                image_bytes = await provider.generate_image(
                    prompt,
                    width=width,
                    height=height,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    **kwargs,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                cost = provider.calculate_cost(width, height)
                model = self._config.imagen.model

                # Langfuse trace for fallback provider
                if self._langfuse_client is not None:
                    self._langfuse_client.generation(
                        trace_id=trace_id or correlation_id or "",
                        name=f"{generation_name}_fallback",
                        provider=provider.provider_name.value,
                        model=model,
                        input_content=prompt,
                        output_content={
                            "image_bytes": len(image_bytes),
                            "width": width,
                            "height": height,
                        },
                        cost_usd=cost,
                        start_time=start_dt,
                        end_time=datetime.now(timezone.utc),
                        metadata={
                            "correlation_id": correlation_id,
                            "fallback": True,
                            "image_size_bytes": len(image_bytes),
                            "type": "image_generation",
                        },
                    )

                return GenerationResult(
                    success=True,
                    provider=provider.provider_name.value,
                    model=model,
                    output=image_bytes,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id or "",
                    metadata={"fallback": True, "width": width, "height": height},
                )
            except Exception as exc:
                failed.append(provider.provider_name.value)
                self._logger.warning(
                    "image_fallback_failed",
                    provider=provider.provider_name.value,
                    error=str(exc),
                )

        if failed:
            raise AllProvidersFailedError("image", [self._get_primary_provider().provider_name.value] + failed)
        return None
