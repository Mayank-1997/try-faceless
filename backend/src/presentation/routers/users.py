"""Users router — user profile and management endpoints.

GET /users/me
PATCH /users/me
PATCH /users/password
GET /users/{id}
GET /users
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    ChangePasswordRequest,
    MessageResponse,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserListResponse,
    UserPreferencesResponse,
    UserResponse,
)
from src.application.services.authorization_service import require_authentication
from src.application.services.password_service import PasswordService
from src.application.services.user_service import UserService
from src.core.enums import UserStatus
from src.infrastructure.database.engine import get_db_session

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_service(db: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(db, PasswordService())


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    http_request: Request,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Get the current authenticated user's profile."""
    return await user_service.get_current_user(UUID(user["id"]))


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    http_request: Request,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Update the current user's profile."""
    response = await user_service.update_profile(UUID(user["id"]), request)
    await user_service._session.commit()
    return response


@router.patch("/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Change the current user's password."""
    await user_service.change_password(UUID(user["id"]), request)
    await user_service._session.commit()
    return MessageResponse(message="Password changed successfully.")


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    http_request: Request,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Get the current user's preferences."""
    return await user_service.get_preferences(UUID(user["id"]))


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    http_request: Request,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Update the current user's preferences."""
    response = await user_service.update_preferences(UUID(user["id"]), request)
    await user_service._session.commit()
    return response


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """Get a user by ID (admin operation)."""
    response = await user_service.get_user_by_id(user_id)
    await user_service._session.commit()
    return response


@router.get("", response_model=UserListResponse)
async def list_users(
    status: UserStatus | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(require_authentication),
    user_service: UserService = Depends(_get_user_service),
):
    """List users with optional status filter and pagination."""
    response = await user_service.list_users(status=status, offset=offset, limit=limit)
    await user_service._session.commit()
    return response
