"""Role entity — represents a named set of permissions in the RBAC system."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4


class Role:
    """A named role that groups permissions together.

    Users are assigned roles; roles are assigned permissions.
    This many-to-many indirection allows flexible authorization.

    Attributes:
        id: UUID primary key.
        name: Unique role name (e.g. "admin", "creator").
        description: Human-readable description.
        is_system: Whether this is a system-defined role (cannot be deleted).
        permission_ids: Set of permission UUIDs assigned to this role.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        name: str,
        description: str = "",
        is_system: bool = False,
        permission_ids: set[UUID] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.name = name
        self.description = description
        self.is_system = is_system
        self.permission_ids: set[UUID] = permission_ids or set()
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)

    def grant_permission(self, permission_id: UUID) -> None:
        """Grant a permission to this role."""
        self.permission_ids.add(permission_id)
        self.updated_at = datetime.now(timezone.utc)

    def revoke_permission(self, permission_id: UUID) -> None:
        """Revoke a permission from this role."""
        self.permission_ids.discard(permission_id)
        self.updated_at = datetime.now(timezone.utc)

    def has_permission(self, permission_id: UUID) -> bool:
        """Check if this role has a specific permission."""
        return permission_id in self.permission_ids

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
            "permission_ids": [str(p) for p in self.permission_ids],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
