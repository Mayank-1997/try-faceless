"""IAM DTOs — request and response data transfer objects.

These Pydantic models validate input and shape output. ORM models
are never exposed through these DTOs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth request DTOs
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    """POST /auth/register request body."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class RefreshTokenRequest(BaseModel):
    """POST /auth/refresh request body."""

    refresh_token: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """POST /auth/forgot-password request body."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """POST /auth/reset-password request body."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class VerifyEmailRequest(BaseModel):
    """POST /auth/verify-email request body."""

    token: str = Field(..., min_length=1)


class ResendVerificationRequest(BaseModel):
    """POST /auth/resend-verification request body."""

    email: EmailStr


# ---------------------------------------------------------------------------
# Auth response DTOs
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    """JWT token pair returned after login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class AuthResponse(BaseModel):
    """Full authentication response with user info."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class LogoutResponse(BaseModel):
    """Logout confirmation."""

    message: str = "Successfully logged out"


# ---------------------------------------------------------------------------
# User DTOs
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    """Public user representation (no sensitive data)."""

    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: str
    profile_image_url: str | None = None
    phone: str | None = None
    status: str
    auth_provider: str
    timezone: str
    language: str
    email_verified: bool
    two_factor_enabled: bool
    roles: list[str] = Field(default_factory=list)
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of users."""

    users: list[UserResponse]
    total: int
    offset: int
    limit: int


class UpdateProfileRequest(BaseModel):
    """PATCH /users/me request body."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    profile_image_url: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    timezone: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=10)


class ChangePasswordRequest(BaseModel):
    """PATCH /users/password request body."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserPreferencesResponse(BaseModel):
    """User preferences response."""

    theme: str
    language: str
    default_ai_model: str
    preferred_llm: str
    preferred_voice: str
    preferred_image_provider: str
    preferred_video_provider: str
    email_notifications: bool
    push_notifications: bool


class UpdatePreferencesRequest(BaseModel):
    """Update user preferences."""

    theme: str | None = None
    language: str | None = None
    default_ai_model: str | None = None
    preferred_llm: str | None = None
    preferred_voice: str | None = None
    preferred_image_provider: str | None = None
    preferred_video_provider: str | None = None
    email_notifications: bool | None = None
    push_notifications: bool | None = None


# ---------------------------------------------------------------------------
# API Key DTOs
# ---------------------------------------------------------------------------
class ApiKeyResponse(BaseModel):
    """API key response (never includes the raw key)."""

    id: UUID
    name: str
    key_prefix: str
    status: str
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime


class ApiKeyWithSecretResponse(ApiKeyResponse):
    """API key response including the raw key (only at creation time)."""

    key: str = Field(..., description="Raw API key — shown only once")


class CreateApiKeyRequest(BaseModel):
    """POST /api-keys request body."""

    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class UpdateApiKeyRequest(BaseModel):
    """PATCH /api-keys/{id} request body."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    scopes: list[str] | None = None


# ---------------------------------------------------------------------------
# Session DTOs
# ---------------------------------------------------------------------------
class SessionResponse(BaseModel):
    """User session response."""

    id: UUID
    device: str
    browser: str
    operating_system: str
    ip_address: str
    status: str
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime | None = None
    is_current: bool = False


class SessionListResponse(BaseModel):
    """List of user sessions."""

    sessions: list[SessionResponse]
    total: int


# ---------------------------------------------------------------------------
# Role / Permission DTOs
# ---------------------------------------------------------------------------
class RoleResponse(BaseModel):
    """Role response."""

    id: UUID
    name: str
    description: str
    is_system: bool
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime


class PermissionResponse(BaseModel):
    """Permission response."""

    id: UUID
    name: str
    description: str
    resource: str
    action: str
    is_system: bool


class CreateRoleRequest(BaseModel):
    """Create a custom role."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    permission_ids: list[UUID] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Audit DTOs
# ---------------------------------------------------------------------------
class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    id: UUID
    user_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Generic message response
# ---------------------------------------------------------------------------
class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# Update forward refs
AuthResponse.model_rebuild()
