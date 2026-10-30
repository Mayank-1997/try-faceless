"""Edge TTS voice provider — free text-to-speech via Microsoft Edge.

Uses the ``edge-tts`` package which calls Microsoft Edge's public TTS
service.  No API key required, no cost per character.  This is the
default fallback when Google TTS is not configured.
"""

from __future__ import annotations

import asyncio
from typing import Any

import edge_tts

from src.core.enums import AIProvider
from src.core.exceptions import AIProviderError, AIProviderTimeoutError
from src.core.interfaces import HealthStatus, ProviderConfig, VoiceProvider
from src.core.logging import get_logger


class EdgeTTSProvider(VoiceProvider):
    """Free Microsoft Edge TTS implementation of ``VoiceProvider``."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._logger = get_logger(__name__)
        self._initialized = False
        self._voice: str = "en-US-ChristopherNeural"
        self._language: str = "en-US"

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.EDGE_TTS

    async def initialize(self, config: ProviderConfig) -> None:
        self._config = config
        self._voice = config.model or "en-US-ChristopherNeural"
        self._language = config.extra.get("language", "en-US")
        self._initialized = True
        self._logger.info(
            "edge_tts_provider_initialized",
            voice=self._voice,
            language=self._language,
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise AIProviderError(self.provider_name.value, "not initialized")

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
        """Generate speech audio (MP3 bytes) via Edge TTS."""
        self._ensure_initialized()
        voice = voice_name or self._voice

        # edge-tts expects rate as "+0%", "-20%", etc.
        rate_pct = int((speaking_rate - 1.0) * 100)
        rate_str = f"{rate_pct:+d}%"
        pitch_str = f"{int(pitch):+d}Hz"

        try:
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate_str,
                pitch=pitch_str,
            )
            audio = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
            if not audio:
                raise AIProviderError(
                    self.provider_name.value, "empty audio response"
                )
            return bytes(audio)
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(
                self.provider_name.value,
                self._config.request_timeout if self._config else 60,
            )
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("edge_tts_generate_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    def calculate_cost(self, character_count: int) -> float:
        """Edge TTS is free."""
        return 0.0

    async def health_check(self) -> HealthStatus:
        return HealthStatus(
            healthy=self._initialized,
            provider=self.provider_name.value,
            details={"voice": self._voice, "language": self._language},
        )

    async def shutdown(self) -> None:
        self._initialized = False
        self._logger.info("edge_tts_provider_shutdown")
