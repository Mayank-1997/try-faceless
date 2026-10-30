"""Tests for the response DTOs."""

from __future__ import annotations

from datetime import datetime

from src.application.dto.responses import (
    FailureResponse,
    GenerationResult,
    HealthCheckResult,
    PaginatedResponse,
    ProgressResponse,
    RetryResult,
    StreamingChunk,
    SuccessResponse,
)


class TestSuccessResponse:
    def test_basic(self):
        resp = SuccessResponse(data={"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}
        assert resp.correlation_id is not None
        assert resp.timestamp is not None

    def test_with_message(self):
        resp = SuccessResponse(data="ok", message="Operation completed")
        assert resp.message == "Operation completed"


class TestFailureResponse:
    def test_basic(self):
        resp = FailureResponse(
            error_code="TEST_ERROR",
            error_message="Something went wrong",
        )
        assert resp.success is False
        assert resp.error_code == "TEST_ERROR"
        assert resp.error_message == "Something went wrong"
        assert resp.retryable is False

    def test_with_details(self):
        resp = FailureResponse(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input",
            error_details={"field": "name", "issue": "required"},
            retryable=True,
        )
        assert resp.error_details["field"] == "name"
        assert resp.retryable is True


class TestProgressResponse:
    def test_basic(self):
        resp = ProgressResponse(
            step="generating",
            current=5,
            total=10,
            percentage=50.0,
        )
        assert resp.step == "generating"
        assert resp.percentage == 50.0
        assert resp.is_complete is False

    def test_complete(self):
        resp = ProgressResponse(
            step="done",
            current=10,
            total=10,
            percentage=100.0,
        )
        assert resp.is_complete is True


class TestStreamingChunk:
    def test_basic(self):
        chunk = StreamingChunk(chunk="hello", chunk_index=0)
        assert chunk.chunk == "hello"
        assert chunk.chunk_index == 0
        assert chunk.is_final is False

    def test_final_chunk(self):
        chunk = StreamingChunk(chunk="", chunk_index=10, is_final=True)
        assert chunk.is_final is True


class TestGenerationResult:
    def test_basic(self):
        result = GenerationResult(
            provider="gemini",
            model="gemini-2.5-pro",
            output="Generated text",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            latency_ms=500,
        )
        assert result.success is True
        assert result.provider == "gemini"
        assert result.total_tokens == 150
        assert result.has_quality_score is False

    def test_with_quality_score(self):
        result = GenerationResult(
            provider="gemini",
            model="gemini-2.5-pro",
            output="text",
            quality_score=0.85,
        )
        assert result.has_quality_score is True
        assert result.quality_score == 0.85


class TestRetryResult:
    def test_has_attempts_remaining(self):
        result = RetryResult(attempt=2, max_attempts=5, succeeded=False)
        assert result.has_attempts_remaining is True
        assert result.is_final_attempt is False

    def test_final_attempt(self):
        result = RetryResult(attempt=5, max_attempts=5, succeeded=False)
        assert result.has_attempts_remaining is False
        assert result.is_final_attempt is True

    def test_succeeded(self):
        result = RetryResult(attempt=3, max_attempts=5, succeeded=True)
        assert result.succeeded is True


class TestHealthCheckResult:
    def test_healthy(self):
        result = HealthCheckResult(service="gemini", healthy=True, latency_ms=50)
        assert result.healthy is True
        assert result.latency_ms == 50

    def test_unhealthy(self):
        result = HealthCheckResult(
            service="veo", healthy=False, details={"error": "timeout"}
        )
        assert result.healthy is False
        assert result.details["error"] == "timeout"


class TestPaginatedResponse:
    def test_basic(self):
        resp = PaginatedResponse(
            items=["a", "b", "c"],
            total=30,
            page=1,
            page_size=10,
            total_pages=3,
        )
        assert resp.total == 30
        assert resp.has_next is True
        assert resp.has_prev is False

    def test_last_page(self):
        resp = PaginatedResponse(
            items=["x"],
            total=25,
            page=3,
            page_size=10,
            total_pages=3,
        )
        assert resp.has_next is False
        assert resp.has_prev is True
