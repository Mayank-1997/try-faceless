"""User preferences entity — per-user application settings."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.core.enums import ThemePreference


class UserPreferences:
    """Per-user application preferences.

    Stored as a separate table with a 1:1 relationship to users.

    Attributes:
        user_id: The user these preferences belong to.
        theme: UI theme preference.
        language: Preferred language code.
        default_ai_model: Default AI model for generation.
        preferred_llm: Preferred LLM provider.
        preferred_voice: Preferred voice provider.
        preferred_image_provider: Preferred image generation provider.
        preferred_video_provider: Preferred video generation provider.
        email_notifications: Whether to send email notifications.
        push_notifications: Whether to send push notifications.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        user_id: UUID,
        theme: ThemePreference = ThemePreference.SYSTEM,
        language: str = "en",
        default_ai_model: str = "gemini-2.5-pro",
        preferred_llm: str = "gemini",
        preferred_voice: str = "google_tts",
        preferred_image_provider: str = "imagen",
        preferred_video_provider: str = "veo",
        email_notifications: bool = True,
        push_notifications: bool = False,
        updated_at: datetime | None = None,
    ) -> None:
        self.user_id = user_id
        self.theme = theme
        self.language = language
        self.default_ai_model = default_ai_model
        self.preferred_llm = preferred_llm
        self.preferred_voice = preferred_voice
        self.preferred_image_provider = preferred_image_provider
        self.preferred_video_provider = preferred_video_provider
        self.email_notifications = email_notifications
        self.push_notifications = push_notifications
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, object]:
        return {
            "user_id": str(self.user_id),
            "theme": self.theme.value,
            "language": self.language,
            "default_ai_model": self.default_ai_model,
            "preferred_llm": self.preferred_llm,
            "preferred_voice": self.preferred_voice,
            "preferred_image_provider": self.preferred_image_provider,
            "preferred_video_provider": self.preferred_video_provider,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
