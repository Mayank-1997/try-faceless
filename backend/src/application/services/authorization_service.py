"""Authorization service — RBAC permission checking.

Provides reusable FastAPI dependencies for authorization:
- require_authentication
- require_role
- require_permission
- require_ownership
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.token_service import TokenService
from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import (
    AuthenticationRequiredError,
    OwnershipRequiredError,
    PermissionDeniedError,
    RoleRequiredError,
)
from src.domain.entities.permission import Permission
from src.domain.entities.role import Role
from src.persistence.repositories.auth_repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)


class AuthorizationService:
    """Service for authorization and RBAC operations.

    Provides methods to check if a user has specific roles or permissions,
    and FastAPI dependency factories for route protection.
    """

    def __init__(self, session: AsyncSession, token_service: TokenService) -> None:
        self._session = session
        self._token_service = token_service
        self._logger = get_logger(__name__)
        self._user_repo = SqlAlchemyUserRepository(session)
        self._role_repo = SqlAlchemyRoleRepository(session)
        self._permission_repo = SqlAlchemyPermissionRepository(session)

    async def get_user_permissions(self, user_id: UUID) -> set[str]:
        """Get all permission names for a user via their roles.

        Args:
            user_id: The user's UUID.

        Returns:
            Set of permission name strings.
        """
        roles = await self._user_repo.get_user_roles(user_id)
        permission_ids: set[UUID] = set()
        for role in roles:
            permission_ids.update(role.permission_ids)

        if not permission_ids:
            return set()

        permissions = await self._permission_repo.get_by_ids(list(permission_ids))
        return {p.name for p in permissions}

    async def get_user_role_names(self, user_id: UUID) -> set[str]:
        """Get all role names for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Set of role name strings.
        """
        roles = await self._user_repo.get_user_roles(user_id)
        return {r.name for r in roles}

    async def has_permission(self, user_id: UUID, permission: str) -> bool:
        """Check if a user has a specific permission.

        Args:
            user_id: The user's UUID.
            permission: Permission name (e.g. "project.create").

        Returns:
            ``True`` if the user has the permission.
        """
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions

    async def has_role(self, user_id: UUID, role_name: str) -> bool:
        """Check if a user has a specific role.

        Args:
            user_id: The user's UUID.
            role_name: Role name string.

        Returns:
            ``True`` if the user has the role.
        """
        role_names = await self.get_user_role_names(user_id)
        return role_name in role_names

    async def has_any_role(self, user_id: UUID, role_names: list[str]) -> bool:
        """Check if a user has any of the specified roles.

        Args:
            user_id: The user's UUID.
            role_names: List of role names to check.

        Returns:
            ``True`` if the user has at least one of the roles.
        """
        user_roles = await self.get_user_role_names(user_id)
        return any(r in user_roles for r in role_names)

    async def check_permission(self, user_id: UUID, permission: str) -> None:
        """Check permission and raise if denied.

        Raises:
            PermissionDeniedError: If the user lacks the permission.
        """
        if not await self.has_permission(user_id, permission):
            raise PermissionDeniedError(permission)

    async def check_role(self, user_id: UUID, role_name: str) -> None:
        """Check role and raise if denied.

        Raises:
            RoleRequiredError: If the user lacks the role.
        """
        if not await self.has_role(user_id, role_name):
            raise RoleRequiredError(role_name)


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------
def require_authentication(request: Request) -> dict[str, object]:
    """FastAPI dependency: require a valid authenticated user.

    Extracts user info from the request state (set by AuthMiddleware).

    Raises:
        AuthenticationRequiredError: If no authenticated user is found.
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise AuthenticationRequiredError()
    return user


def require_role(role_name: str):
    """FastAPI dependency factory: require a specific role.

    Usage::

        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
        async def admin_endpoint():
            ...

    Args:
        role_name: The required role name.

    Returns:
        A FastAPI dependency function.
    """

    def _check(request: Request) -> dict[str, object]:
        user = require_authentication(request)
        roles: list[str] = user.get("roles", [])
        if role_name not in roles and "super_admin" not in roles:
            raise RoleRequiredError(role_name)
        return user

    return _check


def require_permission(permission: str):
    """FastAPI dependency factory: require a specific permission.

    Usage::

        @router.post("/projects", dependencies=[Depends(require_permission("project.create"))])
        async def create_project():
            ...

    Args:
        permission: The required permission name.

    Returns:
        A FastAPI dependency function.
    """

    def _check(request: Request) -> dict[str, object]:
        user = require_authentication(request)
        permissions: set[str] = set(user.get("permissions", []))
        if permission not in permissions:
            raise PermissionDeniedError(permission)
        return user

    return _check


def require_ownership(resource_owner_id: str, current_user_id: str) -> None:
    """Check that the current user owns the resource.

    Super admins bypass ownership checks.

    Args:
        resource_owner_id: UUID string of the resource owner.
        current_user_id: UUID string of the current user.

    Raises:
        OwnershipRequiredError: If the user doesn't own the resource.
    """
    if resource_owner_id != current_user_id:
        raise OwnershipRequiredError("resource", resource_owner_id)
