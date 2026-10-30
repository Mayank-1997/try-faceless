"""Authentication service — login, register, refresh, logout, password reset.

Orchestrates the authentication flow using repositories and the
PasswordService / TokenService. This is where business logic lives —
never in API routes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.application.services.password_service import PasswordService
from src.application.services.token_service import TokenPair, TokenService
from src.core.enums import AuditAction, AuthProvider, UserStatus
from src.core.exceptions import InvalidCredentialsError
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    EmailNotVerifiedError,
    EmailVerificationTokenError,
    PasswordResetTokenError,
    TokenRevokedError,
    UserAlreadyExistsError,
    UserNotActiveError,
    WeakPasswordError,
)
from src.domain.entities.refresh_token import RefreshToken
from src.domain.entities.session import UserSession
from src.domain.entities.tokens import EmailVerificationToken, PasswordResetToken
from src.domain.entities.user import User
from src.persistence.repositories.auth_repositories import (
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyUserRepository,
)


class AuthenticationService:
    """Service for authentication operations.

    Handles registration, login, token refresh, logout, password reset,
    and email verification flows.
    """

    def __init__(
        self,
        session: AsyncSession,
        password_service: PasswordService,
        token_service: TokenService,
    ) -> None:
        self._session = session
        self._password_service = password_service
        self._token_service = token_service
        self._logger = get_logger(__name__)

        self._user_repo = SqlAlchemyUserRepository(session)
        self._refresh_token_repo = SqlAlchemyRefreshTokenRepository(session)
        self._session_repo = SqlAlchemySessionRepository(session)
        self._password_reset_repo = SqlAlchemyPasswordResetTokenRepository(session)
        self._email_verification_repo = SqlAlchemyEmailVerificationTokenRepository(session)

    async def register(self, request: RegisterRequest) -> User:
        """Register a new user.

        Args:
            request: Registration data.

        Returns:
            The newly created ``User`` entity.

        Raises:
            UserAlreadyExistsError: If email or username is taken.
            WeakPasswordError: If password is too weak.
        """
        # Check for existing email
        existing = await self._user_repo.get_by_email(request.email)
        if existing:
            raise UserAlreadyExistsError(request.email)

        existing = await self._user_repo.get_by_username(request.username)
        if existing:
            raise UserAlreadyExistsError(request.username)

        # Validate password strength
        self._password_service.validate_strength(request.password)

        # Create user
        user = User(
            email=request.email,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            status=UserStatus.PENDING,
            auth_provider=AuthProvider.LOCAL,
        )
        hashed_password = self._password_service.hash_password(request.password)
        user = await self._user_repo.create(user, hashed_password)

        self._logger.info(
            "user_registered",
            user_id=str(user.id),
            email=user.email,
            username=user.username,
        )
        return user

    async def login(
        self,
        request: LoginRequest,
        *,
        ip_address: str = "",
        user_agent: str = "",
    ) -> AuthResponse:
        """Authenticate a user and issue tokens.

        Args:
            request: Login credentials.
            ip_address: Client IP address.
            user_agent: Client User-Agent string.

        Returns:
            ``AuthResponse`` with tokens and user info.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
            UserNotActiveError: If the account is not active.
        """
        user = await self._user_repo.get_by_email(request.email)
        if user is None:
            raise InvalidCredentialsError()

        hashed_password = await self._user_repo.get_hashed_password(user.id)
        if hashed_password is None:
            raise InvalidCredentialsError()

        if not self._password_service.verify_password(request.password, hashed_password):
            self._logger.warning("login_failed", email=request.email, reason="invalid_password")
            raise InvalidCredentialsError()

        if user.status not in (UserStatus.ACTIVE, UserStatus.PENDING):
            raise UserNotActiveError(user.status.value)

        # Get role names
        roles = await self._user_repo.get_user_roles(user.id)
        role_names = [r.name for r in roles]

        # Create token pair
        token_pair = self._token_service.create_token_pair(
            user_id=user.id,
            email=user.email,
            username=user.username,
            roles=role_names,
            remember_me=request.remember_me,
        )

        # Create session
        access_payload = self._token_service.decode_access_token(token_pair.access_token)
        refresh_payload = self._token_service.decode_refresh_token(token_pair.refresh_token)

        refresh_token_entity = RefreshToken(
            user_id=user.id,
            token_hash=self._token_service.hash_token(token_pair.refresh_token),
            expires_at=datetime.now(timezone.utc)
            + (datetime.now(timezone.utc) - datetime.fromtimestamp(refresh_payload.iat, tz=timezone.utc))
            if False
            else None,  # Will be set from exp
        )
        # Set expiration from token
        refresh_token_entity.expires_at = datetime.fromtimestamp(refresh_payload.exp, tz=timezone.utc)
        refresh_token_entity = await self._refresh_token_repo.create(refresh_token_entity)

        session = UserSession(
            user_id=user.id,
            token_jti=access_payload.jti,
            refresh_token_id=refresh_token_entity.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.expires_at = datetime.fromtimestamp(access_payload.exp, tz=timezone.utc)
        session = await self._session_repo.create(session)

        # Update last login
        user.record_login()
        await self._user_repo.update(user)

        self._logger.info(
            "login_success",
            user_id=str(user.id),
            email=user.email,
            session_id=str(session.id),
        )

        return AuthResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
            user=_user_to_response(user, role_names),
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Rotate a refresh token and issue a new token pair.

        Args:
            refresh_token_str: The raw refresh token string.

        Returns:
            ``TokenResponse`` with new access and refresh tokens.

        Raises:
            TokenRevokedError: If the refresh token has been revoked.
            TokenExpiredError: If the refresh token has expired.
        """
        payload = self._token_service.decode_refresh_token(refresh_token_str)
        token_hash = self._token_service.hash_token(refresh_token_str)

        stored = await self._refresh_token_repo.get_by_hash(token_hash)
        if stored is None:
            raise TokenRevokedError("Refresh token not found")
        if not stored.is_valid:
            raise TokenRevokedError("Refresh token has been revoked or expired")

        # Revoke old token (rotation)
        await self._refresh_token_repo.revoke(stored.id)

        # Get user
        user = await self._user_repo.get_by_id(UUID(payload.sub))
        if user is None:
            raise InvalidCredentialsError("User not found")

        roles = await self._user_repo.get_user_roles(user.id)
        role_names = [r.name for r in roles]

        # Issue new token pair
        token_pair = self._token_service.create_token_pair(
            user_id=user.id,
            email=user.email,
            username=user.username,
            roles=role_names,
        )

        # Store new refresh token
        new_refresh_payload = self._token_service.decode_refresh_token(token_pair.refresh_token)
        new_refresh = RefreshToken(
            user_id=user.id,
            token_hash=self._token_service.hash_token(token_pair.refresh_token),
            session_id=stored.session_id,
            expires_at=datetime.fromtimestamp(new_refresh_payload.exp, tz=timezone.utc),
        )
        await self._refresh_token_repo.create(new_refresh)

        self._logger.info(
            "token_refreshed",
            user_id=str(user.id),
            old_token_id=str(stored.id),
        )

        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=token_pair.expires_in,
        )

    async def logout(self, access_token: str) -> bool:
        """Logout a user by revoking their session and refresh token.

        Args:
            access_token: The access token to revoke.

        Returns:
            ``True`` if logout was successful.
        """
        payload = self._token_service.decode_access_token(access_token)
        session = await self._session_repo.get_by_jti(payload.jti)
        if session:
            await self._session_repo.revoke(session.id)
            if session.refresh_token_id:
                await self._refresh_token_repo.revoke(session.refresh_token_id)

        self._logger.info("logout", user_id=payload.sub, jti=payload.jti)
        return True

    async def logout_all(self, access_token: str) -> int:
        """Revoke all sessions for the current user.

        Args:
            access_token: The access token identifying the user.

        Returns:
            Number of sessions revoked.
        """
        payload = self._token_service.decode_access_token(access_token)
        user_id = UUID(payload.sub)

        count = await self._session_repo.revoke_all_for_user(user_id)
        await self._refresh_token_repo.revoke_all_for_user(user_id)

        self._logger.info("logout_all", user_id=str(user_id), sessions_revoked=count)
        return count

    async def forgot_password(self, email: str) -> str:
        """Generate a password reset token.

        Args:
            email: The email address to reset.

        Returns:
            The raw reset token (to be sent via email — not stored raw).
        """
        user = await self._user_repo.get_by_email(email)
        if user is None:
            # Don't reveal that the email doesn't exist
            self._logger.info("password_reset_requested", email=email, found=False)
            return ""

        raw_token = self._token_service.generate_random_token()
        token_hash = self._token_service.hash_token(raw_token)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
        )
        await self._password_reset_repo.create(reset_token)

        self._logger.info("password_reset_issued", user_id=str(user.id), email=email)
        return raw_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a reset token.

        Args:
            token: The raw reset token.
            new_password: The new plain-text password.

        Returns:
            ``True`` if the password was reset.

        Raises:
            PasswordResetTokenError: If the token is invalid or expired.
            WeakPasswordError: If the password is too weak.
        """
        token_hash = self._token_service.hash_token(token)
        reset_token = await self._password_reset_repo.get_by_hash(token_hash)
        if reset_token is None or not reset_token.is_valid:
            raise PasswordResetTokenError()

        self._password_service.validate_strength(new_password)
        hashed = self._password_service.hash_password(new_password)

        await self._user_repo.update_password(reset_token.user_id, hashed)
        await self._password_reset_repo.mark_used(reset_token.id)

        # Revoke all sessions for this user
        await self._session_repo.revoke_all_for_user(reset_token.user_id)
        await self._refresh_token_repo.revoke_all_for_user(reset_token.user_id)

        self._logger.info("password_reset_complete", user_id=str(reset_token.user_id))
        return True

    async def verify_email(self, token: str) -> bool:
        """Verify a user's email using a verification token.

        Args:
            token: The raw verification token.

        Returns:
            ``True`` if verification succeeded.

        Raises:
            EmailVerificationTokenError: If the token is invalid or expired.
        """
        token_hash = self._token_service.hash_token(token)
        verification = await self._email_verification_repo.get_by_hash(token_hash)
        if verification is None or not verification.is_valid:
            raise EmailVerificationTokenError()

        user = await self._user_repo.get_by_id(verification.user_id)
        if user is None:
            raise EmailVerificationTokenError("User not found")

        user.verify_email()
        if user.status == UserStatus.PENDING:
            user.activate()
        await self._user_repo.update(user)

        await self._email_verification_repo.mark_used(verification.id)

        self._logger.info("email_verified", user_id=str(user.id), email=user.email)
        return True

    async def resend_verification(self, email: str) -> str:
        """Generate a new email verification token.

        Args:
            email: The email to verify.

        Returns:
            The raw verification token (to be sent via email).
        """
        user = await self._user_repo.get_by_email(email)
        if user is None or user.email_verified:
            self._logger.info("verification_resend", email=email, found=not (user is None))
            return ""

        raw_token = self._token_service.generate_random_token()
        token_hash = self._token_service.hash_token(raw_token)

        verification = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            email=user.email,
        )
        await self._email_verification_repo.create(verification)

        self._logger.info("verification_resent", user_id=str(user.id), email=email)
        return raw_token


def _user_to_response(user: User, role_names: list[str]) -> UserResponse:
    """Convert a User entity to a UserResponse DTO."""
    status = user.status.value if hasattr(user.status, "value") else user.status
    auth_provider = user.auth_provider.value if hasattr(user.auth_provider, "value") else user.auth_provider
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        profile_image_url=user.profile_image_url,
        phone=user.phone,
        status=status,
        auth_provider=auth_provider,
        timezone=user.timezone,
        language=user.language,
        email_verified=user.email_verified,
        two_factor_enabled=user.two_factor_enabled,
        roles=role_names,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
