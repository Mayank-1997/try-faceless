"""Tests for the TokenService — JWT creation, validation, rotation."""

from __future__ import annotations

import os
from datetime import timedelta

import pytest

from src.application.services.token_service import TokenService
from src.core.enums import TokenType
from src.core.exceptions import TokenExpiredError
from src.domain.exceptions.auth_exceptions import TokenInvalidError


@pytest.fixture(autouse=True)
def setup_env():
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("ENVIRONMENT", "testing")
    from src.core.config import get_settings
    get_settings.cache_clear()


class TestTokenService:
    @pytest.fixture
    def service(self):
        return TokenService()

    def test_create_access_token(self, service):
        from uuid import uuid4
        user_id = uuid4()
        token, jti, exp = service.create_access_token(
            user_id, "test@example.com", "testuser", roles=["viewer"]
        )
        assert isinstance(token, str)
        assert isinstance(jti, str)
        assert exp is not None

    def test_decode_access_token(self, service):
        from uuid import uuid4
        user_id = uuid4()
        token, _, _ = service.create_access_token(
            user_id, "test@example.com", "testuser", roles=["admin"]
        )
        payload = service.decode_access_token(token)
        assert payload.sub == str(user_id)
        assert payload.email == "test@example.com"
        assert payload.username == "testuser"
        assert payload.type == TokenType.ACCESS.value
        assert "admin" in payload.roles

    def test_create_refresh_token(self, service):
        from uuid import uuid4
        user_id = uuid4()
        token, jti, exp = service.create_refresh_token(user_id)
        assert isinstance(token, str)
        assert isinstance(jti, str)

    def test_decode_refresh_token(self, service):
        from uuid import uuid4
        user_id = uuid4()
        token, _, _ = service.create_refresh_token(user_id)
        payload = service.decode_refresh_token(token)
        assert payload.sub == str(user_id)
        assert payload.type == TokenType.REFRESH.value

    def test_create_token_pair(self, service):
        from uuid import uuid4
        user_id = uuid4()
        pair = service.create_token_pair(
            user_id, "test@example.com", "testuser", roles=["creator"]
        )
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_decode_expired_token(self, service):
        from uuid import uuid4
        user_id = uuid4()
        token, _, _ = service.create_access_token(
            user_id, "test@example.com", "testuser",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(TokenExpiredError):
            service.decode_access_token(token)

    def test_decode_invalid_token(self, service):
        with pytest.raises(TokenInvalidError):
            service.decode_access_token("not.a.valid.token")

    def test_decode_wrong_token_type(self, service):
        from uuid import uuid4
        user_id = uuid4()
        refresh_token, _, _ = service.create_refresh_token(user_id)
        with pytest.raises(TokenInvalidError, match="Expected access"):
            service.decode_access_token(refresh_token)

    def test_hash_token(self, service):
        h1 = service.hash_token("some-token-string")
        h2 = service.hash_token("some-token-string")
        assert h1 == h2
        assert h1 != "some-token-string"
        assert len(h1) == 64  # SHA-256 hex

    def test_generate_random_token(self, service):
        t1 = service.generate_random_token()
        t2 = service.generate_random_token()
        assert t1 != t2
        assert len(t1) > 20

    def test_remember_me_extends_refresh(self, service):
        from uuid import uuid4
        user_id = uuid4()
        normal_pair = service.create_token_pair(user_id, "test@test.com", "test")
        remember_pair = service.create_token_pair(
            user_id, "test@test.com", "test", remember_me=True
        )
        # Remember me refresh token should have a longer expiration
        normal_payload = service.decode_refresh_token(normal_pair.refresh_token)
        remember_payload = service.decode_refresh_token(remember_pair.refresh_token)
        assert remember_payload.exp > normal_payload.exp
