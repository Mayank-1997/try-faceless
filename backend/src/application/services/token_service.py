"""Token service — JWT creation, validation, and rotation.

Uses PyJWT (already in dependencies) to issue and verify JWT tokens.
Access tokens are short-lived; refresh tokens are long-lived and
rotated on each use.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.enums import TokenType
from src.core.exceptions import (
    TokenExpiredError,
)
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    TokenInvalidError,
)


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: str  # user_id
    email: str = ""
    username: str = ""
    type: str  # "access" or "refresh"
    jti: str  # unique token ID
    iat: int  # issued at (unix timestamp)
    exp: int  # expiration (unix timestamp)
    roles: list[str] = []
    sid: str | None = None  # session ID (refresh tokens only)


class TokenPair(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token lifetime in seconds


class TokenService:
    """Service for JWT token creation, validation, and rotation.

    Access tokens are short-lived (default 30 minutes).
    Refresh tokens are long-lived (default 7 days) and rotated on each use.
    """

    def __init__(self) -> None:
        self._settings = get_settings().jwt
        self._logger = get_logger(__name__)

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        username: str,
        roles: list[str] | None = None,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str, datetime]:
        """Create a JWT access token.

        Args:
            user_id: User UUID.
            email: User email.
            username: User username.
            roles: List of role names.
            expires_delta: Custom expiration time. Defaults to config.

        Returns:
            Tuple of (token_string, jti, expiration_datetime).
        """
        expire_delta = expires_delta or timedelta(minutes=self._settings.access_token_expire_minutes)
        expire_at = datetime.now(timezone.utc) + expire_delta
        jti = secrets.token_urlsafe(16)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "email": email,
            "username": username,
            "type": TokenType.ACCESS.value,
            "jti": jti,
            "iat": datetime.now(timezone.utc),
            "exp": expire_at,
            "roles": roles or [],
        }

        token = jwt.encode(payload, self._settings.secret_key, algorithm=self._settings.algorithm)
        return token, jti, expire_at

    def create_refresh_token(
        self,
        user_id: UUID,
        session_id: UUID | None = None,
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str, datetime]:
        """Create a JWT refresh token.

        Args:
            user_id: User UUID.
            session_id: Associated session UUID.
            expires_delta: Custom expiration time. Defaults to config.

        Returns:
            Tuple of (token_string, jti, expiration_datetime).
        """
        expire_delta = expires_delta or timedelta(days=self._settings.refresh_token_expire_days)
        expire_at = datetime.now(timezone.utc) + expire_delta
        jti = secrets.token_urlsafe(16)

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "type": TokenType.REFRESH.value,
            "jti": jti,
            "iat": datetime.now(timezone.utc),
            "exp": expire_at,
        }
        if session_id:
            payload["sid"] = str(session_id)

        token = jwt.encode(payload, self._settings.secret_key, algorithm=self._settings.algorithm)
        return token, jti, expire_at

    def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        username: str,
        roles: list[str] | None = None,
        remember_me: bool = False,
    ) -> TokenPair:
        """Create an access + refresh token pair.

        Args:
            user_id: User UUID.
            email: User email.
            username: User username.
            roles: List of role names.
            remember_me: If True, extends refresh token lifetime.

        Returns:
            ``TokenPair`` with both tokens.
        """
        access_token, _, _ = self.create_access_token(user_id, email, username, roles)
        refresh_delta = None
        if remember_me:
            refresh_delta = timedelta(days=30)
        refresh_token, _, _ = self.create_refresh_token(user_id, expires_delta=refresh_delta)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.access_token_expire_minutes * 60,
        )

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT token.

        Args:
            token: The JWT token string.

        Returns:
            ``TokenPayload`` with decoded claims.

        Raises:
            TokenExpiredError: If the token has expired.
            TokenInvalidError: If the token is invalid or malformed.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.secret_key,
                algorithms=[self._settings.algorithm],
            )
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as exc:
            raise TokenInvalidError(str(exc))

    def decode_access_token(self, token: str) -> TokenPayload:
        """Decode an access token and verify its type.

        Raises:
            TokenInvalidError: If the token is not an access token.
        """
        payload = self.decode_token(token)
        if payload.type != TokenType.ACCESS.value:
            raise TokenInvalidError("Expected access token")
        return payload

    def decode_refresh_token(self, token: str) -> TokenPayload:
        """Decode a refresh token and verify its type.

        Raises:
            TokenInvalidError: If the token is not a refresh token.
        """
        payload = self.decode_token(token)
        if payload.type != TokenType.REFRESH.value:
            raise TokenInvalidError("Expected refresh token")
        return payload

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage (SHA-256).

        Used for refresh tokens, API keys, and verification tokens.
        We never store raw tokens — only their hashes.

        Args:
            token: The raw token string.

        Returns:
            SHA-256 hex digest.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_random_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token.

        Args:
            length: Token length in bytes (default 32).

        Returns:
            URL-safe random token string.
        """
        return secrets.token_urlsafe(length)
