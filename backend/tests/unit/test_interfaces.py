"""Tests for the base interfaces module."""

from __future__ import annotations

import inspect

import pytest

from src.core.interfaces import (
    CostCalculator,
    HealthStatus,
    ImageProvider,
    LLMProvider,
    ProviderConfig,
    PromptLoader,
    Renderer,
    StorageProvider,
    VideoProvider,
    VoiceProvider,
)


class TestProviderConfig:
    def test_creation_with_defaults(self):
        config = ProviderConfig(api_key="key", model="model")
        assert config.api_key == "key"
        assert config.model == "model"
        assert config.max_retries == 3
        assert config.request_timeout == 120
        assert config.extra == {}

    def test_creation_with_custom_values(self):
        config = ProviderConfig(
            api_key="key",
            model="model",
            max_retries=5,
            request_timeout=60,
            extra={"foo": "bar"},
        )
        assert config.max_retries == 5
        assert config.request_timeout == 60
        assert config.extra == {"foo": "bar"}

    def test_frozen(self):
        config = ProviderConfig(api_key="key", model="model")
        with pytest.raises(AttributeError):
            config.api_key = "new-key"


class TestHealthStatus:
    def test_healthy(self):
        status = HealthStatus(healthy=True, provider="test")
        assert status.healthy is True
        assert status.provider == "test"
        assert status.latency_ms is None
        assert status.details == {}

    def test_with_details(self):
        status = HealthStatus(
            healthy=False,
            provider="test",
            latency_ms=500,
            details={"error": "timeout"},
        )
        assert status.healthy is False
        assert status.latency_ms == 500
        assert status.details == {"error": "timeout"}


class TestInterfaceAbstractness:
    """Verify all interfaces are abstract and cannot be instantiated directly."""

    @pytest.mark.parametrize(
        "interface",
        [LLMProvider, ImageProvider, VideoProvider, VoiceProvider,
         Renderer, StorageProvider, PromptLoader, CostCalculator],
    )
    def test_cannot_instantiate_directly(self, interface):
        with pytest.raises(TypeError):
            interface()

    @pytest.mark.parametrize(
        "interface",
        [LLMProvider, ImageProvider, VideoProvider, VoiceProvider,
         Renderer, StorageProvider, PromptLoader, CostCalculator],
    )
    def test_has_abstract_methods(self, interface):
        assert inspect.isabstract(interface) or len(interface.__abstractmethods__) > 0
