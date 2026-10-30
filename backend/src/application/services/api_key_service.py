"""API Key service — creation, validation, revocation.

API keys are stored as SHA-256 hashes. The raw key is shown to the
user exactly once at creation time.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    ApiKeyResponse,
    ApiKeyWithSecretResponse,
    CreateApiKeyRequest,
    UpdateApiKeyRequest,
)
from src.core.enums import ApiKeyStatus
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import ApiKeyNotFoundError
from src.domain.entities.api_key import ApiKey
from src.persistence.repositories.auth_repositories import SqlAlchemyApiKeyRepository


class ApiKeyService:
    """Service for API key management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logger = get_logger(__name__)
        self._repo = SqlAlchemyApiKeyRepository(session)

    @staticmethod
    def _generate_raw_key() -> str:
        """Generate a raw API key string."""
        return f"avs_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_prefix(raw_key: str) -> str:
        """Get the display prefix (first 12 characters)."""
        return raw_key[:12]

    async def create_key(
        self,
        user_id: UUID,
        request: CreateApiKeyRequest,
    ) -> ApiKeyWithSecretResponse:
        """Create a new API key.

        Args:
            user_id: Owner of the key.
            request: Key creation data.

        Returns:
            ``ApiKeyWithSecretResponse`` including the raw key (shown once).
        """
        raw_key = self._generate_raw_key()
        key_hash = self._hash_key(raw_key)
        key_prefix = self._get_prefix(raw_key)

        expires_at = None
        if request.expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

        api_key = ApiKey(
            user_id=user_id,
            name=request.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=request.scopes,
            expires_at=expires_at,
        )
        api_key = await self._repo.create(api_key)

        self._logger.info("api_key_created", user_id=str(user_id), key_id=str(api_key.id))

        return ApiKeyWithSecretResponse(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,
            key_prefix=api_key.key_prefix,
            status=api_key.status.value,
            scopes=api_key.scopes,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
        )

    async def list_keys(self, user_id: UUID) -> list[ApiKeyResponse]:
        """List all API keys for a user."""
        keys = await self._repo.list_by_user(user_id)
        return [_to_response(k) for k in keys]

    async def revoke_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke an API key.

        Raises:
            ApiKeyNotFoundError: If the key doesn't exist or doesn't belong to the user.
        """
        key = await self._repo.get_by_id(key_id)
        if key is None or key.user_id != user_id:
            raise ApiKeyNotFoundError()

        await self._repo.revoke(key_id)
        self._logger.info("api_key_revoked", user_id=str(user_id), key_id=str(key_id))
        return True

    async def update_key(
        self,
        user_id: UUID,
        key_id: UUID,
        request: UpdateApiKeyRequest,
    ) -> ApiKeyResponse:
        """Update an API key's name or scopes.

        Raises:
            ApiKeyNotFoundError: If the key doesn't exist or doesn't belong to the user.
        """
        key = await self._repo.get_by_id(key_id)
        if key is None or key.user_id != user_id:
            raise ApiKeyNotFoundError()

        if request.name is not None:
            key.name = request.name
        if request.scopes is not None:
            key.scopes = request.scopes

        key = await self._repo.update(key)
        return _to_response(key)

    async def validate_key(self, raw_key: str) -> ApiKey | None:
        """Validate a raw API key and return the entity if valid.

        Args:
            raw_key: The raw API key string from the Authorization header.

        Returns:
            ``ApiKey`` entity if valid, ``None`` otherwise.
        """
        key_hash = self._hash_key(raw_key)
        key = await self._repo.get_by_hash(key_hash)
        if key is None or not key.is_active:
            return None

        await self._repo.record_usage(key.id)
        return key


def _to_response(key: ApiKey) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        status=key.status.value,
        scopes=key.scopes,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )
