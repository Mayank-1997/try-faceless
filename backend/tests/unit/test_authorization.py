"""Tests for the AuthorizationService — RBAC permission checking."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.authorization_service import (
    AuthorizationService,
    require_authentication,
    require_permission,
    require_role,
)
from src.application.services.token_service import TokenService
from src.domain.exceptions.auth_exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    RoleRequiredError,
)
from src.domain.entities.permission import Permission
from src.domain.entities.role import Role
from src.domain.entities.user import User
from src.persistence.models.auth import (
    PermissionModel,
    RoleModel,
    UserModel,
    role_permissions,
    user_roles,
)
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
    """Create an in-memory SQLite session for testing."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


class TestAuthorizationService:
    @pytest.fixture
    async def seeded_data(self, db_session):
        """Seed a user, role, and permission for testing."""
        # Create permission
        perm = PermissionModel(
            name="project.create",
            description="Create projects",
            resource="project",
            action="create",
            is_system=True,
        )
        db_session.add(perm)
        await db_session.flush()

        # Create role with permission
        role = RoleModel(
            name="creator",
            description="Content creator",
            is_system=False,
        )
        db_session.add(role)
        await db_session.flush()

        # Link role to permission
        await db_session.execute(
            role_permissions.insert().values(role_id=role.id, permission_id=perm.id)
        )

        # Create user
        user = UserModel(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Link user to role
        await db_session.execute(
            user_roles.insert().values(user_id=user.id, role_id=role.id)
        )
        await db_session.commit()

        return user.id, role.id, perm.id

    async def test_get_user_permissions(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        permissions = await service.get_user_permissions(user_id)
        assert "project.create" in permissions

    async def test_get_user_role_names(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        roles = await service.get_user_role_names(user_id)
        assert "creator" in roles

    async def test_has_permission_true(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        assert await service.has_permission(user_id, "project.create") is True

    async def test_has_permission_false(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        assert await service.has_permission(user_id, "project.delete") is False

    async def test_has_role_true(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        assert await service.has_role(user_id, "creator") is True

    async def test_has_role_false(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        assert await service.has_role(user_id, "admin") is False

    async def test_has_any_role(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        assert await service.has_any_role(user_id, ["admin", "creator"]) is True
        assert await service.has_any_role(user_id, ["admin", "viewer"]) is False

    async def test_check_permission_raises(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        with pytest.raises(PermissionDeniedError):
            await service.check_permission(user_id, "project.delete")

    async def test_check_role_raises(self, db_session, seeded_data):
        user_id, _, _ = seeded_data
        service = AuthorizationService(db_session, TokenService())
        with pytest.raises(RoleRequiredError):
            await service.check_role(user_id, "admin")

    async def test_no_permissions_for_user_without_roles(self, db_session):
        # Create user without roles
        user = UserModel(
            email="noroles@test.com",
            username="noroles",
            hashed_password="h",
            status="active",
        )
        db_session.add(user)
        await db_session.commit()

        service = AuthorizationService(db_session, TokenService())
        permissions = await service.get_user_permissions(user.id)
        assert permissions == set()


class TestFastAPIDependencies:
    def test_require_authentication_no_user(self):
        from fastapi import Request
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {},
        }
        request = StarletteRequest(scope)
        with pytest.raises(AuthenticationRequiredError):
            require_authentication(request)

    def test_require_authentication_with_user(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "roles": ["viewer"]}},
        }
        request = StarletteRequest(scope)
        user = require_authentication(request)
        assert user["id"] == "123"

    def test_require_role_with_correct_role(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "roles": ["admin"]}},
        }
        request = StarletteRequest(scope)
        checker = require_role("admin")
        user = checker(request)
        assert user["id"] == "123"

    def test_require_role_with_wrong_role(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "roles": ["viewer"]}},
        }
        request = StarletteRequest(scope)
        checker = require_role("admin")
        with pytest.raises(RoleRequiredError):
            checker(request)

    def test_require_role_super_admin_bypass(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "roles": ["super_admin"]}},
        }
        request = StarletteRequest(scope)
        checker = require_role("admin")
        user = checker(request)
        assert user["id"] == "123"

    def test_require_permission_with_correct_permission(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "permissions": ["project.create"]}},
        }
        request = StarletteRequest(scope)
        checker = require_permission("project.create")
        user = checker(request)
        assert user["id"] == "123"

    def test_require_permission_with_wrong_permission(self):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": Headers({}).raw,
            "query_string": b"",
            "state": {"user": {"id": "123", "permissions": ["project.read"]}},
        }
        request = StarletteRequest(scope)
        checker = require_permission("project.create")
        with pytest.raises(PermissionDeniedError):
            checker(request)
