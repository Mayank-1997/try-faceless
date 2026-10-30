"""Tests for the ApiKeyService."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import CreateApiKeyRequest
from src.application.services.api_key_service import ApiKeyService
from src.domain.exceptions.auth_exceptions import ApiKeyNotFoundError
from src.persistence.models.auth import UserModel
from src.persistence.models.base import Base


@pytest.fixture(autouse=True)
def setup_env():
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("ENVIRONMENT", "testing")
    from src.core.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    user = UserModel(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        status="active",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user.id


class TestApiKeyService:
    async def test_create_key(self, db_session, test_user):
        service = ApiKeyService(db_session)
        request = CreateApiKeyRequest(name="My Key", scopes=["project.read"])
        response = await service.create_key(test_user, request)
        assert response.name == "My Key"
        assert response.key.startswith("avs_")
        assert response.key_prefix == response.key[:12]
        assert response.status == "active"
        assert "project.read" in response.scopes

    async def test_list_keys(self, db_session, test_user):
        service = ApiKeyService(db_session)
        await service.create_key(test_user, CreateApiKeyRequest(name="K1"))
        await service.create_key(test_user, CreateApiKeyRequest(name="K2"))
        keys = await service.list_keys(test_user)
        assert len(keys) == 2

    async def test_revoke_key(self, db_session, test_user):
        service = ApiKeyService(db_session)
        response = await service.create_key(test_user, CreateApiKeyRequest(name="K"))
        await service.revoke_key(test_user, response.id)
        keys = await service.list_keys(test_user)
        revoked = [k for k in keys if k.id == response.id][0]
        assert revoked.status == "revoked"

    async def test_revoke_key_not_found(self, db_session, test_user):
        service = ApiKeyService(db_session)
        with pytest.raises(ApiKeyNotFoundError):
            await service.revoke_key(test_user, uuid4())

    async def test_validate_key_valid(self, db_session, test_user):
        service = ApiKeyService(db_session)
        response = await service.create_key(test_user, CreateApiKeyRequest(name="K"))
        api_key = await service.validate_key(response.key)
        assert api_key is not None
        assert api_key.name == "K"

    async def test_validate_key_invalid(self, db_session, test_user):
        service = ApiKeyService(db_session)
        api_key = await service.validate_key("avs_invalid_key")
        assert api_key is None

    async def test_validate_key_revoked(self, db_session, test_user):
        service = ApiKeyService(db_session)
        response = await service.create_key(test_user, CreateApiKeyRequest(name="K"))
        await service.revoke_key(test_user, response.id)
        api_key = await service.validate_key(response.key)
        assert api_key is None
