"""Provider registry — central registry for all AI provider implementations.

The registry maps ``AIProvider`` enum values to concrete provider
instances.  Gateways query the registry to obtain providers by name
or by capability.

Design:
- Providers are registered at startup via ``register()``.
- The registry holds **instances**, not classes — providers are
  initialised before registration.
- ``get_provider()`` returns a provider by enum value.
- ``get_providers_by_type()`` returns all providers of a given
  interface type (e.g. all ``LLMProvider`` instances).
- Provider order within a type defines the fallback chain.

Extensibility:
- Adding a new provider requires only:
  1. Implementing the appropriate interface.
  2. Registering it in ``initialize()``.
- No gateway or agent code needs to change.
"""

from __future__ import annotations

from typing import Any

from src.core.config_service import ConfigService
from src.core.enums import AIProvider
from src.core.exceptions import (
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
)
from src.core.interfaces import (
    ImageProvider,
    LLMProvider,
    VideoProvider,
    VoiceProvider,
)
from src.core.logging import get_logger


class ProviderRegistry:
    """Central registry for AI provider instances.

    Holds initialised provider instances keyed by ``AIProvider`` enum
    values.  Provides type-filtered lookups for gateways.
    """

    def __init__(self, config: ConfigService) -> None:
        """Create the registry.

        Args:
            config: The application configuration service.
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._providers: dict[AIProvider, Any] = {}

    async def initialize(self) -> None:
        """Register all configured providers.

        Only providers with valid API keys are registered.  This allows
        the system to run with partial provider configuration (e.g.
        Gemini only, no Veo).
        """
        await self._register_llm_providers()
        await self._register_image_providers()   # Imagen registered FIRST (primary)
        await self._register_video_providers()   # Veo registered FIRST (primary)
        await self._register_stock_providers()  # Stock registered LAST (fallback)
        await self._register_voice_providers()

        self._logger.info(
            "provider_registry_initialized",
            providers=[p.value for p in self._providers.keys()],
        )

    def register(self, provider_enum: AIProvider, instance: Any) -> None:
        """Register a provider instance.

        Args:
            provider_enum: The ``AIProvider`` enum value.
            instance: The initialised provider instance.

        Raises:
            ProviderAlreadyRegisteredError: If the provider is already registered.
        """
        if provider_enum in self._providers:
            raise ProviderAlreadyRegisteredError(provider_enum.value)
        self._providers[provider_enum] = instance
        self._logger.info("provider_registered", provider=provider_enum.value)

    def unregister(self, provider_enum: AIProvider) -> None:
        """Remove a provider from the registry.

        Args:
            provider_enum: The ``AIProvider`` enum value.

        Raises:
            ProviderNotRegisteredError: If the provider is not registered.
        """
        if provider_enum not in self._providers:
            raise ProviderNotRegisteredError(provider_enum.value)
        del self._providers[provider_enum]
        self._logger.info("provider_unregistered", provider=provider_enum.value)

    def get_provider(self, provider_enum: AIProvider) -> Any:
        """Get a provider by enum value.

        Args:
            provider_enum: The ``AIProvider`` enum value.

        Returns:
            The provider instance.

        Raises:
            ProviderNotRegisteredError: If the provider is not registered.
        """
        if provider_enum not in self._providers:
            raise ProviderNotRegisteredError(provider_enum.value)
        return self._providers[provider_enum]

    def get_providers_by_type(self, interface_type: type) -> list[Any]:
        """Get all registered providers that implement a given interface.

        Providers are returned in registration order, which defines the
        fallback chain.

        Args:
            interface_type: The abstract interface class (e.g. ``LLMProvider``).

        Returns:
            List of provider instances implementing the interface.
        """
        return [
            provider
            for provider in self._providers.values()
            if isinstance(provider, interface_type)
        ]

    def get_provider_names_by_type(self, interface_type: type) -> list[str]:
        """Get the names of all providers of a given type.

        Args:
            interface_type: The abstract interface class.

        Returns:
            List of provider enum string values.
        """
        return [
            enum_val.value
            for enum_val, provider in self._providers.items()
            if isinstance(provider, interface_type)
        ]

    def has_provider(self, provider_enum: AIProvider) -> bool:
        """Check if a provider is registered.

        Args:
            provider_enum: The ``AIProvider`` enum value.

        Returns:
            ``True`` if the provider is registered.
        """
        return provider_enum in self._providers

    def list_all(self) -> dict[str, str]:
        """List all registered providers and their type names.

        Returns:
            Dictionary mapping provider names to their interface type name.
        """
        return {
            enum_val.value: type(provider).__name__
            for enum_val, provider in self._providers.items()
        }

    async def shutdown(self) -> None:
        """Shut down all registered providers."""
        for enum_val, provider in list(self._providers.items()):
            if hasattr(provider, "shutdown"):
                try:
                    await provider.shutdown()
                except Exception as exc:
                    self._logger.error(
                        "provider_shutdown_error",
                        provider=enum_val.value,
                        error=str(exc),
                    )
        self._providers.clear()
        self._logger.info("provider_registry_shutdown")

    # -----------------------------------------------------------------------
    # Private registration helpers
    # -----------------------------------------------------------------------
    async def _register_llm_providers(self) -> None:
        """Register LLM providers with valid API keys."""
        gemini_config = self._config.gemini
        if gemini_config.api_key:
            from src.ai.providers.gemini import GeminiLLMProvider

            provider = GeminiLLMProvider()
            from src.core.interfaces import ProviderConfig

            await provider.initialize(
                ProviderConfig(
                    api_key=gemini_config.api_key,
                    model=gemini_config.pro_model,
                    max_retries=gemini_config.max_retries,
                    request_timeout=gemini_config.request_timeout,
                    extra={
                        "flash_model": gemini_config.flash_model,
                        "cost_input_per_1k": self._config.cost.gemini_pro_input_per_1k,
                        "cost_output_per_1k": self._config.cost.gemini_pro_output_per_1k,
                        "flash_cost_input_per_1k": self._config.cost.gemini_flash_input_per_1k,
                        "flash_cost_output_per_1k": self._config.cost.gemini_flash_output_per_1k,
                    },
                )
            )
            self.register(AIProvider.GEMINI, provider)
        else:
            self._logger.warning("gemini_api_key_missing")

    async def _register_image_providers(self) -> None:
        """Register image generation providers with valid API keys.

        The Imagen provider is registered when either
        ``GOOGLE_IMAGEN_API_KEY`` or ``GEMINI_API_KEY`` is set — the
        Gemini key is sufficient because the image generation models
        (e.g. ``gemini-2.5-flash-image``) use the same API.
        """
        imagen_config = self._config.imagen
        gemini_config = self._config.gemini
        # Prefer the dedicated Imagen key; fall back to the Gemini key.
        imagen_api_key = imagen_config.api_key or gemini_config.api_key
        if imagen_api_key:
            from src.ai.providers.imagen import ImagenProvider

            provider = ImagenProvider()
            from src.core.interfaces import ProviderConfig

            await provider.initialize(
                ProviderConfig(
                    api_key=imagen_config.api_key,
                    model=imagen_config.model,
                    max_retries=imagen_config.max_retries,
                    request_timeout=imagen_config.request_timeout,
                    extra={
                        "cost_per_image": self._config.cost.imagen_per_image,
                        "gemini_api_key": gemini_config.api_key,
                    },
                )
            )
            self.register(AIProvider.IMAGEN, provider)
        else:
            self._logger.warning("imagen_api_key_missing")

    async def _register_video_providers(self) -> None:
        """Register video generation providers with valid API keys.

        Kling (fal.ai) is registered FIRST when ``USE_KLING`` is enabled and
        ``FAL_KEY`` is set, making it the primary video provider.

        Veo is registered when ``USE_VEO`` is enabled and either
        ``GOOGLE_VEO_API_KEY`` or ``GEMINI_API_KEY`` is set — the Gemini
        API serves Veo models under the same key, mirroring the Imagen
        fallback behaviour.  When both are enabled, Kling is primary and
        Veo acts as the fallback.
        """
        from src.core.interfaces import ProviderConfig

        kling_config = self._config.kling
        if kling_config.enabled and kling_config.api_key:
            from src.ai.providers.kling import KlingProvider

            provider = KlingProvider()
            await provider.initialize(
                ProviderConfig(
                    api_key=kling_config.api_key,
                    model=kling_config.model,
                    max_retries=kling_config.max_retries,
                    request_timeout=kling_config.request_timeout,
                    extra={
                        "endpoint": kling_config.endpoint,
                        "cost_per_second": self._config.cost.kling_per_second,
                        "generate_audio": kling_config.generate_audio,
                    },
                )
            )
            self.register(AIProvider.KLING, provider)
        elif kling_config.enabled:
            self._logger.warning("kling_enabled_but_no_fal_key")

        veo_config = self._config.veo
        veo_api_key = veo_config.api_key or self._config.gemini.api_key
        if veo_config.enabled and veo_api_key:
            from src.ai.providers.veo import VeoProvider

            provider = VeoProvider()
            await provider.initialize(
                ProviderConfig(
                    api_key=veo_config.api_key,
                    model=veo_config.model,
                    max_retries=veo_config.max_retries,
                    request_timeout=veo_config.request_timeout,
                    extra={
                        "cost_per_second": self._config.cost.veo_per_second,
                        "gemini_api_key": self._config.gemini.api_key,
                    },
                )
            )
            self.register(AIProvider.VEO, provider)
        elif veo_config.enabled:
            self._logger.warning("veo_enabled_but_no_api_key")
        else:
            self._logger.info("veo_provider_disabled")

    async def _register_stock_providers(self) -> None:
        """Register free stock image / video providers if any API key is set."""
        stock_config = self._config.stock
        if stock_config.pexels_api_key or stock_config.pixabay_api_key or stock_config.unsplash_api_key:
            from src.ai.providers.stock import StockImageProvider, StockVideoProvider
            from src.core.interfaces import ProviderConfig

            extra = {
                "pexels_api_key": stock_config.pexels_api_key,
                "pixabay_api_key": stock_config.pixabay_api_key,
                "unsplash_api_key": stock_config.unsplash_api_key,
                "max_results": stock_config.max_results,
                "request_timeout": stock_config.request_timeout,
            }

            image_provider = StockImageProvider()
            await image_provider.initialize(
                ProviderConfig(
                    api_key="",
                    model="",
                    max_retries=2,
                    request_timeout=stock_config.request_timeout,
                    extra=extra,
                )
            )
            self.register(AIProvider.STOCK_IMAGE, image_provider)

            video_provider = StockVideoProvider()
            await video_provider.initialize(
                ProviderConfig(
                    api_key="",
                    model="",
                    max_retries=2,
                    request_timeout=stock_config.request_timeout,
                    extra=extra,
                )
            )
            self.register(AIProvider.STOCK_VIDEO, video_provider)

    async def _register_voice_providers(self) -> None:
        """Register voice/TTS providers. Falls back to free Edge TTS."""
        from src.core.interfaces import ProviderConfig

        edge_provider = None
        try:
            from src.ai.providers.edge_tts_provider import EdgeTTSProvider

            edge_provider = EdgeTTSProvider()
            tts_config = self._config.tts
            await edge_provider.initialize(
                ProviderConfig(
                    api_key="",
                    model=tts_config.voice.replace("en-US-Studio-Q", "en-US-ChristopherNeural")
                    if tts_config.voice
                    else "en-US-ChristopherNeural",
                    max_retries=tts_config.max_retries,
                    request_timeout=tts_config.request_timeout,
                    extra={"language": tts_config.language},
                )
            )
        except Exception as exc:
            self._logger.warning("edge_tts_registration_failed", error=str(exc))

        if edge_provider is not None:
            self.register(AIProvider.EDGE_TTS, edge_provider)
            self._logger.info("edge_tts_provider_registered", provider="edge_tts")

        tts_config = self._config.tts
        if tts_config.api_key:
            from src.ai.providers.google_tts import GoogleTTSProvider

            provider = GoogleTTSProvider()
            await provider.initialize(
                ProviderConfig(
                    api_key=tts_config.api_key,
                    model=tts_config.voice,
                    max_retries=tts_config.max_retries,
                    request_timeout=tts_config.request_timeout,
                    extra={
                        "language": tts_config.language,
                        "cost_per_1k_chars": self._config.cost.tts_per_1k_chars,
                    },
                )
            )
            self.register(AIProvider.GOOGLE_TTS, provider)
        else:
            self._logger.info(
                "google_tts_api_key_missing_using_edge_tts_fallback"
            )
