"""User service — user management operations.

Handles profile updates, password changes, preferences, and user listing.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    ChangePasswordRequest,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserListResponse,
    UserPreferencesResponse,
    UserResponse,
)
from src.application.services.password_service import PasswordService
from src.core.enums import ThemePreference, UserStatus
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    PasswordMismatchError,
    UserNotFoundError,
)
from src.domain.entities.preferences import UserPreferences
from src.persistence.repositories.auth_repositories import (
    SqlAlchemyUserPreferencesRepository,
    SqlAlchemyUserRepository,
)


class UserService:
    """Service for user management operations."""

    def __init__(
        self,
        session: AsyncSession,
        password_service: PasswordService,
    ) -> None:
        self._session = session
        self._password_service = password_service
        self._logger = get_logger(__name__)
        self._user_repo = SqlAlchemyUserRepository(session)
        self._preferences_repo = SqlAlchemyUserPreferencesRepository(session)

    async def get_current_user(self, user_id: UUID) -> UserResponse:
        """Get the current user's profile.

        Raises:
            UserNotFoundError: If the user doesn't exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        roles = await self._user_repo.get_user_roles(user_id)
        return _user_to_response(user, [r.name for r in roles])

    async def get_user_by_id(self, user_id: UUID) -> UserResponse:
        """Get a user by ID (admin operation).

        Raises:
            UserNotFoundError: If the user doesn't exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        roles = await self._user_repo.get_user_roles(user_id)
        return _user_to_response(user, [r.name for r in roles])

    async def list_users(
        self,
        *,
        status: UserStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> UserListResponse:
        """List users with optional status filter and pagination."""
        users = await self._user_repo.list_users(status=status, offset=offset, limit=limit)
        total = await self._user_repo.count(status=status)

        responses: list[UserResponse] = []
        for user in users:
            roles = await self._user_repo.get_user_roles(user.id)
            responses.append(_user_to_response(user, [r.name for r in roles]))

        return UserListResponse(users=responses, total=total, offset=offset, limit=limit)

    async def update_profile(self, user_id: UUID, request: UpdateProfileRequest) -> UserResponse:
        """Update the current user's profile.

        Raises:
            UserNotFoundError: If the user doesn't exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        user.update_profile(
            first_name=request.first_name,
            last_name=request.last_name,
            profile_image_url=request.profile_image_url,
            phone=request.phone,
            timezone=request.timezone,
            language=request.language,
        )
        user = await self._user_repo.update(user)
        roles = await self._user_repo.get_user_roles(user.id)

        self._logger.info("profile_updated", user_id=str(user_id))
        return _user_to_response(user, [r.name for r in roles])

    async def change_password(self, user_id: UUID, request: ChangePasswordRequest) -> bool:
        """Change the current user's password.

        Raises:
            UserNotFoundError: If the user doesn't exist.
            PasswordMismatchError: If the current password is incorrect.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        hashed = await self._user_repo.get_hashed_password(user_id)
        if hashed is None:
            raise UserNotFoundError(str(user_id))

        if not self._password_service.verify_password(request.current_password, hashed):
            raise PasswordMismatchError()

        self._password_service.validate_strength(request.new_password)
        new_hash = self._password_service.hash_password(request.new_password)
        await self._user_repo.update_password(user_id, new_hash)

        self._logger.info("password_changed", user_id=str(user_id))
        return True

    async def get_preferences(self, user_id: UUID) -> UserPreferencesResponse:
        """Get the current user's preferences."""
        prefs = await self._preferences_repo.get_or_create(user_id)
        return _preferences_to_response(prefs)

    async def update_preferences(
        self, user_id: UUID, request: UpdatePreferencesRequest
    ) -> UserPreferencesResponse:
        """Update the current user's preferences."""
        prefs = await self._preferences_repo.get_or_create(user_id)

        if request.theme is not None:
            prefs.theme = ThemePreference(request.theme)
        if request.language is not None:
            prefs.language = request.language
        if request.default_ai_model is not None:
            prefs.default_ai_model = request.default_ai_model
        if request.preferred_llm is not None:
            prefs.preferred_llm = request.preferred_llm
        if request.preferred_voice is not None:
            prefs.preferred_voice = request.preferred_voice
        if request.preferred_image_provider is not None:
            prefs.preferred_image_provider = request.preferred_image_provider
        if request.preferred_video_provider is not None:
            prefs.preferred_video_provider = request.preferred_video_provider
        if request.email_notifications is not None:
            prefs.email_notifications = request.email_notifications
        if request.push_notifications is not None:
            prefs.push_notifications = request.push_notifications

        prefs = await self._preferences_repo.update(prefs)

        self._logger.info("preferences_updated", user_id=str(user_id))
        return _preferences_to_response(prefs)


def _user_to_response(user, role_names: list[str]) -> UserResponse:
    from src.application.services.authentication_service import _user_to_response as _convert
    return _convert(user, role_names)


def _preferences_to_response(prefs: UserPreferences) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        theme=prefs.theme.value,
        language=prefs.language,
        default_ai_model=prefs.default_ai_model,
        preferred_llm=prefs.preferred_llm,
        preferred_voice=prefs.preferred_voice,
        preferred_image_provider=prefs.preferred_image_provider,
        preferred_video_provider=prefs.preferred_video_provider,
        email_notifications=prefs.email_notifications,
        push_notifications=prefs.push_notifications,
    )
