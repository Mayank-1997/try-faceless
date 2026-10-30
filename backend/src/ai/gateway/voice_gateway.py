"""Voice Gateway — unified interface for text-to-speech generation.

Agents call the Voice Gateway instead of provider-specific APIs. The
gateway handles provider selection, fallback, retries, cost calculation,
and structured logging.

Architecture::

    Agent → VoiceGateway → ProviderRegistry → GoogleTTSProvider (or fallback)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from src.application.dto.responses import GenerationResult
from src.core.config_service import ConfigService
from src.core.exceptions import (
    AllProvidersFailedError,
    ProviderException,
    VoiceGatewayError,
)
from src.core.interfaces import HealthStatus, VoiceProvider
from src.core.logging import get_logger


class VoiceGateway:
    """Unified gateway for text-to-speech operations."""

    def __init__(
        self,
        registry: Any,
        config: ConfigService,
    ) -> None:
        self._registry = registry
        self._config = config
        self._logger = get_logger(__name__)
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True
        providers = self._registry.get_provider_names_by_type(VoiceProvider)
        self._logger.info("voice_gateway_initialized", providers=providers)

    async def generate_speech(
        self,
        text: str,
        *,
        language: str = "en-US",
        voice_name: str | None = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        correlation_id: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult[bytes]:
        """Generate speech audio from text.

        Args:
            text: The text to synthesise.
            language: BCP-47 language code.
            voice_name: Specific voice identifier.
            speaking_rate: Speed multiplier (1.0 = normal).
            pitch: Pitch adjustment in semitones.
            correlation_id: Optional correlation ID for tracing.
            **kwargs: Provider-specific options.

        Returns:
            ``GenerationResult`` containing raw audio bytes, cost, and metadata.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"voice-{str(hash(text))[-8:]}"

        provider = self._get_primary_provider()
        start = time.monotonic()

        try:
            audio_bytes = await self._call_with_retry(
                provider.generate_speech,
                text,
                language=language,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
                pitch=pitch,
                **kwargs,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            char_count = len(text)
            cost = provider.calculate_cost(char_count)

            self._logger.info(
                "voice_generate_success",
                correlation_id=corr_id,
                provider=provider.provider_name.value,
                char_count=char_count,
                language=language,
                cost_usd=cost,
                latency_ms=latency_ms,
                audio_size_bytes=len(audio_bytes),
            )

            return GenerationResult(
                success=True,
                provider=provider.provider_name.value,
                model=self._config.tts.voice,
                output=audio_bytes,
                cost_usd=cost,
                latency_ms=latency_ms,
                correlation_id=corr_id,
                metadata={
                    "char_count": char_count,
                    "language": language,
                    "voice_name": voice_name,
                    "speaking_rate": speaking_rate,
                    "pitch": pitch,
                },
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "voice_generate_failed",
                correlation_id=corr_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            if self._config.is_feature_enabled("provider_fallback"):
                fallback = await self._try_fallback(
                    text,
                    language=language,
                    voice_name=voice_name,
                    speaking_rate=speaking_rate,
                    pitch=pitch,
                    correlation_id=corr_id,
                    **kwargs,
                )
                if fallback is not None:
                    return fallback
            raise VoiceGatewayError(f"Voice generation failed: {exc}")

    def calculate_cost(self, character_count: int) -> float:
        """Calculate the USD cost for generating speech."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return provider.calculate_cost(character_count)

    async def health_check(self) -> HealthStatus:
        """Check the health of the primary voice provider."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return await provider.health_check()

    async def shutdown(self) -> None:
        self._initialized = False
        self._logger.info("voice_gateway_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise VoiceGatewayError("Voice Gateway is not initialised")

    def _get_primary_provider(self) -> VoiceProvider:
        providers = self._registry.get_providers_by_type(VoiceProvider)
        if not providers:
            raise VoiceGatewayError("No voice providers registered")
        return providers[0]

    async def _call_with_retry(self, func: Any, *args: Any, max_retries: int | None = None, **kwargs: Any) -> bytes:
        retries = max_retries or (self._config.tts.max_retries if self._config else 3)
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except (ProviderException, Exception) as exc:
                last_exc = exc
                if attempt < retries:
                    backoff = min(2**attempt, 30)
                    self._logger.warning(
                        "voice_retry",
                        attempt=attempt,
                        max_retries=retries,
                        backoff_seconds=backoff,
                        error=str(exc),
                    )
                    await asyncio.sleep(backoff)
        raise last_exc  # type: ignore[misc]

    async def _try_fallback(
        self,
        text: str,
        *,
        language: str = "en-US",
        voice_name: str | None = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        correlation_id: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult[bytes] | None:
        providers = self._registry.get_providers_by_type(VoiceProvider)
        failed: list[str] = []

        for provider in providers[1:]:
            try:
                self._logger.info(
                    "voice_fallback_attempt",
                    provider=provider.provider_name.value,
                    correlation_id=correlation_id,
                )
                start = time.monotonic()
                audio_bytes = await provider.generate_speech(
                    text,
                    language=language,
                    voice_name=voice_name,
                    speaking_rate=speaking_rate,
                    pitch=pitch,
                    **kwargs,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                char_count = len(text)
                cost = provider.calculate_cost(char_count)

                return GenerationResult(
                    success=True,
                    provider=provider.provider_name.value,
                    model=self._config.tts.voice,
                    output=audio_bytes,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id or "",
                    metadata={"fallback": True, "char_count": char_count, "language": language},
                )
            except Exception as exc:
                failed.append(provider.provider_name.value)
                self._logger.warning(
                    "voice_fallback_failed",
                    provider=provider.provider_name.value,
                    error=str(exc),
                )

        if failed:
            raise AllProvidersFailedError("voice", [self._get_primary_provider().provider_name.value] + failed)
        return None
