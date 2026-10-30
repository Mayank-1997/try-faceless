"""Imagen image generation provider — concrete implementation of ``ImageProvider``.

Wraps the Google Generative AI SDK (``google.generativeai``) image
generation models behind the common ``ImageProvider`` interface.

Uses the Gemini API image generation models (e.g.
``gemini-2.5-flash-image``) which are accessible with a standard
``GEMINI_API_KEY`` — no Vertex AI / GCP service-account required.

The provider accepts the ``GOOGLE_IMAGEN_API_KEY`` if set, but falls
back to the ``GEMINI_API_KEY`` (passed via ``extra["gemini_api_key"]``)
so image generation works out-of-the-box in environments that only have
the Gemini key configured.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from src.core.enums import AIProvider
from src.core.exceptions import (
    AIProviderError,
    AIProviderTimeoutError,
    ProviderNotInitializedError,
)
from src.core.interfaces import HealthStatus, ImageProvider, ProviderConfig
from src.core.logging import get_logger


class ImagenProvider(ImageProvider):
    """Google Imagen / Gemini image generation implementation of ``ImageProvider``.

    Uses ``google.generativeai`` with an image-capable model
    (default ``gemini-2.5-flash-image``) to generate images from text
    prompts.  The response parts contain ``inline_data`` with the raw
    image bytes (PNG).
    """

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._logger = get_logger(__name__)
        self._initialized = False
        self._cost_per_image: float = 0.04
        self._api_key: str = ""
        self._model_name: str = "gemini-2.5-flash-image"
        self._model: Any = None

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.IMAGEN

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the Imagen provider.

        Uses ``GOOGLE_IMAGEN_API_KEY`` if provided, otherwise falls back
        to the Gemini API key supplied via ``extra["gemini_api_key"]``.
        """
        self._config = config
        self._cost_per_image = config.extra.get("cost_per_image", 0.04)

        # Prefer the dedicated Imagen key; fall back to the Gemini key.
        self._api_key = config.api_key or config.extra.get("gemini_api_key", "")
        if not self._api_key:
            self._logger.warning(
                "imagen_provider_no_api_key",
                message="No GOOGLE_IMAGEN_API_KEY or GEMINI_API_KEY — provider disabled",
            )
            return  # stay uninitialised

        self._model_name = config.model or "gemini-2.5-flash-image"

        try:
            import google.generativeai as genai

            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self._model_name)
        except Exception as exc:
            self._logger.error("imagen_provider_init_failed", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

        self._initialized = True
        self._logger.info(
            "imagen_provider_initialized",
            model=self._model_name,
            cost_per_image=self._cost_per_image,
            using_gemini_key=not bool(config.api_key),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise ProviderNotInitializedError(self.provider_name.value)

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
        """Generate an image using Google Gemini image generation.

        The Gemini image models accept a text prompt via
        ``generate_content`` and return ``inline_data`` parts containing
        the raw image bytes (PNG).  The call is wrapped in
        ``asyncio.to_thread`` for async compatibility.
        """
        self._ensure_initialized()
        assert self._config is not None
        assert self._model is not None

        # Build a rich prompt that conveys aspect-ratio guidance.
        aspect = "landscape" if width >= height else "portrait"
        full_prompt = (
            f"{prompt}\n\n"
            f"Style: photorealistic, high detail, cinematic lighting. "
            f"Aspect ratio: {aspect} ({width}x{height})."
        )
        if negative_prompt:
            full_prompt += f"\nAvoid: {negative_prompt}"

        try:
            image_bytes = await asyncio.wait_for(
                asyncio.to_thread(self._generate_image_sync, full_prompt, seed),
                timeout=self._config.request_timeout,
            )
            return image_bytes
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(self.provider_name.value, self._config.request_timeout)
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("imagen_generate_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    def _generate_image_sync(self, prompt: str, seed: int | None) -> bytes:
        """Synchronous image generation via the Gemini API.

        Calls ``GenerativeModel.generate_content`` and extracts the
        ``inline_data`` bytes from the first candidate that contains
        image data.
        """
        generation_config: dict[str, Any] = {}
        if seed is not None:
            # Gemini image models may not honour seed, but we pass it anyway.
            generation_config["seed"] = seed

        response = self._model.generate_content(
            prompt,
            generation_config=generation_config or None,
        )

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", []) or []:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and inline_data.data:
                    # inline_data.data is already raw bytes
                    return inline_data.data  # type: ignore[no-any-return]

        raise AIProviderError(
            self.provider_name.value,
            "Image generation returned no inline_data — the model may have refused the prompt",
        )

    def calculate_cost(self, width: int, height: int) -> float:
        """Calculate cost based on per-image pricing."""
        return self._cost_per_image

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
        self._model = None
        self._logger.info("imagen_provider_shutdown")
