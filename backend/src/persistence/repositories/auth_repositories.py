"""SQLAlchemy repository implementations for the IAM domain.

Each repository converts between ORM models and domain entities.
ORM models are never exposed outside this layer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from src.domain.repositories.auth_repositories import (
    ApiKeyRepository,
    AuditLogRepository,
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    SessionRepository,
    UserPreferencesRepository,
    UserRepository,
)
from src.persistence.models.auth import (
    ApiKeyModel,
    AuditLogModel,
    EmailVerificationTokenModel,
    PasswordResetTokenModel,
    PermissionModel,
    RefreshTokenModel,
    RoleModel,
    UserModel,
    UserPreferencesModel,
    UserSessionModel,
    role_permissions,
    user_roles,
)


# ---------------------------------------------------------------------------
# ORM → Domain mappers
# ---------------------------------------------------------------------------
def _map_user(orm: UserModel) -> User:
    return User(
        id=orm.id,
        email=orm.email,
        username=orm.username,
        first_name=orm.first_name,
        last_name=orm.last_name,
        profile_image_url=orm.profile_image_url,
        phone=orm.phone,
        status=UserStatus(orm.status),
        auth_provider=orm.auth_provider,  # stored as string
        timezone=orm.timezone,
        language=orm.language,
        email_verified=orm.email_verified,
        two_factor_enabled=orm.two_factor_enabled,
        role_ids={r.id for r in orm.roles} if orm.roles else set(),
        last_login_at=orm.last_login_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        deleted_at=orm.deleted_at,
    )


def _map_role(orm: RoleModel) -> Role:
    return Role(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        is_system=orm.is_system,
        permission_ids={p.id for p in orm.permissions} if orm.permissions else set(),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _map_permission(orm: PermissionModel) -> Permission:
    return Permission(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        resource=orm.resource,
        action=orm.action,
        is_system=orm.is_system,
        created_at=orm.created_at,
    )


def _map_session(orm: UserSessionModel) -> UserSession:
    return UserSession(
        id=orm.id,
        user_id=orm.user_id,
        token_jti=orm.token_jti,
        refresh_token_id=orm.refresh_token_id,
        device=orm.device,
        browser=orm.browser,
        operating_system=orm.operating_system,
        ip_address=orm.ip_address,
        user_agent=orm.user_agent,
        status=SessionStatus(orm.status),
        created_at=orm.created_at,
        last_activity_at=orm.last_activity_at,
        expires_at=orm.expires_at,
    )


def _map_api_key(orm: ApiKeyModel) -> ApiKey:
    scopes: list[str] = []
    if orm.scopes:
        try:
            scopes = json.loads(orm.scopes)
        except (json.JSONDecodeError, TypeError):
            scopes = []
    return ApiKey(
        id=orm.id,
        user_id=orm.user_id,
        name=orm.name,
        key_hash=orm.key_hash,
        key_prefix=orm.key_prefix,
        status=ApiKeyStatus(orm.status),
        scopes=scopes,
        expires_at=orm.expires_at,
        last_used_at=orm.last_used_at,
        created_at=orm.created_at,
    )


def _map_refresh_token(orm: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=orm.id,
        user_id=orm.user_id,
        token_hash=orm.token_hash,
        session_id=orm.session_id,
        expires_at=orm.expires_at,
        revoked=orm.revoked,
        revoked_at=orm.revoked_at,
        created_at=orm.created_at,
    )


def _map_password_reset_token(orm: PasswordResetTokenModel) -> PasswordResetToken:
    return PasswordResetToken(
        id=orm.id,
        user_id=orm.user_id,
        token_hash=orm.token_hash,
        expires_at=orm.expires_at,
        used=orm.used,
        used_at=orm.used_at,
        created_at=orm.created_at,
    )


def _map_email_verification_token(orm: EmailVerificationTokenModel) -> EmailVerificationToken:
    return EmailVerificationToken(
        id=orm.id,
        user_id=orm.user_id,
        token_hash=orm.token_hash,
        email=orm.email,
        expires_at=orm.expires_at,
        used=orm.used,
        used_at=orm.used_at,
        created_at=orm.created_at,
    )


def _map_preferences(orm: UserPreferencesModel) -> UserPreferences:
    from src.core.enums import ThemePreference

    return UserPreferences(
        user_id=orm.user_id,
        theme=ThemePreference(orm.theme),
        language=orm.language,
        default_ai_model=orm.default_ai_model,
        preferred_llm=orm.preferred_llm,
        preferred_voice=orm.preferred_voice,
        preferred_image_provider=orm.preferred_image_provider,
        preferred_video_provider=orm.preferred_video_provider,
        email_notifications=orm.email_notifications,
        push_notifications=orm.push_notifications,
        updated_at=orm.updated_at,
    )


def _map_audit_log(orm: AuditLogModel) -> AuditLog:
    from src.core.enums import AuditAction

    details: dict[str, object] = {}
    if orm.details:
        try:
            details = json.loads(orm.details)
        except (json.JSONDecodeError, TypeError):
            details = {}
    return AuditLog(
        id=orm.id,
        user_id=orm.user_id,
        action=AuditAction(orm.action),
        resource_type=orm.resource_type,
        resource_id=orm.resource_id,
        ip_address=orm.ip_address,
        user_agent=orm.user_agent,
        details=details,
        correlation_id=orm.correlation_id,
        created_at=orm.created_at,
    )


# ---------------------------------------------------------------------------
# UserRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of ``UserRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User, hashed_password: str) -> User:
        orm = UserModel(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image_url=user.profile_image_url,
            phone=user.phone,
            status=user.status.value,
            auth_provider=user.auth_provider.value,
            timezone=user.timezone,
            language=user.language,
            email_verified=user.email_verified,
            two_factor_enabled=user.two_factor_enabled,
            last_login_at=user.last_login_at,
        )
        self._session.add(orm)
        await self._session.flush()
        # Assign roles if any
        for role_id in user.role_ids:
            await self._session.execute(
                user_roles.insert().values(user_id=orm.id, role_id=role_id)
            )
        await self._session.refresh(orm)
        return _map_user(orm)

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = (
            select(UserModel)
            .where(UserModel.id == user_id, UserModel.is_deleted == False)
            .options(selectinload(UserModel.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_user(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(UserModel)
            .where(UserModel.email == email, UserModel.is_deleted == False)
            .options(selectinload(UserModel.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_user(orm) if orm else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(UserModel)
            .where(UserModel.username == username, UserModel.is_deleted == False)
            .options(selectinload(UserModel.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_user(orm) if orm else None

    async def update(self, user: User) -> User:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_image_url=user.profile_image_url,
                phone=user.phone,
                status=user.status.value,
                timezone=user.timezone,
                language=user.language,
                email_verified=user.email_verified,
                two_factor_enabled=user.two_factor_enabled,
                last_login_at=user.last_login_at,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(UserModel)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        await self._session.refresh(orm)
        return _map_user(orm)

    async def soft_delete(self, user_id: UUID) -> bool:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(
                is_deleted=True,
                deleted_at=datetime.now(timezone.utc),
                status=UserStatus.DELETED.value,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_users(
        self,
        *,
        status: UserStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        stmt = (
            select(UserModel)
            .where(UserModel.is_deleted == False)
            .options(selectinload(UserModel.roles))
            .offset(offset)
            .limit(limit)
            .order_by(UserModel.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(UserModel.status == status.value)
        result = await self._session.execute(stmt)
        return [_map_user(orm) for orm in result.scalars().all()]

    async def get_hashed_password(self, user_id: UUID) -> str | None:
        stmt = select(UserModel.hashed_password).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_password(self, user_id: UUID, hashed_password: str) -> bool:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(hashed_password=hashed_password, updated_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        await self._session.execute(
            user_roles.insert().values(user_id=user_id, role_id=role_id)
        )
        return True

    async def revoke_role(self, user_id: UUID, role_id: UUID) -> bool:
        await self._session.execute(
            delete(user_roles).where(
                user_roles.c.user_id == user_id, user_roles.c.role_id == role_id
            )
        )
        return True

    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        stmt = (
            select(RoleModel)
            .join(user_roles, user_roles.c.role_id == RoleModel.id)
            .where(user_roles.c.user_id == user_id)
            .options(selectinload(RoleModel.permissions))
        )
        result = await self._session.execute(stmt)
        return [_map_role(orm) for orm in result.scalars().all()]

    async def count(self, *, status: UserStatus | None = None) -> int:
        stmt = select(func.count(UserModel.id)).where(UserModel.is_deleted == False)
        if status is not None:
            stmt = stmt.where(UserModel.status == status.value)
        result = await self._session.execute(stmt)
        return result.scalar_one()


# ---------------------------------------------------------------------------
# RoleRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyRoleRepository(RoleRepository):
    """SQLAlchemy implementation of ``RoleRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, role: Role) -> Role:
        orm = RoleModel(
            name=role.name,
            description=role.description,
            is_system=role.is_system,
        )
        self._session.add(orm)
        await self._session.flush()
        for perm_id in role.permission_ids:
            await self._session.execute(
                role_permissions.insert().values(role_id=orm.id, permission_id=perm_id)
            )
        await self._session.refresh(orm)
        return _map_role(orm)

    async def get_by_id(self, role_id: UUID) -> Role | None:
        stmt = (
            select(RoleModel)
            .where(RoleModel.id == role_id, RoleModel.is_deleted == False)
            .options(selectinload(RoleModel.permissions))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_role(orm) if orm else None

    async def get_by_name(self, name: str) -> Role | None:
        stmt = (
            select(RoleModel)
            .where(RoleModel.name == name, RoleModel.is_deleted == False)
            .options(selectinload(RoleModel.permissions))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_role(orm) if orm else None

    async def update(self, role: Role) -> Role:
        stmt = (
            update(RoleModel)
            .where(RoleModel.id == role.id)
            .values(
                name=role.name,
                description=role.description,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(RoleModel)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        await self._session.refresh(orm)
        return _map_role(orm)

    async def delete(self, role_id: UUID) -> bool:
        stmt = update(RoleModel).where(RoleModel.id == role_id).values(
            is_deleted=True, updated_at=datetime.now(timezone.utc)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_roles(self, *, offset: int = 0, limit: int = 50) -> list[Role]:
        stmt = (
            select(RoleModel)
            .where(RoleModel.is_deleted == False)
            .options(selectinload(RoleModel.permissions))
            .offset(offset)
            .limit(limit)
            .order_by(RoleModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_map_role(orm) for orm in result.scalars().all()]

    async def grant_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        await self._session.execute(
            role_permissions.insert().values(role_id=role_id, permission_id=permission_id)
        )
        return True

    async def revoke_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        await self._session.execute(
            delete(role_permissions).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        )
        return True

    async def get_role_permissions(self, role_id: UUID) -> list[Permission]:
        stmt = (
            select(PermissionModel)
            .join(role_permissions, role_permissions.c.permission_id == PermissionModel.id)
            .where(role_permissions.c.role_id == role_id)
        )
        result = await self._session.execute(stmt)
        return [_map_permission(orm) for orm in result.scalars().all()]


# ---------------------------------------------------------------------------
# PermissionRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyPermissionRepository(PermissionRepository):
    """SQLAlchemy implementation of ``PermissionRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, permission: Permission) -> Permission:
        orm = PermissionModel(
            name=permission.name,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
            is_system=permission.is_system,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_permission(orm)

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        stmt = select(PermissionModel).where(PermissionModel.id == permission_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_permission(orm) if orm else None

    async def get_by_name(self, name: str) -> Permission | None:
        stmt = select(PermissionModel).where(PermissionModel.name == name)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_permission(orm) if orm else None

    async def list_permissions(self, *, offset: int = 0, limit: int = 100) -> list[Permission]:
        stmt = select(PermissionModel).offset(offset).limit(limit).order_by(PermissionModel.name.asc())
        result = await self._session.execute(stmt)
        return [_map_permission(orm) for orm in result.scalars().all()]

    async def delete(self, permission_id: UUID) -> bool:
        stmt = delete(PermissionModel).where(PermissionModel.id == permission_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def get_by_ids(self, permission_ids: list[UUID]) -> list[Permission]:
        if not permission_ids:
            return []
        stmt = select(PermissionModel).where(PermissionModel.id.in_(permission_ids))
        result = await self._session.execute(stmt)
        return [_map_permission(orm) for orm in result.scalars().all()]


# ---------------------------------------------------------------------------
# SessionRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of ``SessionRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, session: UserSession) -> UserSession:
        orm = UserSessionModel(
            user_id=session.user_id,
            token_jti=session.token_jti,
            refresh_token_id=session.refresh_token_id,
            device=session.device,
            browser=session.browser,
            operating_system=session.operating_system,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            status=session.status.value,
            expires_at=session.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_session(orm)

    async def get_by_id(self, session_id: UUID) -> UserSession | None:
        stmt = select(UserSessionModel).where(UserSessionModel.id == session_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_session(orm) if orm else None

    async def get_by_jti(self, jti: str) -> UserSession | None:
        stmt = select(UserSessionModel).where(UserSessionModel.token_jti == jti)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_session(orm) if orm else None

    async def list_by_user(
        self, user_id: UUID, *, active_only: bool = True
    ) -> list[UserSession]:
        stmt = select(UserSessionModel).where(UserSessionModel.user_id == user_id)
        if active_only:
            stmt = stmt.where(UserSessionModel.status == SessionStatus.ACTIVE.value)
        stmt = stmt.order_by(UserSessionModel.last_activity_at.desc())
        result = await self._session.execute(stmt)
        return [_map_session(orm) for orm in result.scalars().all()]

    async def update(self, session: UserSession) -> UserSession:
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.id == session.id)
            .values(
                status=session.status.value,
                last_activity_at=session.last_activity_at,
                ip_address=session.ip_address,
            )
            .returning(UserSessionModel)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        await self._session.refresh(orm)
        return _map_session(orm)

    async def revoke(self, session_id: UUID) -> bool:
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.id == session_id)
            .values(status=SessionStatus.REVOKED.value)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        stmt = (
            update(UserSessionModel)
            .where(UserSessionModel.user_id == user_id, UserSessionModel.status == SessionStatus.ACTIVE.value)
            .values(status=SessionStatus.REVOKED.value)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def update_activity(self, session_id: UUID, ip_address: str | None = None) -> bool:
        values: dict[str, object] = {"last_activity_at": datetime.now(timezone.utc)}
        if ip_address:
            values["ip_address"] = ip_address
        stmt = update(UserSessionModel).where(UserSessionModel.id == session_id).values(**values)
        result = await self._session.execute(stmt)
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# ApiKeyRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    """SQLAlchemy implementation of ``ApiKeyRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        orm = ApiKeyModel(
            user_id=api_key.user_id,
            name=api_key.name,
            key_hash=api_key.key_hash,
            key_prefix=api_key.key_prefix,
            status=api_key.status.value,
            scopes=json.dumps(api_key.scopes),
            expires_at=api_key.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_api_key(orm)

    async def get_by_id(self, key_id: UUID) -> ApiKey | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.id == key_id, ApiKeyModel.is_deleted == False)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_api_key(orm) if orm else None

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash, ApiKeyModel.is_deleted == False)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_api_key(orm) if orm else None

    async def list_by_user(self, user_id: UUID) -> list[ApiKey]:
        stmt = (
            select(ApiKeyModel)
            .where(ApiKeyModel.user_id == user_id, ApiKeyModel.is_deleted == False)
            .order_by(ApiKeyModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_map_api_key(orm) for orm in result.scalars().all()]

    async def update(self, api_key: ApiKey) -> ApiKey:
        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == api_key.id)
            .values(
                name=api_key.name,
                status=api_key.status.value,
                scopes=json.dumps(api_key.scopes),
                last_used_at=api_key.last_used_at,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(ApiKeyModel)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        await self._session.refresh(orm)
        return _map_api_key(orm)

    async def revoke(self, key_id: UUID) -> bool:
        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(status=ApiKeyStatus.REVOKED.value, updated_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def record_usage(self, key_id: UUID) -> bool:
        stmt = (
            update(ApiKeyModel)
            .where(ApiKeyModel.id == key_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# RefreshTokenRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    """SQLAlchemy implementation of ``RefreshTokenRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: RefreshToken) -> RefreshToken:
        orm = RefreshTokenModel(
            user_id=token.user_id,
            token_hash=token.token_hash,
            session_id=token.session_id,
            expires_at=token.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_refresh_token(orm)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_refresh_token(orm) if orm else None

    async def revoke(self, token_id: UUID) -> bool:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked == False)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def cleanup_expired(self) -> int:
        stmt = delete(RefreshTokenModel).where(
            RefreshTokenModel.expires_at < datetime.now(timezone.utc)
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ---------------------------------------------------------------------------
# PasswordResetTokenRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    """SQLAlchemy implementation of ``PasswordResetTokenRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        orm = PasswordResetTokenModel(
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_password_reset_token(orm)

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_password_reset_token(orm) if orm else None

    async def mark_used(self, token_id: UUID) -> bool:
        stmt = (
            update(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.id == token_id)
            .values(used=True, used_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def cleanup_expired(self) -> int:
        stmt = delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.expires_at < datetime.now(timezone.utc)
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ---------------------------------------------------------------------------
# EmailVerificationTokenRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyEmailVerificationTokenRepository(EmailVerificationTokenRepository):
    """SQLAlchemy implementation of ``EmailVerificationTokenRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        orm = EmailVerificationTokenModel(
            user_id=token.user_id,
            token_hash=token.token_hash,
            email=token.email,
            expires_at=token.expires_at,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_email_verification_token(orm)

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _map_email_verification_token(orm) if orm else None

    async def mark_used(self, token_id: UUID) -> bool:
        stmt = (
            update(EmailVerificationTokenModel)
            .where(EmailVerificationTokenModel.id == token_id)
            .values(used=True, used_at=datetime.now(timezone.utc))
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def cleanup_expired(self) -> int:
        stmt = delete(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.expires_at < datetime.now(timezone.utc)
        )
        result = await self._session.execute(stmt)
        return result.rowcount


# ---------------------------------------------------------------------------
# UserPreferencesRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyUserPreferencesRepository(UserPreferencesRepository):
    """SQLAlchemy implementation of ``UserPreferencesRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: UUID) -> UserPreferences:
        stmt = select(UserPreferencesModel).where(UserPreferencesModel.user_id == user_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            orm = UserPreferencesModel(user_id=user_id)
            self._session.add(orm)
            await self._session.flush()
            await self._session.refresh(orm)
        return _map_preferences(orm)

    async def update(self, preferences: UserPreferences) -> UserPreferences:
        stmt = (
            update(UserPreferencesModel)
            .where(UserPreferencesModel.user_id == preferences.user_id)
            .values(
                theme=preferences.theme.value,
                language=preferences.language,
                default_ai_model=preferences.default_ai_model,
                preferred_llm=preferences.preferred_llm,
                preferred_voice=preferences.preferred_voice,
                preferred_image_provider=preferences.preferred_image_provider,
                preferred_video_provider=preferences.preferred_video_provider,
                email_notifications=preferences.email_notifications,
                push_notifications=preferences.push_notifications,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(UserPreferencesModel)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one()
        await self._session.refresh(orm)
        return _map_preferences(orm)


# ---------------------------------------------------------------------------
# AuditLogRepository implementation
# ---------------------------------------------------------------------------
class SqlAlchemyAuditLogRepository(AuditLogRepository):
    """SQLAlchemy implementation of ``AuditLogRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: AuditLog) -> AuditLog:
        orm = AuditLogModel(
            user_id=log.user_id,
            action=log.action.value,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=json.dumps(log.details) if log.details else "",
            correlation_id=log.correlation_id,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _map_audit_log(orm)

    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_audit_log(orm) for orm in result.scalars().all()]

    async def list_recent(self, *, offset: int = 0, limit: int = 100) -> list[AuditLog]:
        stmt = (
            select(AuditLogModel)
            .order_by(AuditLogModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_map_audit_log(orm) for orm in result.scalars().all()]
