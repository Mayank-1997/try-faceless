"""Role and Permission services — RBAC management.

Handles role/permission CRUD, role-permission assignment, and
user-role assignment. Also provides default role/permission seeding.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth_dtos import (
    CreateRoleRequest,
    PermissionResponse,
    RoleResponse,
)
from src.core.enums import DefaultRoleName
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    PermissionNotFoundError,
    RoleNotFoundError,
    SystemRoleCannotBeDeletedError,
)
from src.domain.entities.permission import Permission
from src.domain.entities.role import Role
from src.persistence.repositories.auth_repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)


# ---------------------------------------------------------------------------
# Default permissions (system-defined, never hardcoded in business logic)
# ---------------------------------------------------------------------------
DEFAULT_PERMISSIONS: list[tuple[str, str]] = [
    ("project.create", "Create new video projects"),
    ("project.read", "View projects"),
    ("project.update", "Modify projects"),
    ("project.delete", "Delete projects"),
    ("video.generate", "Generate video content"),
    ("video.publish", "Publish videos to YouTube"),
    ("settings.update", "Update application settings"),
    ("analytics.view", "View analytics and metrics"),
    ("user.read", "View user profiles"),
    ("user.update", "Update user profiles"),
    ("user.delete", "Delete user accounts"),
    ("role.manage", "Manage roles and permissions"),
    ("api_key.manage", "Manage API keys"),
    ("audit.view", "View audit logs"),
]


class RoleService:
    """Service for role management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logger = get_logger(__name__)
        self._role_repo = SqlAlchemyRoleRepository(session)
        self._permission_repo = SqlAlchemyPermissionRepository(session)
        self._user_repo = SqlAlchemyUserRepository(session)

    async def create_role(self, request: CreateRoleRequest) -> RoleResponse:
        """Create a custom role."""
        role = Role(
            name=request.name,
            description=request.description,
            is_system=False,
            permission_ids=set(request.permission_ids),
        )
        role = await self._role_repo.create(role)
        return await _role_to_response(role, self._permission_repo)

    async def get_role(self, role_id: UUID) -> RoleResponse:
        """Get a role by ID."""
        role = await self._role_repo.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))
        return await _role_to_response(role, self._permission_repo)

    async def list_roles(self) -> list[RoleResponse]:
        """List all roles."""
        roles = await self._role_repo.list_roles(limit=100)
        results: list[RoleResponse] = []
        for role in roles:
            results.append(await _role_to_response(role, self._permission_repo))
        return results

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a role (system roles cannot be deleted)."""
        role = await self._role_repo.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))
        if role.is_system:
            raise SystemRoleCannotBeDeletedError(role.name)
        return await self._role_repo.delete(role_id)

    async def grant_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        """Grant a permission to a role."""
        role = await self._role_repo.get_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id))
        perm = await self._permission_repo.get_by_id(permission_id)
        if perm is None:
            raise PermissionNotFoundError(str(permission_id))
        return await self._role_repo.grant_permission(role_id, permission_id)

    async def revoke_permission(self, role_id: UUID, permission_id: UUID) -> bool:
        """Revoke a permission from a role."""
        return await self._role_repo.revoke_permission(role_id, permission_id)

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user."""
        return await self._user_repo.assign_role(user_id, role_id)

    async def revoke_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        return await self._user_repo.revoke_role(user_id, role_id)


class PermissionService:
    """Service for permission management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._logger = get_logger(__name__)
        self._repo = SqlAlchemyPermissionRepository(session)

    async def list_permissions(self) -> list[PermissionResponse]:
        """List all permissions."""
        permissions = await self._repo.list_permissions(limit=200)
        return [_permission_to_response(p) for p in permissions]

    async def get_permission(self, permission_id: UUID) -> PermissionResponse:
        """Get a permission by ID."""
        perm = await self._repo.get_by_id(permission_id)
        if perm is None:
            raise PermissionNotFoundError(str(permission_id))
        return _permission_to_response(perm)

    async def seed_default_permissions(self) -> int:
        """Seed the default system permissions if they don't exist.

        Returns:
            Number of permissions created.
        """
        count = 0
        for name, description in DEFAULT_PERMISSIONS:
            existing = await self._repo.get_by_name(name)
            if existing is None:
                perm = Permission.from_name(name, description=description, is_system=True)
                await self._repo.create(perm)
                count += 1
        self._logger.info("permissions_seeded", created=count)
        return count


class RolePermissionSeeder:
    """Utility for seeding default roles and their permissions."""

    @staticmethod
    async def seed_defaults(session: AsyncSession) -> None:
        """Seed default roles, permissions, and role-permission mappings."""
        perm_repo = SqlAlchemyPermissionRepository(session)
        role_repo = SqlAlchemyRoleRepository(session)

        # Seed permissions
        perm_map: dict[str, UUID] = {}
        for name, description in DEFAULT_PERMISSIONS:
            existing = await perm_repo.get_by_name(name)
            if existing is None:
                perm = Permission.from_name(name, description=description, is_system=True)
                perm = await perm_repo.create(perm)
                perm_map[name] = perm.id
            else:
                perm_map[name] = existing.id

        # Seed roles
        role_configs: list[tuple[str, str, list[str]]] = [
            (
                DefaultRoleName.SUPER_ADMIN.value,
                "Full system access with all permissions",
                list(perm_map.keys()),
            ),
            (
                DefaultRoleName.ADMIN.value,
                "Administrative access — user and project management",
                [
                    "project.create", "project.read", "project.update", "project.delete",
                    "video.generate", "video.publish",
                    "settings.update", "analytics.view",
                    "user.read", "user.update",
                    "api_key.manage", "audit.view",
                ],
            ),
            (
                DefaultRoleName.CREATOR.value,
                "Content creator — can create and manage own projects",
                [
                    "project.create", "project.read", "project.update", "project.delete",
                    "video.generate", "video.publish",
                    "analytics.view",
                    "api_key.manage",
                ],
            ),
            (
                DefaultRoleName.VIEWER.value,
                "Read-only access to projects and analytics",
                [
                    "project.read",
                    "analytics.view",
                ],
            ),
        ]

        for role_name, description, perm_names in role_configs:
            existing = await role_repo.get_by_name(role_name)
            if existing is None:
                role = Role(
                    name=role_name,
                    description=description,
                    is_system=True,
                    permission_ids={perm_map[n] for n in perm_names if n in perm_map},
                )
                await role_repo.create(role)

        get_logger(__name__).info("default_roles_seeded")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _role_to_response(role: Role, perm_repo: SqlAlchemyPermissionRepository) -> RoleResponse:
    permissions = await perm_repo.get_by_ids(list(role.permission_ids))
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[p.name for p in permissions],
        created_at=role.created_at,
    )


def _permission_to_response(perm: Permission) -> PermissionResponse:
    return PermissionResponse(
        id=perm.id,
        name=perm.name,
        description=perm.description,
        resource=perm.resource,
        action=perm.action,
        is_system=perm.is_system,
    )
