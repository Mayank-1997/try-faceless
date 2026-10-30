"""Langfuse client wrapper for LLM tracing and observability.

Provides a thin, conditional wrapper around the official ``langfuse``
Python SDK.  If credentials are not configured or the feature is
disabled, all calls are no-ops so the application runs unchanged.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.core.config_service import ConfigService
from src.core.logging import get_logger


class LangfuseClient:
    """Conditional Langfuse client for tracing LLM calls and agent runs."""

    def __init__(self, config: ConfigService) -> None:
        """Create the Langfuse client.

        Args:
            config: The central configuration service.
        """
        self._config = config
        self._logger = get_logger(__name__)
        self._client: Any = None
        self.enabled = self._should_enable()

        if self.enabled:
            try:
                from langfuse import Langfuse  # type: ignore[import-untyped]

                self._client = Langfuse(
                    public_key=config.langfuse.public_key,
                    secret_key=config.langfuse.secret_key,
                    host=config.langfuse.host,
                    release=config.langfuse.release or None,
                )
                self._logger.info(
                    "langfuse_client_initialized",
                    host=config.langfuse.host,
                    release=config.langfuse.release,
                )
            except Exception as exc:
                self._logger.error("langfuse_init_failed", error=str(exc))
                self.enabled = False

    def _should_enable(self) -> bool:
        """Check whether Langfuse is enabled and properly configured."""
        return bool(
            self._config.langfuse.enabled
            and self._config.langfuse.public_key
            and self._config.langfuse.secret_key
            and self._config.langfuse.host
        )

    def start_trace(
        self,
        *,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Start a new top-level trace and return its ID."""
        if not self.enabled or self._client is None:
            return None

        trace_id = str(uuid4())
        try:
            self._client.trace(
                id=trace_id,
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            return trace_id
        except Exception as exc:
            self._logger.error("langfuse_trace_failed", error=str(exc))
            return None

    def generation(
        self,
        *,
        trace_id: str,
        name: str,
        provider: str = "",
        model: str = "",
        input_content: Any = None,
        output_content: Any = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        input_cost: float = 0.0,
        output_cost: float = 0.0,
        cost_usd: float = 0.0,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an LLM generation observation inside a trace."""
        if not self.enabled or self._client is None:
            return

        start = start_time or datetime.now(timezone.utc)
        end = end_time or datetime.now(timezone.utc)
        meta: dict[str, Any] = {"cost_usd": cost_usd}
        if provider:
            meta["provider"] = provider
        if metadata:
            meta.update(metadata)

        total_cost = round(input_cost + output_cost, 6) or cost_usd
        try:
            trace = self._client.trace(id=trace_id)
            trace.generation(
                id=str(uuid4()),
                name=name,
                model=model,
                input=input_content,
                output=output_content,
                start_time=start,
                end_time=end,
                usage_details={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens,
                },
                cost_details={
                    "input": input_cost,
                    "output": output_cost,
                    "total": total_cost,
                },
                metadata=meta,
            )
        except Exception as exc:
            self._logger.error("langfuse_generation_failed", error=str(exc))

    def span(
        self,
        *,
        trace_id: str,
        name: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        input_content: Any = None,
        output_content: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """Record a span (e.g. a workflow step) inside an existing trace."""
        if not self.enabled or self._client is None:
            return None

        span_id = str(uuid4())
        try:
            trace = self._client.trace(id=trace_id)
            trace.span(
                id=span_id,
                name=name,
                input=input_content,
                output=output_content,
                start_time=start_time or datetime.now(timezone.utc),
                end_time=end_time or datetime.now(timezone.utc),
                metadata=metadata or {},
            )
            return span_id
        except Exception as exc:
            self._logger.error("langfuse_span_failed", error=str(exc))
            return None

    def update_trace(
        self,
        *,
        trace_id: str,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update an existing trace with output and metadata."""
        if not self.enabled or self._client is None:
            return

        try:
            trace = self._client.trace(id=trace_id)
            trace.update(output=output, metadata=metadata or {})
        except Exception as exc:
            self._logger.error("langfuse_update_trace_failed", error=str(exc))

    async def shutdown(self) -> None:
        """Flush pending Langfuse events on shutdown."""
        if not self.enabled or self._client is None:
            return

        try:
            await asyncio.to_thread(self._client.flush)
        except Exception as exc:
            self._logger.error("langfuse_flush_failed", error=str(exc))
