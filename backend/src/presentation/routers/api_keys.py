"""API Keys router — API key management endpoints.

GET /api-keys
POST /api-keys
DELETE /api-keys/{id}
PATCH /api-keys/{id}
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    ApiKeyResponse,
    ApiKeyWithSecretResponse,
    CreateApiKeyRequest,
    MessageResponse,
    UpdateApiKeyRequest,
)
from src.application.services.api_key_service import ApiKeyService
from src.application.services.authorization_service import require_authentication
from src.infrastructure.database.engine import get_db_session

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def _get_api_key_service(db: AsyncSession = Depends(get_db_session)) -> ApiKeyService:
    return ApiKeyService(db)


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: dict = Depends(require_authentication),
    api_key_service: ApiKeyService = Depends(_get_api_key_service),
):
    """List all API keys for the current user."""
    return await api_key_service.list_keys(UUID(user["id"]))


@router.post("", response_model=ApiKeyWithSecretResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    user: dict = Depends(require_authentication),
    api_key_service: ApiKeyService = Depends(_get_api_key_service),
):
    """Create a new API key. The raw key is shown only once."""
    response = await api_key_service.create_key(UUID(user["id"]), request)
    await api_key_service._session.commit()
    return response


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: UUID,
    user: dict = Depends(require_authentication),
    api_key_service: ApiKeyService = Depends(_get_api_key_service),
):
    """Revoke an API key."""
    await api_key_service.revoke_key(UUID(user["id"]), key_id)
    await api_key_service._session.commit()
    return MessageResponse(message="API key revoked successfully.")


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: UUID,
    request: UpdateApiKeyRequest,
    user: dict = Depends(require_authentication),
    api_key_service: ApiKeyService = Depends(_get_api_key_service),
):
    """Update an API key's name or scopes."""
    response = await api_key_service.update_key(UUID(user["id"]), key_id, request)
    await api_key_service._session.commit()
    return response
