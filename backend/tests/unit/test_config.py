"""Unit tests for configuration management."""

from __future__ import annotations

import os

import pytest

from src.core.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings configuration model."""

    def test_default_values(self) -> None:
        """Settings should load with sensible defaults even without env vars."""
        get_settings.cache_clear()
        settings = Settings()
        assert settings.app_name == "AI Video Studio"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.port == 8000
        assert settings.api_prefix == "/api/v1"

    def test_database_url_construction(self) -> None:
        settings = Settings()
        assert "postgresql+asyncpg://" in settings.database.url
        assert settings.database.host in settings.database.url

    def test_sync_url_for_alembic(self) -> None:
        settings = Settings()
        assert "postgresql+psycopg2://" in settings.database.sync_url

    def test_redis_url_construction(self) -> None:
        settings = Settings()
        assert "redis://" in settings.redis.url

    def test_is_production_flag(self) -> None:
        settings = Settings(environment="production")
        assert settings.is_production is True
        assert settings.is_development is False

    def test_is_development_flag(self) -> None:
        settings = Settings(environment="development")
        assert settings.is_development is True
        assert settings.is_production is False

    def test_cors_origins_parsing_from_string(self) -> None:
        """CORS_ORIGINS should parse comma-separated strings into lists."""
        from src.core.config import CORSSettings

        cors = CORSSettings(origins="http://a.com,http://b.com")
        assert cors.origins == ["http://a.com", "http://b.com"]

    def test_gemini_settings_defaults(self) -> None:
        settings = Settings()
        assert settings.gemini.pro_model == "gemini-2.5-pro"
        assert settings.gemini.flash_model == "gemini-2.5-flash"
        assert settings.gemini.max_retries == 3

    def test_cost_settings_defaults(self) -> None:
        settings = Settings()
        assert settings.cost.veo_per_second > 0
        assert settings.cost.imagen_per_image > 0
        assert settings.cost.tts_per_1k_chars > 0

    def test_get_settings_is_cached(self) -> None:
        """get_settings() should return the same instance on repeated calls."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_settings_cache_clear(self) -> None:
        """Cache clearing should produce a new instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        assert s1 is not s2
