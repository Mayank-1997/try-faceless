"""LLM Gateway — unified interface for all LLM operations.

Agents call the LLM Gateway instead of provider-specific APIs.  The
gateway handles:

- **Provider selection**: chooses the best provider based on config.
- **Fallback**: if the primary provider fails, tries the next.
- **Retries**: exponential backoff on transient failures.
- **Streaming**: async iterator interface for streaming completions.
- **Token counting**: delegates to the active provider.
- **Cost calculation**: delegates to the active provider's cost model.
- **Caching**: optional response caching for identical prompts.
- **Structured logging**: every request is logged with correlation ID.
- **JSON validation**: parses and validates JSON responses.
- **Rate limiting**: ready for future rate-limit integration.

Architecture::

    Agent → LLMGateway → ProviderRegistry → GeminiProvider (or fallback)

The agent never knows which provider was used.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from src.application.dto.responses import GenerationResult, StreamingChunk
from src.core.config_service import ConfigService
from src.core.enums import AIProvider
from src.core.exceptions import (
    AllProvidersFailedError,
    LLMGatewayError,
    ProviderException,
)
from src.core.interfaces import HealthStatus, LLMProvider
from src.core.logging import get_logger
from src.infrastructure.observability.langfuse_client import LangfuseClient


class LLMGateway:
    """Unified gateway for Large Language Model operations.

    Wraps the provider registry and adds retry, fallback, caching,
    and observability logic.  Agents interact only with this gateway.
    """

    def __init__(
        self,
        registry: Any,
        config: ConfigService,
        langfuse_client: LangfuseClient | None = None,
    ) -> None:
        """Create the LLM Gateway.

        Args:
            registry: The provider registry containing initialised providers.
            config: The application configuration service.
            langfuse_client: Optional Langfuse client for tracing.
        """
        self._registry = registry
        self._config = config
        self._logger = get_logger(__name__)
        self._cache: dict[str, str] = {}
        self._langfuse_client = langfuse_client
        self._initialized = False

    async def initialize(self) -> None:
        """Initialise the gateway.  No heavy work — providers are already ready."""
        self._initialized = True
        providers = self._registry.get_provider_names_by_type(LLMProvider)
        self._logger.info("llm_gateway_initialized", providers=providers)

    async def generate(
        self,
        prompt: str,
        *,
        use_flash: bool = False,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        generation_name: str = "generate",
        **kwargs: Any,
    ) -> GenerationResult[str]:
        """Generate a text completion.

        Args:
            prompt: The input prompt string.
            use_flash: If ``True``, prefer the Flash (cheaper) model.
            temperature: Sampling temperature (0.0–1.0).
            max_output_tokens: Maximum tokens to generate.
            correlation_id: Optional correlation ID for tracing.
            **kwargs: Additional provider-specific options.

        Returns:
            ``GenerationResult`` containing the generated text, cost,
            token usage, and metadata.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"llm-{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
        trace_id = trace_id or corr_id

        # Check cache (if enabled)
        cache_key = self._cache_key(prompt, use_flash, temperature, max_output_tokens)
        if self._config.is_feature_enabled("prompt_caching") and cache_key in self._cache:
            self._logger.info("llm_cache_hit", correlation_id=corr_id)
            return GenerationResult(
                success=True,
                provider="cached",
                model="cached",
                output=self._cache[cache_key],
                correlation_id=corr_id,
                metadata={"cached": True},
            )

        provider = self._get_primary_provider()
        start = time.monotonic()
        start_dt = datetime.now(timezone.utc)

        try:
            text = await self._call_with_retry(
                provider.generate,
                prompt,
                use_flash=use_flash,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            # Estimate tokens (provider's count_tokens may not be perfectly accurate)
            input_tokens = provider.count_tokens(prompt)
            output_tokens = provider.count_tokens(text)
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            if use_flash and hasattr(provider, "calculate_flash_cost"):
                cost = provider.calculate_flash_cost(input_tokens, output_tokens)
                input_cost = provider.calculate_flash_cost(input_tokens, 0)
                output_cost = provider.calculate_flash_cost(0, output_tokens)
            else:
                cost = provider.calculate_cost(input_tokens, output_tokens)
                input_cost = provider.calculate_cost(input_tokens, 0)
                output_cost = provider.calculate_cost(0, output_tokens)

            model = self._config.gemini.flash_model if use_flash else self._config.gemini.pro_model

            # Cache the result
            if self._config.is_feature_enabled("prompt_caching"):
                self._cache[cache_key] = text

            self._logger.info(
                "llm_generate_success",
                correlation_id=corr_id,
                provider=provider.provider_name.value,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )

            if self._langfuse_client is not None:
                self._langfuse_client.generation(
                    trace_id=trace_id,
                    name=generation_name,
                    provider=provider.provider_name.value,
                    model=model,
                    input_content=prompt,
                    output_content=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                    cost_usd=cost,
                    start_time=start_dt,
                    end_time=datetime.now(timezone.utc),
                    metadata={"correlation_id": corr_id, "cached": False},
                )

            return GenerationResult(
                success=True,
                provider=provider.provider_name.value,
                model=model,
                output=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                correlation_id=corr_id,
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            self._logger.error(
                "llm_generate_failed",
                correlation_id=corr_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            # Try fallback providers
            if self._config.is_feature_enabled("provider_fallback"):
                fallback_result = await self._try_fallback(
                    prompt,
                    use_flash=use_flash,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    trace_id=trace_id,
                    correlation_id=corr_id,
                    **kwargs,
                )
                if fallback_result is not None:
                    return fallback_result

            raise LLMGatewayError(f"LLM generation failed: {exc}")

    async def generate_json(
        self,
        prompt: str,
        *,
        use_flash: bool = False,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult[dict[str, Any]]:
        """Generate a completion and parse it as JSON.

        Args:
            prompt: The input prompt string.
            use_flash: If ``True``, prefer the Flash model.
            temperature: Sampling temperature.
            max_output_tokens: Maximum tokens to generate.
            correlation_id: Optional correlation ID for tracing.
            **kwargs: Additional provider-specific options.

        Returns:
            ``GenerationResult`` containing the parsed JSON dictionary.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"llm-json-{hashlib.md5(prompt.encode()).hexdigest()[:8]}"

        text_result = await self.generate(
            prompt,
            use_flash=use_flash,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            correlation_id=corr_id,
            trace_id=trace_id,
            **kwargs,
        )

        # Parse JSON from the generated text
        provider = self._get_primary_provider()
        parsed = provider._parse_json_response(text_result.output)

        return GenerationResult(
            success=True,
            provider=text_result.provider,
            model=text_result.model,
            output=parsed,
            input_tokens=text_result.input_tokens,
            output_tokens=text_result.output_tokens,
            total_tokens=text_result.total_tokens,
            cost_usd=text_result.cost_usd,
            latency_ms=text_result.latency_ms,
            correlation_id=corr_id,
        )

    async def stream(
        self,
        prompt: str,
        *,
        use_flash: bool = False,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        correlation_id: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamingChunk]:
        """Stream a completion chunk-by-chunk.

        Args:
            prompt: The input prompt string.
            use_flash: If ``True``, prefer the Flash model.
            temperature: Sampling temperature.
            max_output_tokens: Maximum tokens to generate.
            correlation_id: Optional correlation ID for tracing.
            **kwargs: Additional provider-specific options.

        Yields:
            ``StreamingChunk`` objects as text arrives.
        """
        self._ensure_initialized()
        corr_id = correlation_id or f"llm-stream-{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
        provider = self._get_primary_provider()
        chunk_index = 0

        try:
            async for text_chunk in provider.stream(
                prompt,
                use_flash=use_flash,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                **kwargs,
            ):
                yield StreamingChunk(
                    chunk=text_chunk,
                    chunk_index=chunk_index,
                    is_final=False,
                    correlation_id=corr_id,
                )
                chunk_index += 1

            # Send final chunk
            yield StreamingChunk(
                chunk="",
                chunk_index=chunk_index,
                is_final=True,
                correlation_id=corr_id,
            )

        except Exception as exc:
            self._logger.error(
                "llm_stream_failed",
                correlation_id=corr_id,
                error=str(exc),
            )
            raise LLMGatewayError(f"LLM streaming failed: {exc}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in the given text using the primary provider.

        Args:
            text: The text to count tokens for.

        Returns:
            Estimated token count.
        """
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return provider.count_tokens(text)

    def calculate_cost(self, input_tokens: int, output_tokens: int, *, use_flash: bool = False) -> float:
        """Calculate the USD cost for a request.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            use_flash: If ``True``, use Flash model pricing.

        Returns:
            Cost in USD.
        """
        self._ensure_initialized()
        provider = self._get_primary_provider()
        if use_flash and hasattr(provider, "calculate_flash_cost"):
            return provider.calculate_flash_cost(input_tokens, output_tokens)
        return provider.calculate_cost(input_tokens, output_tokens)

    async def health_check(self) -> HealthStatus:
        """Check the health of the primary LLM provider."""
        self._ensure_initialized()
        provider = self._get_primary_provider()
        return await provider.health_check()

    async def shutdown(self) -> None:
        """Release resources."""
        self._cache.clear()
        self._initialized = False
        self._logger.info("llm_gateway_shutdown")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise LLMGatewayError("LLM Gateway is not initialised")

    def _get_primary_provider(self) -> LLMProvider:
        """Get the primary LLM provider from the registry."""
        providers = self._registry.get_providers_by_type(LLMProvider)
        if not providers:
            raise LLMGatewayError("No LLM providers registered")
        return providers[0]

    async def _call_with_retry(
        self,
        func: Any,
        *args: Any,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Call a provider function with exponential backoff retries.

        Args:
            func: The async function to call.
            *args: Positional arguments.
            max_retries: Override max retries. Defaults to provider config.
            **kwargs: Keyword arguments.

        Returns:
            The function's return value.

        Raises:
            The last exception if all retries fail.
        """
        retries = max_retries or (self._config.gemini.max_retries if self._config else 3)
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except (ProviderException, Exception) as exc:
                last_exc = exc
                if attempt < retries:
                    backoff = min(2**attempt, 30)
                    self._logger.warning(
                        "llm_retry",
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
        use_flash: bool = False,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        **kwargs: Any,
    ) -> GenerationResult[str] | None:
        """Try fallback providers after the primary fails.

        Args:
            prompt: The input prompt.
            use_flash: Prefer Flash model.
            temperature: Sampling temperature.
            max_output_tokens: Max tokens.
            correlation_id: Correlation ID.
            **kwargs: Additional options.

        Returns:
            ``GenerationResult`` if a fallback succeeds, ``None`` otherwise.
        """
        providers = self._registry.get_providers_by_type(LLMProvider)
        failed: list[str] = []

        for provider in providers[1:]:  # Skip primary (already failed)
            try:
                self._logger.info(
                    "llm_fallback_attempt",
                    provider=provider.provider_name.value,
                    correlation_id=correlation_id,
                )
                start = time.monotonic()
                start_dt = datetime.now(timezone.utc)
                text = await provider.generate(
                    prompt,
                    use_flash=use_flash,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    **kwargs,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                input_tokens = provider.count_tokens(prompt)
                output_tokens = provider.count_tokens(text)
                cost = provider.calculate_cost(input_tokens, output_tokens)
                input_cost = provider.calculate_cost(input_tokens, 0)
                output_cost = provider.calculate_cost(0, output_tokens)

                if self._langfuse_client is not None:
                    self._langfuse_client.generation(
                        trace_id=trace_id or correlation_id or "",
                        name="fallback-generate",
                        provider=provider.provider_name.value,
                        model=self._config.gemini.pro_model,
                        input_content=prompt,
                        output_content=text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                        input_cost=input_cost,
                        output_cost=output_cost,
                        cost_usd=cost,
                        start_time=start_dt,
                        end_time=datetime.now(timezone.utc),
                        metadata={"correlation_id": correlation_id, "fallback": True},
                    )

                return GenerationResult(
                    success=True,
                    provider=provider.provider_name.value,
                    model=self._config.gemini.pro_model,
                    output=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=input_tokens + output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    correlation_id=correlation_id or "",
                    metadata={"fallback": True},
                )
            except Exception as exc:
                failed.append(provider.provider_name.value)
                self._logger.warning(
                    "llm_fallback_failed",
                    provider=provider.provider_name.value,
                    error=str(exc),
                )

        if failed:
            raise AllProvidersFailedError("llm", [self._get_primary_provider().provider_name.value] + failed)
        return None

    @staticmethod
    def _cache_key(prompt: str, use_flash: bool, temperature: float, max_tokens: int) -> str:
        """Generate a cache key from prompt and generation parameters."""
        key_str = f"{prompt}|{use_flash}|{temperature}|{max_tokens}"
        return hashlib.sha256(key_str.encode()).hexdigest()
