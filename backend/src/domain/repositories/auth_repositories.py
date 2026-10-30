"""Repository interfaces — abstract contracts for data access.

Repositories expose domain entities, never ORM models. The persistence
layer implements these interfaces using SQLAlchemy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.core.enums import ApiKeyStatus, SessionStatus, UserStatus
from src.domain.entities.api_key import ApiKey
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.permission import Permission
from src.domain.entities.preferences import UserPreferences
from src.domain.entities.refresh_token import RefreshToken
from src.domain.entities.role import Role
from src.domain.entities.session import UserSession
from src.domain.entities.tokens import EmailVerificationToken, PasswordResetToken
from src.domain.entities.user import User


class UserRepository(ABC):
    """Abstract repository for ``User`` aggregate."""

    @abstractmethod
    async def create(self, user: User, hashed_password: str) -> User:
        """Create a new user with a hashed password."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Get a user by username (excludes soft-deleted)."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...

    @abstractmethod
    async def soft_delete(self, user_id: UUID) -> bool:
        """Soft-delete a user."""
        ...

    @abstractmethod
    async def list_users(
        self,
        *,
        status: UserStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        """List users with optional status filter and pagination."""
        ...

    @abstractmethod
    async def get_hashed_password(self, user_id: UUID) -> str | None:
        """Get the hashed password for a user."""
        ...

    @abstractmethod
    async def update_password(self, user_id: UUID, hashed_password: str) -> bool:
        """Update a user's hashed password."""
        ...

    @abstractmethod
    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user."""
        ...

    @abstractmethod
    async def revoke_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        ...

    @abstractmethod
    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """Get all roles assigned to a user."""
        ...

    @abstractmethod
    async def count(self, *, status: UserStatus | None = None) -> int:
        """Count users with optional status filter."""
        ...


class RoleRepository(ABC):
    """Abstract repository for ``Role`` entities."""

    @abstractmethod
    async def create(self, role: Role) -> Role:
        ...

    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Role | None:
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None:
        ...

    @abstractmethod
    async def update(self, role: Role) -> Role:
        ...

    @abstractmethod
    async def delete(self, role_id: UUID) -> bool:
        ...

    @abstractmethod
    async def list_roles(self, *, offset: int = 0, limit: int = 50) -> list[Role]:
        ...

    @abstractmethod
    async def grant_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        ...

    @abstractmethod
    async def revoke_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        ...

    @abstractmethod
    async def get_role_permissions(self, role_id: UUID) -> list[Permission]:
        ...


class PermissionRepository(ABC):
    """Abstract repository for ``Permission`` entities."""

    @abstractmethod
    async def create(self, permission: Permission) -> Permission:
        ...

    @abstractmethod
    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Permission | None:
        ...

    @abstractmethod
    async def list_permissions(self, *, offset: int = 0, limit: int = 100) -> list[Permission]:
        ...

    @abstractmethod
    async def delete(self, permission_id: UUID) -> bool:
        ...

    @abstractmethod
    async def get_by_ids(self, permission_ids: list[UUID]) -> list[Permission]:
        ...


class SessionRepository(ABC):
    """Abstract repository for ``UserSession`` entities."""

    @abstractmethod
    async def create(self, session: UserSession) -> UserSession:
        ...

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        ...

    @abstractmethod
    async def get_by_jti(self, jti: str) -> UserSession | None:
        ...

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, *, active_only: bool = True
    ) -> list[UserSession]:
        ...

    @abstractmethod
    async def update(self, session: UserSession) -> UserSession:
        ...

    @abstractmethod
    async def revoke(self, session_id: UUID) -> bool:
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> int:
        ...

    @abstractmethod
    async def update_activity(self, session_id: UUID, ip_address: str | None = None) -> bool:
        ...


class ApiKeyRepository(ABC):
    """Abstract repository for ``ApiKey`` entities."""

    @abstractmethod
    async def create(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    async def get_by_id(self, key_id: UUID) -> ApiKey | None:
        ...

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[ApiKey]:
        ...

    @abstractmethod
    async def update(self, api_key: ApiKey) -> ApiKey:
        ...

    @abstractmethod
    async def revoke(self, key_id: UUID) -> bool:
        ...

    @abstractmethod
    async def record_usage(self, key_id: UUID) -> bool:
        ...


class RefreshTokenRepository(ABC):
    """Abstract repository for ``RefreshToken`` entities."""

    @abstractmethod
    async def create(self, token: RefreshToken) -> RefreshToken:
        ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        ...

    @abstractmethod
    async def revoke(self, token_id: UUID) -> bool:
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> int:
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Delete expired tokens. Returns count of deleted tokens."""
        ...


class PasswordResetTokenRepository(ABC):
    """Abstract repository for ``PasswordResetToken`` entities."""

    @abstractmethod
    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        ...

    @abstractmethod
    async def mark_used(self, token_id: UUID) -> bool:
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        ...


class EmailVerificationTokenRepository(ABC):
    """Abstract repository for ``EmailVerificationToken`` entities."""

    @abstractmethod
    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        ...

    @abstractmethod
    async def mark_used(self, token_id: UUID) -> bool:
        ...

    @abstractmethod
    async def cleanup_expired(self) -> int:
        ...


class UserPreferencesRepository(ABC):
    """Abstract repository for ``UserPreferences`` entities."""

    @abstractmethod
    async def get_or_create(self, user_id: UUID) -> UserPreferences:
        ...

    @abstractmethod
    async def update(self, preferences: UserPreferences) -> UserPreferences:
        ...


class AuditLogRepository(ABC):
    """Abstract repository for ``AuditLog`` entries (append-only)."""

    @abstractmethod
    async def create(self, log: AuditLog) -> AuditLog:
        ...

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        ...

    @abstractmethod
    async def list_recent(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        ...
