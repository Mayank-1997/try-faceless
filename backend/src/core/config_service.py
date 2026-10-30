"""Centralised configuration service — wraps Settings with feature flags,
runtime overrides, and environment-aware behaviour.

This is the **only** module that should access environment variables.
All other modules receive configuration via dependency injection through
``ConfigService``.

Responsibilities:
- Load and validate environment variables (delegated to ``Settings``).
- Provide feature flag checking (``is_feature_enabled()``).
- Support runtime configuration overrides (for testing and hot-reload).
- Environment switching (development, staging, production).
- Provider configuration access (typed sub-settings).
- Typed access to all configuration values.

Usage::

    config = ConfigService()
    if config.is_feature_enabled("video_generation"):
        ...
    db_url = config.database.url
"""

from __future__ import annotations

from typing import Any

from src.core.config import Settings, get_settings
from src.core.enums import AppEnvironment
from src.core.exceptions import ConfigurationError


class ConfigService:
    """Centralised configuration service with feature flags and runtime overrides.

    Wraps the ``Settings`` Pydantic model and adds:
    - Feature flag management with defaults and runtime overrides.
    - Environment-aware behaviour (dev/staging/prod).
    - Runtime configuration overrides for testing.
    - Provider configuration access.

    Attributes:
        settings: The underlying ``Settings`` instance.
    """

    # Default feature flags — can be overridden via runtime overrides
    # or environment variables in future iterations.
    _DEFAULT_FEATURE_FLAGS: dict[str, bool] = {
        "video_generation": True,
        "image_generation": True,
        "voice_generation": True,
        "subtitle_generation": True,
        "thumbnail_generation": True,
        "seo_optimization": True,
        "auto_publish": False,
        "cost_tracking": True,
        "token_tracking": True,
        "event_bus": True,
        "observability": True,
        "parallel_generation": True,
        "quality_check": True,
        "prompt_caching": True,
        "provider_fallback": True,
        "streaming_responses": True,
    }

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialise the configuration service.

        Args:
            settings: Optional ``Settings`` instance. If ``None``, loads
                from environment via ``get_settings()``.
        """
        self._settings = settings or get_settings()
        self._feature_flags: dict[str, bool] = dict(self._DEFAULT_FEATURE_FLAGS)
        self._runtime_overrides: dict[str, Any] = {}

    # -----------------------------------------------------------------------
    # Properties — delegate to the underlying Settings
    # -----------------------------------------------------------------------
    @property
    def settings(self) -> Settings:
        """Return the underlying ``Settings`` instance."""
        return self._settings

    @property
    def app_name(self) -> str:
        return self._settings.app_name

    @property
    def environment(self) -> AppEnvironment:
        return AppEnvironment(self._settings.environment)

    @property
    def is_development(self) -> bool:
        return self._settings.is_development

    @property
    def is_staging(self) -> bool:
        return self._settings.environment == "staging"

    @property
    def is_production(self) -> bool:
        return self._settings.is_production

    @property
    def is_testing(self) -> bool:
        return self._runtime_overrides.get("__testing__", False)

    @property
    def debug(self) -> bool:
        return self._settings.debug

    @property
    def api_prefix(self) -> str:
        return self._settings.api_prefix

    # -----------------------------------------------------------------------
    # Sub-settings access
    # -----------------------------------------------------------------------
    @property
    def database(self):
        return self._settings.database

    @property
    def redis(self):
        return self._settings.redis

    @property
    def celery(self):
        return self._settings.celery

    @property
    def jwt(self):
        return self._settings.jwt

    @property
    def gemini(self):
        return self._settings.gemini

    @property
    def veo(self):
        return self._settings.veo

    @property
    def kling(self):
        return self._settings.kling

    @property
    def imagen(self):
        return self._settings.imagen

    @property
    def stock(self):
        return self._settings.stock

    @property
    def tts(self):
        return self._settings.tts

    @property
    def youtube(self):
        return self._settings.youtube

    @property
    def storage(self):
        return self._settings.storage

    @property
    def ffmpeg(self):
        return self._settings.ffmpeg

    @property
    def cost(self):
        return self._settings.cost

    @property
    def cors(self):
        return self._settings.cors

    @property
    def rate_limit(self):
        return self._settings.rate_limit

    @property
    def langfuse(self):
        return self._settings.langfuse

    # -----------------------------------------------------------------------
    # Feature flags
    # -----------------------------------------------------------------------
    def is_feature_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled.

        Runtime overrides take precedence over defaults.

        Args:
            flag_name: The feature flag identifier.

        Returns:
            ``True`` if the feature is enabled.

        Raises:
            ConfigurationError: If the flag name is not recognised.
        """
        if flag_name not in self._feature_flags:
            raise ConfigurationError(
                f"Unknown feature flag '{flag_name}'. "
                f"Available flags: {sorted(self._feature_flags.keys())}"
            )
        return self._feature_flags[flag_name]

    def set_feature_flag(self, flag_name: str, enabled: bool) -> None:
        """Set a feature flag at runtime.

        Args:
            flag_name: The feature flag identifier.
            enabled: Whether the feature should be enabled.

        Raises:
            ConfigurationError: If the flag name is not recognised.
        """
        if flag_name not in self._feature_flags:
            raise ConfigurationError(f"Unknown feature flag '{flag_name}'")
        self._feature_flags[flag_name] = enabled

    def get_all_feature_flags(self) -> dict[str, bool]:
        """Return a copy of all feature flags and their current state."""
        return dict(self._feature_flags)

    # -----------------------------------------------------------------------
    # Runtime overrides (primarily for testing)
    # -----------------------------------------------------------------------
    def set_override(self, key: str, value: Any) -> None:
        """Set a runtime configuration override.

        These overrides are stored in-memory and do not persist across
        process restarts.  Primarily used for testing.

        Args:
            key: The override key.
            value: The override value.
        """
        self._runtime_overrides[key] = value

    def get_override(self, key: str, default: Any = None) -> Any:
        """Get a runtime configuration override.

        Args:
            key: The override key.
            default: Default value if the key is not set.

        Returns:
            The override value or the default.
        """
        return self._runtime_overrides.get(key, default)

    def clear_overrides(self) -> None:
        """Clear all runtime configuration overrides."""
        self._runtime_overrides.clear()

    def set_testing_mode(self, enabled: bool = True) -> None:
        """Enable or disable testing mode.

        In testing mode, certain safety checks are relaxed and mock
        providers are preferred.
        """
        self._runtime_overrides["__testing__"] = enabled

    # -----------------------------------------------------------------------
    # Provider configuration
    # -----------------------------------------------------------------------
    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get configuration for a specific AI provider.

        Args:
            provider: Provider name (e.g. "gemini", "veo", "imagen", "tts").

        Returns:
            Dictionary of provider configuration values.

        Raises:
            ConfigurationError: If the provider is not recognised.
        """
        provider_configs = {
            "gemini": self._settings.gemini,
            "veo": self._settings.veo,
            "imagen": self._settings.imagen,
            "tts": self._settings.tts,
            "youtube": self._settings.youtube,
        }
        if provider not in provider_configs:
            raise ConfigurationError(
                f"Unknown provider '{provider}'. "
                f"Available: {sorted(provider_configs.keys())}"
            )
        config = provider_configs[provider]
        return {k: v for k, v in config.__dict__.items() if not k.startswith("_")}

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Validate the configuration and return a list of issues.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        issues: list[str] = []

        if self.is_production:
            if self._settings.jwt.secret_key in ("change-me", "change-me-in-production-use-a-secure-random-string"):
                issues.append("JWT secret key must be changed in production")
            if self._settings.debug:
                issues.append("Debug mode should be disabled in production")

        if not self._settings.gemini.api_key and self.is_feature_enabled("cost_tracking"):
            issues.append("GEMINI_API_KEY is not set — LLM operations will fail")

        return issues
