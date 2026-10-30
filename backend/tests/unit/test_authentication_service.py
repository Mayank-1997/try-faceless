"""Integration tests for the AuthenticationService — register, login, refresh, logout."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import LoginRequest, RegisterRequest
from src.application.services.authentication_service import AuthenticationService
from src.application.services.password_service import PasswordService
from src.application.services.token_service import TokenService
from src.core.exceptions import InvalidCredentialsError
from src.domain.exceptions.auth_exceptions import (
    TokenRevokedError,
    UserAlreadyExistsError,
    WeakPasswordError,
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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def auth_service(db_session):
    return AuthenticationService(db_session, PasswordService(), TokenService())


class TestAuthenticationService:
    async def test_register(self, db_session, auth_service):
        request = RegisterRequest(
            email="newuser@example.com",
            username="newuser",
            password="SecurePass123!",
            first_name="New",
            last_name="User",
        )
        user = await auth_service.register(request)
        await db_session.commit()
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"

    async def test_register_duplicate_email(self, db_session, auth_service):
        request = RegisterRequest(
            email="dup@example.com",
            username="user1",
            password="SecurePass123!",
        )
        await auth_service.register(request)
        await db_session.commit()

        request2 = RegisterRequest(
            email="dup@example.com",
            username="user2",
            password="SecurePass123!",
        )
        with pytest.raises(UserAlreadyExistsError):
            await auth_service.register(request2)

    async def test_register_weak_password(self, db_session, auth_service):
        with pytest.raises(ValidationError):
            request = RegisterRequest(
                email="weak@test.com",
                username="weakuser",
                password="weak",
            )
            await auth_service.register(request)

    async def test_login_success(self, db_session, auth_service):
        # Register first
        reg_request = RegisterRequest(
            email="login@test.com",
            username="loginuser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        # Activate user (normally done via email verification)
        from src.persistence.models.auth import UserModel
        from sqlalchemy import update
        await db_session.execute(
            update(UserModel)
            .where(UserModel.email == "login@test.com")
            .values(status="active")
        )
        await db_session.commit()

        # Login
        login_request = LoginRequest(email="login@test.com", password="SecurePass123!")
        response = await auth_service.login(login_request, ip_address="127.0.0.1")
        await db_session.commit()

        assert response.access_token
        assert response.refresh_token
        assert response.user.email == "login@test.com"

    async def test_login_wrong_password(self, db_session, auth_service):
        reg_request = RegisterRequest(
            email="wrong@test.com",
            username="wronguser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        login_request = LoginRequest(email="wrong@test.com", password="WrongPassword123!")
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login_request)

    async def test_login_nonexistent_user(self, db_session, auth_service):
        login_request = LoginRequest(email="nonexistent@test.com", password="SomePass123!")
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(login_request)

    async def test_refresh_token_rotation(self, db_session, auth_service):
        # Register and activate
        reg_request = RegisterRequest(
            email="refresh@test.com",
            username="refreshuser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        from src.persistence.models.auth import UserModel
        from sqlalchemy import update
        await db_session.execute(
            update(UserModel)
            .where(UserModel.email == "refresh@test.com")
            .values(status="active")
        )
        await db_session.commit()

        # Login
        login_request = LoginRequest(email="refresh@test.com", password="SecurePass123!")
        login_response = await auth_service.login(login_request)
        await db_session.commit()

        # Refresh
        token_response = await auth_service.refresh_token(login_response.refresh_token)
        await db_session.commit()
        assert token_response.access_token
        assert token_response.refresh_token
        assert token_response.refresh_token != login_response.refresh_token

        # Old refresh token should be revoked
        with pytest.raises((TokenRevokedError, InvalidCredentialsError)):
            await auth_service.refresh_token(login_response.refresh_token)

    async def test_logout(self, db_session, auth_service):
        reg_request = RegisterRequest(
            email="logout@test.com",
            username="logoutuser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        from src.persistence.models.auth import UserModel
        from sqlalchemy import update
        await db_session.execute(
            update(UserModel)
            .where(UserModel.email == "logout@test.com")
            .values(status="active")
        )
        await db_session.commit()

        login_request = LoginRequest(email="logout@test.com", password="SecurePass123!")
        login_response = await auth_service.login(login_request)
        await db_session.commit()

        result = await auth_service.logout(login_response.access_token)
        await db_session.commit()
        assert result is True

    async def test_forgot_password(self, db_session, auth_service):
        reg_request = RegisterRequest(
            email="forgot@test.com",
            username="forgotuser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        token = await auth_service.forgot_password("forgot@test.com")
        await db_session.commit()
        assert token  # Raw token returned

    async def test_forgot_password_nonexistent(self, db_session, auth_service):
        token = await auth_service.forgot_password("nonexistent@test.com")
        await db_session.commit()
        assert token == ""  # Don't reveal that email doesn't exist

    async def test_reset_password(self, db_session, auth_service):
        reg_request = RegisterRequest(
            email="reset@test.com",
            username="resetuser",
            password="SecurePass123!",
        )
        await auth_service.register(reg_request)
        await db_session.commit()

        token = await auth_service.forgot_password("reset@test.com")
        await db_session.commit()

        result = await auth_service.reset_password(token, "NewSecurePass456!")
        await db_session.commit()
        assert result is True

        # Login with new password
        from src.persistence.models.auth import UserModel
        from sqlalchemy import update
        await db_session.execute(
            update(UserModel)
            .where(UserModel.email == "reset@test.com")
            .values(status="active")
        )
        await db_session.commit()

        login_request = LoginRequest(email="reset@test.com", password="NewSecurePass456!")
        response = await auth_service.login(login_request)
        await db_session.commit()
        assert response.access_token
