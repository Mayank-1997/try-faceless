"""Gemini LLM provider — concrete implementation of ``LLMProvider``.

Wraps the Google Generative AI SDK (``google.generativeai``) behind the
common ``LLMProvider`` interface.  Agents and gateways never interact
with Gemini-specific APIs directly.

Supports:
- Text generation (``generate()``)
- JSON-structured generation (``generate_json()``)
- Streaming generation (``stream()``)
- Token counting (``count_tokens()``)
- Cost calculation (``calculate_cost()``)
- Health check (``health_check()``)

Future providers (OpenAI, Claude, etc.) will implement the same
interface, allowing zero-code-change provider switching.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from src.core.enums import AIProvider
from src.core.exceptions import (
    AIProviderError,
    AIProviderTimeoutError,
    ProviderNotInitializedError,
    ProviderResponseParsingError,
)
from src.core.interfaces import HealthStatus, LLMProvider, ProviderConfig
from src.core.logging import get_logger


class GeminiLLMProvider(LLMProvider):
    """Google Gemini implementation of the ``LLMProvider`` interface.

    Uses ``google.generativeai`` for API calls.  Supports both the Pro
    and Flash models, with per-model cost calculation.
    """

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._model: Any = None
        self._flash_model: Any = None
        self._logger = get_logger(__name__)
        self._initialized = False
        self._cost_input_per_1k: float = 0.00125
        self._cost_output_per_1k: float = 0.005
        self._flash_cost_input_per_1k: float = 0.0003
        self._flash_cost_output_per_1k: float = 0.0015

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.GEMINI

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the Gemini provider with API key and model configuration.

        Args:
            config: Provider configuration containing the API key, model
                name, and cost parameters.
        """
        import google.generativeai as genai

        self._config = config
        genai.configure(api_key=config.api_key)

        self._model = genai.GenerativeModel(config.model)
        flash_model_name = config.extra.get("flash_model", "gemini-2.5-flash")
        self._flash_model = genai.GenerativeModel(flash_model_name)

        self._cost_input_per_1k = config.extra.get("cost_input_per_1k", 0.00125)
        self._cost_output_per_1k = config.extra.get("cost_output_per_1k", 0.005)
        self._flash_cost_input_per_1k = config.extra.get("flash_cost_input_per_1k", 0.0003)
        self._flash_cost_output_per_1k = config.extra.get("flash_cost_output_per_1k", 0.0015)

        self._initialized = True
        self._logger.info(
            "gemini_provider_initialized",
            model=config.model,
            flash_model=flash_model_name,
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._model is None:
            raise ProviderNotInitializedError(self.provider_name.value)

    def _get_model(self, use_flash: bool = False) -> Any:
        """Return the appropriate model (Pro or Flash)."""
        self._ensure_initialized()
        return self._flash_model if use_flash else self._model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a text completion using Gemini.

        Args:
            prompt: The input prompt string.
            **kwargs: Additional options:
                - ``use_flash`` (bool): Use Flash model instead of Pro.
                - ``temperature`` (float): Sampling temperature.
                - ``max_output_tokens`` (int): Max tokens to generate.

        Returns:
            The generated text response.
        """
        self._ensure_initialized()
        use_flash = kwargs.pop("use_flash", False)
        model = self._get_model(use_flash)

        generation_config = {
            "temperature": kwargs.pop("temperature", 0.7),
            "max_output_tokens": kwargs.pop("max_output_tokens", 8192),
        }

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    prompt,
                    generation_config=generation_config,
                ),
                timeout=self._config.request_timeout if self._config else 120,
            )
            return response.text
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(
                self.provider_name.value,
                self._config.request_timeout if self._config else 120,
            )
        except Exception as exc:
            self._logger.error("gemini_generate_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    async def generate_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Generate a completion and parse it as JSON.

        Injects a system instruction to request JSON output, then
        parses the response.  Handles common LLM JSON formatting issues
        (markdown code fences, trailing commas).

        Args:
            prompt: The input prompt string.
            **kwargs: Same as ``generate()``.

        Returns:
            Parsed JSON dictionary.

        Raises:
            ProviderResponseParsingError: If the response cannot be parsed.
        """
        json_prompt = (
            f"{prompt}\n\n"
            "Respond with ONLY valid JSON. No markdown, no code fences, "
            "no explanations — just the JSON object."
        )
        raw = await self.generate(json_prompt, **kwargs)
        return self._parse_json_response(raw)

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream a completion chunk-by-chunk.

        Args:
            prompt: The input prompt string.
            **kwargs: Same as ``generate()``.

        Yields:
            Text chunks as they arrive from the API.
        """
        self._ensure_initialized()
        use_flash = kwargs.pop("use_flash", False)
        model = self._get_model(use_flash)

        generation_config = {
            "temperature": kwargs.pop("temperature", 0.7),
            "max_output_tokens": kwargs.pop("max_output_tokens", 8192),
        }

        try:
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config=generation_config,
                stream=True,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            self._logger.error("gemini_stream_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's token counter.

        Falls back to a heuristic estimate if the API is unavailable.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
        """
        self._ensure_initialized()
        try:
            result = self._model.count_tokens(text)
            return result.total_tokens
        except Exception:
            # Heuristic: ~4 characters per token for English text
            return max(1, len(text) // 4)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost based on per-1K-token rates.

        Uses the Pro model rates by default.  The gateway can pass
        Flash model rates when appropriate.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost in USD.
        """
        input_cost = (input_tokens / 1000) * self._cost_input_per_1k
        output_cost = (output_tokens / 1000) * self._cost_output_per_1k
        return round(input_cost + output_cost, 6)

    def calculate_flash_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost using Flash model rates (cheaper)."""
        input_cost = (input_tokens / 1000) * self._flash_cost_input_per_1k
        output_cost = (output_tokens / 1000) * self._flash_cost_output_per_1k
        return round(input_cost + output_cost, 6)

    async def health_check(self) -> HealthStatus:
        """Check if the Gemini API is reachable.

        Sends a minimal request and measures latency.
        """
        if not self._initialized:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name.value,
                details={"reason": "not initialized"},
            )
        try:
            import time

            start = time.monotonic()
            await asyncio.to_thread(
                self._model.generate_content,
                "Reply with: OK",
                generation_config={"max_output_tokens": 5},
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            return HealthStatus(
                healthy=True,
                provider=self.provider_name.value,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name.value,
                details={"error": str(exc)},
            )

    async def shutdown(self) -> None:
        """Release resources."""
        self._model = None
        self._flash_model = None
        self._initialized = False
        self._logger.info("gemini_provider_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, Any]:
        """Parse a JSON response from an LLM, handling common formatting issues.

        Args:
            raw: The raw text response from the LLM.

        Returns:
            Parsed JSON dictionary.

        Raises:
            ProviderResponseParsingError: If the text cannot be parsed as JSON.
        """
        text = raw.strip()

        # Remove markdown code fences
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

        # Remove trailing commas (common LLM JSON error)
        text = re.sub(r",\s*([}\]])", r"\1", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderResponseParsingError(
                "gemini",
                f"JSON decode error at line {exc.lineno} col {exc.colno}: {exc.msg}",
            )
