"""Authentication middleware — JWT validation and request context setup.

This middleware intercepts every request, extracts the JWT token from
the Authorization header (or API key), validates it, and sets the
user context on ``request.state`` for downstream dependencies.

Public paths (health, docs, auth endpoints) are exempt.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.application.services.api_key_service import ApiKeyService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.token_service import TokenService
from src.core.exceptions import TokenExpiredError
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    AuthenticationRequiredError,
    TokenInvalidError,
)


# Paths that don't require authentication
PUBLIC_PATHS: list[str] = [
    r"^/health$",
    r"^/docs$",
    r"^/redoc$",
    r"^/openapi\.json$",
    r"^/api/v1/auth/register$",
    r"^/api/v1/auth/login$",
    r"^/api/v1/auth/refresh$",
    r"^/api/v1/auth/forgot-password$",
    r"^/api/v1/auth/reset-password$",
    r"^/api/v1/auth/verify-email$",
    r"^/api/v1/auth/resend-verification$",
]

_COMPILED_PUBLIC_PATHS = [re.compile(p) for p in PUBLIC_PATHS]


def is_public_path(path: str) -> bool:
    """Check if a request path is exempt from authentication."""
    return any(p.match(path) for p in _COMPILED_PUBLIC_PATHS)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens and sets request context.

    Sets ``request.state.user`` with the decoded token payload and
    ``request.state.user_id`` with the user's UUID. If the request
    uses an API key, sets ``request.state.api_key``.
    """

    def __init__(self, app: Any, token_service: TokenService) -> None:
        super().__init__(app)
        self._token_service = token_service
        self._logger = get_logger(__name__)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip authentication for public paths
        if is_public_path(request.url.path):
            return await call_next(request)

        # Try to extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = self._token_service.decode_access_token(token)
                request.state.user = {
                    "id": payload.sub,
                    "email": payload.email,
                    "username": payload.username,
                    "roles": payload.roles,
                    "jti": payload.jti,
                    "permissions": [],  # Will be populated by AuthorizationService when needed
                }
                request.state.user_id = payload.sub
                request.state.auth_method = "jwt"
            except TokenExpiredError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token has expired", "code": "TOKEN_EXPIRED"},
                )
            except TokenInvalidError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token", "code": "TOKEN_INVALID"},
                )

        elif auth_header.startswith("ApiKey "):
            # API key authentication (for SDK/programmatic access)
            raw_key = auth_header[7:]
            # We need a DB session to validate — use the session factory
            from src.infrastructure.database.engine import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                api_key_service = ApiKeyService(session)
                api_key = await api_key_service.validate_key(raw_key)
                if api_key is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid API key", "code": "API_KEY_INVALID"},
                    )
                request.state.user = {
                    "id": str(api_key.user_id),
                    "email": "",
                    "username": "",
                    "roles": [],
                    "jti": "",
                    "permissions": [],
                    "api_key_id": str(api_key.id),
                    "api_key_scopes": api_key.scopes,
                }
                request.state.user_id = str(api_key.user_id)
                request.state.auth_method = "api_key"

        # If no auth header and path requires auth, let the route's
        # dependency handle the 401 (via require_authentication)

        response = await call_next(request)
        return response
