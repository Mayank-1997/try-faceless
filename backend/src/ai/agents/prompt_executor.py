"""Prompt executor for the AI Agent Framework.

Handles the complete prompt execution pipeline:

1. **Prompt rendering** — Load template, inject variables, validate
2. **Provider selection** — Choose LLM provider via gateway
3. **AI execution** — Call LLM gateway (never providers directly)
4. **Response parsing** — Parse JSON if structured output expected
5. **Execution logging** — Log prompt, response, cost, tokens, latency
6. **Prompt history** — Track prompt executions for audit
7. **Metrics** — Record execution metrics

The ``PromptExecutor`` is the single entry point for all AI calls
made by agents.  It wraps the existing ``LLMGateway`` and
``PromptManager`` with agent-specific concerns.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.ai.agents.exceptions import PromptExecutionError
from src.ai.agents.output_validator import _clean_json_output
from src.ai.agents.prompt_template import PromptTemplate
from src.ai.agents.response import AIResponse
from src.core.logging import get_logger
from src.infrastructure.observability.langfuse_client import LangfuseClient


# ---------------------------------------------------------------------------
# Execution record
# ---------------------------------------------------------------------------
class PromptExecutionRecord(BaseModel):
    """Record of a single prompt execution.

    Attributes:
        execution_id: Unique ID for this prompt execution.
        agent_name: The agent that executed the prompt.
        template_name: The prompt template name.
        template_version: The prompt template version.
        rendered_prompt: The fully rendered prompt (may be truncated for logging).
        response: The AI response text.
        success: Whether the execution succeeded.
        provider: The AI provider used.
        model: The model used.
        cost_usd: Cost of the execution.
        input_tokens: Input tokens consumed.
        output_tokens: Output tokens generated.
        latency_ms: Response latency in milliseconds.
        error: Error message if failed.
        timestamp: When the execution occurred.
    """

    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str = ""
    template_name: str = ""
    template_version: str = ""
    rendered_prompt: str = ""
    response: str = ""
    success: bool = True
    provider: str = ""
    model: str = ""
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Execution options
# ---------------------------------------------------------------------------
class PromptExecutionOptions(BaseModel):
    """Options for a single prompt execution.

    Attributes:
        temperature: Sampling temperature (0.0–1.0).
        max_output_tokens: Maximum tokens to generate.
        use_flash: Prefer the Flash (cheaper) model.
        expect_json: Whether the response is expected to be JSON.
        json_schema: Optional JSON schema for validation.
        correlation_id: Optional correlation ID for tracing.
        trace_id: Optional parent (workflow) Langfuse trace ID.  When set,
            the generation is attached to that trace instead of starting a
            new standalone trace per prompt execution.
    """

    temperature: float = 0.7
    max_output_tokens: int = 8192
    use_flash: bool = False
    expect_json: bool = False
    json_schema: dict[str, Any] | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


# ---------------------------------------------------------------------------
# Prompt executor
# ---------------------------------------------------------------------------
class PromptExecutor:
    """Executes prompts through the LLM gateway with full tracking.

    Wraps the existing ``LLMGateway`` and provides:
    - Prompt template rendering and validation
    - AI execution via the gateway (never providers directly)
    - JSON response parsing
    - Execution history tracking
    - Structured logging with correlation IDs
    - Cost and token tracking

    Attributes:
        llm_gateway: The LLM gateway instance.
        prompt_manager: The existing prompt manager for file-based prompts.
    """

    def __init__(
        self,
        llm_gateway: Any = None,
        prompt_manager: Any = None,
        langfuse_client: LangfuseClient | None = None,
    ) -> None:
        """Initialize the prompt executor.

        Args:
            llm_gateway: The LLM gateway for AI calls.
            prompt_manager: The prompt manager for file-based prompt loading.
            langfuse_client: Optional Langfuse client for tracing.
        """
        self._llm_gateway = llm_gateway
        self._prompt_manager = prompt_manager
        self._langfuse_client = langfuse_client
        self._logger = get_logger(__name__)
        self._history: list[PromptExecutionRecord] = []

    @property
    def history(self) -> list[PromptExecutionRecord]:
        """Return the prompt execution history."""
        return list(self._history)

    @property
    def history_count(self) -> int:
        """Return the number of recorded executions."""
        return len(self._history)

    def clear_history(self) -> None:
        """Clear the execution history."""
        self._history.clear()

    async def execute_template(
        self,
        template: PromptTemplate,
        variables: dict[str, Any],
        *,
        agent_name: str = "",
        options: PromptExecutionOptions | None = None,
    ) -> AIResponse:
        """Execute a ``PromptTemplate`` with variables.

        Args:
            template: The prompt template to execute.
            variables: Variables to inject into the template.
            agent_name: The name of the agent executing the prompt.
            options: Execution options (temperature, max tokens, etc.).

        Returns:
            An ``AIResponse`` with the AI result.

        Raises:
            PromptExecutionError: If execution fails.
        """
        opts = options or PromptExecutionOptions()

        # Render the template
        try:
            rendered_prompt = template.render(variables)
        except Exception as exc:
            self._record_execution(
                agent_name=agent_name,
                template_name=template.name,
                template_version=template.version,
                rendered_prompt="",
                success=False,
                error=str(exc),
            )
            raise PromptExecutionError(agent_name, f"Template rendering: {exc}") from exc

        return await self._execute(
            rendered_prompt=rendered_prompt,
            agent_name=agent_name,
            template_name=template.name,
            template_version=template.version,
            options=opts,
        )

    async def execute_prompt(
        self,
        prompt: str,
        *,
        agent_name: str = "",
        options: PromptExecutionOptions | None = None,
    ) -> AIResponse:
        """Execute a raw prompt string.

        Args:
            prompt: The fully rendered prompt string.
            agent_name: The name of the agent executing the prompt.
            options: Execution options.

        Returns:
            An ``AIResponse`` with the AI result.

        Raises:
            PromptExecutionError: If execution fails.
        """
        opts = options or PromptExecutionOptions()
        return await self._execute(
            rendered_prompt=prompt,
            agent_name=agent_name,
            template_name="raw",
            template_version="",
            options=opts,
        )

    async def execute_file_prompt(
        self,
        agent_type: str,
        prompt_name: str,
        variables: dict[str, Any],
        *,
        agent_name: str = "",
        version: str | None = None,
        options: PromptExecutionOptions | None = None,
    ) -> AIResponse:
        """Execute a file-based prompt via the ``PromptManager``.

        Args:
            agent_type: The agent category for prompt lookup.
            prompt_name: The specific prompt name.
            variables: Variables to inject into the template.
            agent_name: The name of the executing agent.
            version: Optional prompt version.
            options: Execution options.

        Returns:
            An ``AIResponse`` with the AI result.

        Raises:
            PromptExecutionError: If loading or execution fails.
        """
        if self._prompt_manager is None:
            raise PromptExecutionError(agent_name, "No prompt manager configured")

        opts = options or PromptExecutionOptions()

        try:
            rendered_prompt = await self._prompt_manager.load_and_render(
                agent_type, prompt_name, variables, version
            )
        except Exception as exc:
            self._record_execution(
                agent_name=agent_name,
                template_name=f"{agent_type}/{prompt_name}",
                template_version=version or "",
                rendered_prompt="",
                success=False,
                error=str(exc),
            )
            raise PromptExecutionError(agent_name, f"Prompt loading: {exc}") from exc

        return await self._execute(
            rendered_prompt=rendered_prompt,
            agent_name=agent_name,
            template_name=f"{agent_type}/{prompt_name}",
            template_version=version or "",
            options=opts,
        )

    async def _execute(
        self,
        rendered_prompt: str,
        *,
        agent_name: str,
        template_name: str,
        template_version: str,
        options: PromptExecutionOptions,
    ) -> AIResponse:
        """Internal execution method that calls the LLM gateway."""
        if self._llm_gateway is None:
            raise PromptExecutionError(agent_name, "No LLM gateway configured")

        corr_id = options.correlation_id or str(uuid4())
        start = time.monotonic()

        # Parent (workflow) trace: attach to it instead of starting a new one.
        parent_trace_id = options.trace_id
        owns_trace = parent_trace_id is None
        trace_id: str | None = parent_trace_id
        if self._langfuse_client is not None and owns_trace:
            trace_id = self._langfuse_client.start_trace(
                name=agent_name or "prompt-execution",
                metadata={
                    "template": template_name,
                    "template_version": template_version,
                    "correlation_id": corr_id,
                },
            )

        self._logger.info(
            "prompt_executing",
            agent=agent_name,
            template=template_name,
            correlation_id=corr_id,
            prompt_length=len(rendered_prompt),
        )

        try:
            result = await self._llm_gateway.generate(
                rendered_prompt,
                use_flash=options.use_flash,
                temperature=options.temperature,
                max_output_tokens=options.max_output_tokens,
                correlation_id=corr_id,
                trace_id=trace_id,
                generation_name=f"agent: {agent_name}" if agent_name else "generate",
            )

            latency_ms = int((time.monotonic() - start) * 1000)

            # Parse JSON if expected
            structured_data = None
            warnings: list[str] = []

            if options.expect_json and result.success:
                try:
                    output = result.output if hasattr(result, "output") else str(result)
                    structured_data = json.loads(_clean_json_output(output))
                except (json.JSONDecodeError, TypeError) as exc:
                    warnings.append(f"JSON parsing failed: {exc}")

            ai_response = AIResponse.from_generation_result(
                result,
                structured_data=structured_data,
                warnings=warnings,
            )
            ai_response.correlation_id = corr_id

            if self._langfuse_client is not None and trace_id is not None and owns_trace:
                self._langfuse_client.update_trace(
                    trace_id=trace_id,
                    output=ai_response.response[:1000] if ai_response.response else "",
                    metadata={
                        "template": template_name,
                        "template_version": template_version,
                        "provider": ai_response.provider,
                        "model": ai_response.model,
                        "cost_usd": ai_response.cost_usd,
                        "input_tokens": ai_response.input_tokens,
                        "output_tokens": ai_response.output_tokens,
                        "latency_ms": latency_ms,
                        "success": True,
                    },
                )

            self._record_execution(
                agent_name=agent_name,
                template_name=template_name,
                template_version=template_version,
                rendered_prompt=rendered_prompt[:500],  # Truncate for logging
                response=ai_response.response[:500] if ai_response.response else "",
                success=True,
                provider=ai_response.provider,
                model=ai_response.model,
                cost_usd=ai_response.cost_usd,
                input_tokens=ai_response.input_tokens,
                output_tokens=ai_response.output_tokens,
                latency_ms=latency_ms,
            )

            self._logger.info(
                "prompt_executed",
                agent=agent_name,
                template=template_name,
                provider=ai_response.provider,
                model=ai_response.model,
                cost_usd=ai_response.cost_usd,
                input_tokens=ai_response.input_tokens,
                output_tokens=ai_response.output_tokens,
                latency_ms=latency_ms,
                correlation_id=corr_id,
            )

            return ai_response

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            if self._langfuse_client is not None and trace_id is not None and owns_trace:
                self._langfuse_client.update_trace(
                    trace_id=trace_id,
                    metadata={
                        "template": template_name,
                        "template_version": template_version,
                        "success": False,
                        "error": str(exc),
                        "latency_ms": latency_ms,
                    },
                )
            self._record_execution(
                agent_name=agent_name,
                template_name=template_name,
                template_version=template_version,
                rendered_prompt=rendered_prompt[:500],
                success=False,
                error=str(exc),
                latency_ms=latency_ms,
            )
            self._logger.error(
                "prompt_execution_failed",
                agent=agent_name,
                template=template_name,
                error=str(exc),
                latency_ms=latency_ms,
                correlation_id=corr_id,
            )
            raise PromptExecutionError(agent_name, str(exc)) from exc

    def _record_execution(
        self,
        *,
        agent_name: str,
        template_name: str,
        template_version: str,
        rendered_prompt: str,
        response: str = "",
        success: bool = True,
        provider: str = "",
        model: str = "",
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        """Record a prompt execution in history."""
        record = PromptExecutionRecord(
            agent_name=agent_name,
            template_name=template_name,
            template_version=template_version,
            rendered_prompt=rendered_prompt,
            response=response,
            success=success,
            provider=provider,
            model=model,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            error=error,
        )
        self._history.append(record)

    def get_history(
        self,
        agent_name: str | None = None,
        template_name: str | None = None,
    ) -> list[PromptExecutionRecord]:
        """Get execution history, optionally filtered.

        Args:
            agent_name: Filter by agent name.
            template_name: Filter by template name.

        Returns:
            List of execution records.
        """
        results = list(self._history)
        if agent_name is not None:
            results = [r for r in results if r.agent_name == agent_name]
        if template_name is not None:
            results = [r for r in results if r.template_name == template_name]
        return results

    def get_total_cost(self, agent_name: str | None = None) -> float:
        """Get total cost of all prompt executions.

        Args:
            agent_name: Optional filter by agent name.

        Returns:
            Total cost in USD.
        """
        records = self.get_history(agent_name=agent_name)
        return sum(r.cost_usd for r in records if r.success)

    def get_total_tokens(self, agent_name: str | None = None) -> int:
        """Get total tokens consumed by all prompt executions.

        Args:
            agent_name: Optional filter by agent name.

        Returns:
            Total tokens (input + output).
        """
        records = self.get_history(agent_name=agent_name)
        return sum(r.input_tokens + r.output_tokens for r in records if r.success)
