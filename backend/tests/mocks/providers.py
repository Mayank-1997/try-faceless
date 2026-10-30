"""Mock providers for testing — implement the same interfaces as real providers.

These mocks allow unit tests to exercise gateway logic without making
actual API calls.  They return deterministic, configurable responses.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.core.enums import AIProvider
from src.core.interfaces import (
    HealthStatus,
    ImageProvider,
    LLMProvider,
    ProviderConfig,
    StorageProvider,
    VideoProvider,
    VoiceProvider,
)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing.

    Returns deterministic responses.  Can be configured with custom
    responses via ``responses`` list (consumed in order).
    """

    def __init__(
        self,
        *,
        responses: list[str] | None = None,
        json_responses: list[dict[str, Any]] | None = None,
        token_count: int = 100,
        cost_per_1k: float = 0.001,
    ) -> None:
        self._responses = responses or ["Mock LLM response"]
        self._json_responses = json_responses or [{"result": "mock"}]
        self._token_count = token_count
        self._cost_per_1k = cost_per_1k
        self._initialized = False
        self._call_count = 0

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.GEMINI

    async def initialize(self, config: ProviderConfig) -> None:
        self._initialized = True

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        self._call_count += 1
        return self._responses[(self._call_count - 1) % len(self._responses)]

    async def generate_json(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        self._call_count += 1
        return self._json_responses[(self._call_count - 1) % len(self._json_responses)]

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        for word in self._responses[0].split():
            yield word + " "

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return ((input_tokens + output_tokens) / 1000) * self._cost_per_1k

    async def health_check(self) -> HealthStatus:
        return HealthStatus(healthy=True, provider="mock_llm", latency_ms=1)

    async def shutdown(self) -> None:
        self._initialized = False

    @property
    def call_count(self) -> int:
        return self._call_count


class MockImageProvider(ImageProvider):
    """Mock image provider for testing."""

    def __init__(self, *, cost_per_image: float = 0.04) -> None:
        self._cost_per_image = cost_per_image
        self._initialized = False
        self._call_count = 0

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.IMAGEN

    async def initialize(self, config: ProviderConfig) -> None:
        self._initialized = True

    async def generate_image(
        self, prompt: str, *, width: int = 1920, height: int = 1080, **kwargs: Any
    ) -> bytes:
        self._call_count += 1
        return f"mock_image_{width}x{height}".encode()

    def calculate_cost(self, width: int, height: int) -> float:
        return self._cost_per_image

    async def health_check(self) -> HealthStatus:
        return HealthStatus(healthy=True, provider="mock_image", latency_ms=1)

    async def shutdown(self) -> None:
        self._initialized = False

    @property
    def call_count(self) -> int:
        return self._call_count


class MockVideoProvider(VideoProvider):
    """Mock video provider for testing."""

    def __init__(self, *, cost_per_second: float = 0.05) -> None:
        self._cost_per_second = cost_per_second
        self._initialized = False
        self._call_count = 0

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.VEO

    async def initialize(self, config: ProviderConfig) -> None:
        self._initialized = True

    async def generate_video(
        self, prompt: str, *, duration_seconds: float = 5.0, **kwargs: Any
    ) -> bytes:
        self._call_count += 1
        return f"mock_video_{duration_seconds}s".encode()

    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        return self._cost_per_second * duration_seconds

    async def health_check(self) -> HealthStatus:
        return HealthStatus(healthy=True, provider="mock_video", latency_ms=1)

    async def shutdown(self) -> None:
        self._initialized = False

    @property
    def call_count(self) -> int:
        return self._call_count


class MockVoiceProvider(VoiceProvider):
    """Mock voice provider for testing."""

    def __init__(self, *, cost_per_1k_chars: float = 0.016) -> None:
        self._cost_per_1k_chars = cost_per_1k_chars
        self._initialized = False
        self._call_count = 0

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.GOOGLE_TTS

    async def initialize(self, config: ProviderConfig) -> None:
        self._initialized = True

    async def generate_speech(
        self, text: str, *, language: str = "en-US", **kwargs: Any
    ) -> bytes:
        self._call_count += 1
        return f"mock_audio_{len(text)}chars".encode()

    def calculate_cost(self, character_count: int) -> float:
        return (character_count / 1000) * self._cost_per_1k_chars

    async def health_check(self) -> HealthStatus:
        return HealthStatus(healthy=True, provider="mock_voice", latency_ms=1)

    async def shutdown(self) -> None:
        self._initialized = False

    @property
    def call_count(self) -> int:
        return self._call_count


class MockStorageProvider(StorageProvider):
    """Mock storage provider for testing — stores data in memory."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "mock"

    async def initialize(self, config: ProviderConfig) -> None:
        self._initialized = True

    async def upload(self, data: bytes, key: str, *, content_type: str = "application/octet-stream") -> str:
        self._data[key] = data
        return f"mock://{key}"

    async def download(self, key: str) -> bytes:
        if key not in self._data:
            from src.core.exceptions import StorageError

            raise StorageError(f"Key not found: {key}")
        return self._data[key]

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def get_url(self, key: str, *, expires_in: int = 3600) -> str:
        return f"mock://{key}"

    async def list_files(self, prefix: str, *, limit: int = 100) -> list[str]:
        return [k for k in self._data if k.startswith(prefix)][:limit]

    async def shutdown(self) -> None:
        self._data.clear()
        self._initialized = False
