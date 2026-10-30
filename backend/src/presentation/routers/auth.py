"""Auth router — authentication endpoints.

POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
POST /auth/logout-all
POST /auth/forgot-password
POST /auth/reset-password
POST /auth/verify-email
POST /auth/resend-verification
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    ResendVerificationRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from src.application.services.authentication_service import AuthenticationService
from src.application.services.password_service import PasswordService
from src.application.services.token_service import TokenService
from src.core.enums import AuditAction
from src.infrastructure.database.engine import get_db_session

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_services(db: AsyncSession = Depends(get_db_session)):
    """Create services for this request."""
    password_service = PasswordService()
    token_service = TokenService()
    auth_service = AuthenticationService(db, password_service, token_service)
    return auth_service, token_service


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user account."""
    auth_service, _ = _get_services(db)
    user = await auth_service.register(request)
    await db.commit()
    return MessageResponse(
        message=f"User registered successfully. Please verify your email: {user.email}"
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email and password."""
    auth_service, _ = _get_services(db)
    ip = http_request.client.host if http_request.client else ""
    user_agent = http_request.headers.get("User-Agent", "")
    response = await auth_service.login(request, ip_address=ip, user_agent=user_agent)
    await db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Refresh an expired access token."""
    auth_service, _ = _get_services(db)
    response = await auth_service.refresh_token(request.refresh_token)
    await db.commit()
    return response


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Logout the current user (revoke session and refresh token)."""
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return LogoutResponse()
    token = auth_header[7:]
    auth_service, _ = _get_services(db)
    await auth_service.logout(token)
    await db.commit()
    return LogoutResponse()


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    http_request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke all sessions for the current user."""
    auth_header = http_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return MessageResponse(message="No active session")
    token = auth_header[7:]
    auth_service, _ = _get_services(db)
    count = await auth_service.logout_all(token)
    await db.commit()
    return MessageResponse(message=f"Revoked {count} session(s)")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Request a password reset token."""
    auth_service, _ = _get_services(db)
    token = await auth_service.forgot_password(request.email)
    await db.commit()
    # In production, send `token` via email. For now, return a generic message.
    return MessageResponse(
        message="If the email exists, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Reset password using a reset token."""
    auth_service, _ = _get_services(db)
    await auth_service.reset_password(request.token, request.new_password)
    await db.commit()
    return MessageResponse(message="Password reset successfully.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify email using a verification token."""
    auth_service, _ = _get_services(db)
    await auth_service.verify_email(request.token)
    await db.commit()
    return MessageResponse(message="Email verified successfully.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Resend email verification token."""
    auth_service, _ = _get_services(db)
    token = await auth_service.resend_verification(request.email)
    await db.commit()
    return MessageResponse(
        message="If the email exists and is unverified, a new verification link has been sent."
    )
