"""Tests for the LLM Gateway using mock providers."""

from __future__ import annotations

from typing import Any

import pytest

from src.ai.gateway.llm_gateway import LLMGateway
from src.ai.providers.registry import ProviderRegistry
from src.core.enums import AIProvider
from src.core.exceptions import LLMGatewayError
from tests.mocks.providers import MockLLMProvider


class MockRegistry:
    """Minimal registry mock for gateway tests."""

    def __init__(self, providers: list[Any]) -> None:
        self._providers = providers

    def get_providers_by_type(self, interface_type: type) -> list[Any]:
        return self._providers

    def get_provider_names_by_type(self, interface_type: type) -> list[str]:
        return [p.provider_name.value for p in self._providers]


class MockConfig:
    """Minimal config mock for gateway tests."""

    class _Gemini:
        pro_model = "gemini-2.5-pro"
        flash_model = "gemini-2.5-flash"
        max_retries = 2

    gemini = _Gemini()

    def is_feature_enabled(self, flag: str) -> bool:
        return flag != "provider_fallback"  # Disable fallback by default


@pytest.fixture
def mock_registry():
    provider = MockLLMProvider(
        responses=["Test response 1", "Test response 2"],
        json_responses=[{"result": "test"}],
    )
    return MockRegistry([provider])


@pytest.fixture
def mock_config():
    return MockConfig()


@pytest.fixture
async def llm_gateway(mock_registry, mock_config):
    gateway = LLMGateway(registry=mock_registry, config=mock_config)
    await gateway.initialize()
    yield gateway
    await gateway.shutdown()


class TestLLMGateway:
    @pytest.mark.asyncio
    async def test_generate(self, llm_gateway):
        result = await llm_gateway.generate("test prompt")
        assert result.success is True
        assert result.output == "Test response 1"
        assert result.provider == "gemini"
        assert result.input_tokens > 0
        assert result.output_tokens > 0
        assert result.cost_usd >= 0
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_generate_json(self, llm_gateway):
        result = await llm_gateway.generate_json("test prompt")
        assert result.success is True
        assert result.output == {"result": "test"}

    @pytest.mark.asyncio
    async def test_stream(self, llm_gateway):
        chunks = []
        async for chunk in llm_gateway.stream("test prompt"):
            chunks.append(chunk)
        # Should have at least the text chunks plus a final chunk
        assert len(chunks) > 0
        assert chunks[-1].is_final is True

    def test_count_tokens(self, llm_gateway):
        count = llm_gateway.count_tokens("Hello world")
        assert count > 0

    def test_calculate_cost(self, llm_gateway):
        cost = llm_gateway.calculate_cost(1000, 500)
        assert cost > 0

    @pytest.mark.asyncio
    async def test_health_check(self, llm_gateway):
        health = await llm_gateway.health_check()
        assert health.healthy is True

    @pytest.mark.asyncio
    async def test_not_initialized_raises(self, mock_registry, mock_config):
        gateway = LLMGateway(registry=mock_registry, config=mock_config)
        with pytest.raises(LLMGatewayError):
            await gateway.generate("test")

    @pytest.mark.asyncio
    async def test_caching(self, llm_gateway, mock_config):
        # Enable caching
        mock_config.is_feature_enabled = lambda flag: True

        result1 = await llm_gateway.generate("cached prompt")
        result2 = await llm_gateway.generate("cached prompt")
        assert result2.metadata.get("cached") is True
