"""Tests for the ConfigService module."""

from __future__ import annotations

import pytest

from src.core.config_service import ConfigService
from src.core.exceptions import ConfigurationError


class TestConfigService:
    def test_initialization(self):
        config = ConfigService()
        assert config.app_name is not None
        assert config.environment is not None

    def test_sub_settings_access(self):
        config = ConfigService()
        assert config.database is not None
        assert config.redis is not None
        assert config.celery is not None
        assert config.jwt is not None
        assert config.gemini is not None
        assert config.veo is not None
        assert config.imagen is not None
        assert config.tts is not None
        assert config.storage is not None
        assert config.ffmpeg is not None
        assert config.cost is not None
        assert config.cors is not None
        assert config.rate_limit is not None

    def test_feature_flags_default(self):
        config = ConfigService()
        assert config.is_feature_enabled("video_generation") is True
        assert config.is_feature_enabled("auto_publish") is False
        assert config.is_feature_enabled("cost_tracking") is True

    def test_feature_flag_override(self):
        config = ConfigService()
        config.set_feature_flag("auto_publish", True)
        assert config.is_feature_enabled("auto_publish") is True

    def test_unknown_feature_flag_raises(self):
        config = ConfigService()
        with pytest.raises(ConfigurationError):
            config.is_feature_enabled("nonexistent_flag")

    def test_set_unknown_feature_flag_raises(self):
        config = ConfigService()
        with pytest.raises(ConfigurationError):
            config.set_feature_flag("nonexistent_flag", True)

    def test_get_all_feature_flags(self):
        config = ConfigService()
        flags = config.get_all_feature_flags()
        assert isinstance(flags, dict)
        assert "video_generation" in flags
        assert len(flags) > 10

    def test_runtime_overrides(self):
        config = ConfigService()
        config.set_override("custom_key", "custom_value")
        assert config.get_override("custom_key") == "custom_value"
        assert config.get_override("nonexistent", "default") == "default"

    def test_clear_overrides(self):
        config = ConfigService()
        config.set_override("key1", "value1")
        config.clear_overrides()
        assert config.get_override("key1") is None

    def test_testing_mode(self):
        config = ConfigService()
        assert config.is_testing is False
        config.set_testing_mode(True)
        assert config.is_testing is True

    def test_get_provider_config(self):
        config = ConfigService()
        gemini_config = config.get_provider_config("gemini")
        assert isinstance(gemini_config, dict)

    def test_get_unknown_provider_config_raises(self):
        config = ConfigService()
        with pytest.raises(ConfigurationError):
            config.get_provider_config("nonexistent")

    def test_validate_returns_list(self):
        config = ConfigService()
        issues = config.validate()
        assert isinstance(issues, list)

    def test_environment_properties(self):
        config = ConfigService()
        # Environment should be one of the AppEnvironment values
        assert config.environment is not None
        # is_development / is_production should be consistent
        if config.is_production:
            assert not config.is_development
