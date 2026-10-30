"""Tests for the extended exception hierarchy."""

from __future__ import annotations

import pytest

from src.core.exceptions import (
    AIProviderError,
    AllProvidersFailedError,
    EventBusError,
    EventPublishError,
    GatewayError,
    ImageGatewayError,
    LLMGatewayError,
    ObservabilityError,
    PromptException,
    PromptNotFoundError,
    PromptRenderingError,
    PromptValidationError,
    ProviderAlreadyRegisteredError,
    ProviderException,
    ProviderNotInitializedError,
    ProviderNotRegisteredError,
    ProviderResponseParsingError,
    RegistryError,
    VideoGatewayError,
    VoiceGatewayError,
    WorkflowStateError,
)


class TestGatewayExceptions:
    def test_gateway_error_base(self):
        exc = GatewayError("Gateway failed")
        assert exc.code == "GATEWAY_ERROR"
        assert exc.status_code == 502

    def test_llm_gateway_error_inherits(self):
        exc = LLMGatewayError("LLM failed")
        assert isinstance(exc, GatewayError)
        assert exc.code == "LLM_GATEWAY_ERROR"

    def test_image_gateway_error_inherits(self):
        exc = ImageGatewayError("Image failed")
        assert isinstance(exc, GatewayError)
        assert exc.code == "IMAGE_GATEWAY_ERROR"

    def test_video_gateway_error_inherits(self):
        exc = VideoGatewayError("Video failed")
        assert isinstance(exc, GatewayError)
        assert exc.code == "VIDEO_GATEWAY_ERROR"

    def test_voice_gateway_error_inherits(self):
        exc = VoiceGatewayError("Voice failed")
        assert isinstance(exc, GatewayError)
        assert exc.code == "VOICE_GATEWAY_ERROR"

    def test_all_providers_failed(self):
        exc = AllProvidersFailedError("llm", ["gemini", "openai"])
        assert exc.code == "ALL_PROVIDERS_FAILED"
        assert exc.status_code == 503
        assert "gemini" in str(exc)
        assert "openai" in str(exc)


class TestProviderExceptions:
    def test_provider_exception_base(self):
        exc = ProviderException("gemini", "rate limited")
        assert exc.code == "PROVIDER_EXCEPTION"
        assert exc.provider == "gemini"
        assert "gemini" in str(exc)
        assert "rate limited" in str(exc)

    def test_provider_not_initialized(self):
        exc = ProviderNotInitializedError("gemini")
        assert exc.code == "PROVIDER_NOT_INITIALIZED"
        assert exc.provider == "gemini"

    def test_provider_response_parsing_error(self):
        exc = ProviderResponseParsingError("gemini", "invalid JSON")
        assert exc.code == "PROVIDER_RESPONSE_PARSING_ERROR"
        assert "invalid JSON" in str(exc)


class TestPromptExceptions:
    def test_prompt_not_found(self):
        exc = PromptNotFoundError("research", "web_search", "1.0")
        assert exc.code == "PROMPT_NOT_FOUND"
        assert exc.status_code == 404
        assert "web_search" in str(exc)
        assert "research" in str(exc)
        assert "1.0" in str(exc)

    def test_prompt_not_found_no_version(self):
        exc = PromptNotFoundError("research", "web_search")
        assert "version" not in str(exc)

    def test_prompt_validation_error(self):
        exc = PromptValidationError("Missing required field")
        assert exc.code == "PROMPT_VALIDATION_ERROR"
        assert exc.status_code == 422

    def test_prompt_rendering_error(self):
        exc = PromptRenderingError("template", ["topic", "audience"])
        assert exc.code == "PROMPT_RENDERING_ERROR"
        assert "topic" in str(exc)
        assert "audience" in str(exc)


class TestRegistryExceptions:
    def test_provider_not_registered(self):
        exc = ProviderNotRegisteredError("openai")
        assert exc.code == "PROVIDER_NOT_REGISTERED"
        assert exc.status_code == 404
        assert "openai" in str(exc)

    def test_provider_already_registered(self):
        exc = ProviderAlreadyRegisteredError("gemini")
        assert exc.code == "PROVIDER_ALREADY_REGISTERED"
        assert exc.status_code == 409
        assert "gemini" in str(exc)


class TestEventBusExceptions:
    def test_event_publish_error(self):
        exc = EventPublishError("ResearchCompleted", "bus not initialised")
        assert exc.code == "EVENT_PUBLISH_ERROR"
        assert "ResearchCompleted" in str(exc)


class TestOtherExceptions:
    def test_observability_error(self):
        exc = ObservabilityError("Metrics collection failed")
        assert exc.code == "OBSERVABILITY_ERROR"

    def test_workflow_state_error(self):
        exc = WorkflowStateError("Invalid state transition")
        assert exc.code == "WORKFLOW_STATE_ERROR"
        assert exc.status_code == 422
