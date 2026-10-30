"""Permission entity — a granular authorization action in the system."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4


class Permission:
    """A granular permission (e.g. "project.create", "video.publish").

    Permissions are the atomic unit of authorization. They are grouped
    into roles, which are assigned to users.

    Attributes:
        id: UUID primary key.
        name: Unique permission name (dot-separated, e.g. "project.create").
        description: Human-readable description.
        resource: The resource type this permission applies to (e.g. "project").
        action: The action allowed (e.g. "create", "read", "update", "delete").
        is_system: Whether this is a system-defined permission (cannot be deleted).
        created_at: Creation timestamp.
    """

    def __init__(
        self,
        *,
        id: UUID | None = None,
        name: str,
        description: str = "",
        resource: str = "",
        action: str = "",
        is_system: bool = False,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.name = name
        self.description = description
        self.resource = resource
        self.action = action
        self.is_system = is_system
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def from_name(cls, name: str, description: str = "", is_system: bool = False) -> Permission:
        """Create a permission from a dot-separated name.

        Args:
            name: Permission name (e.g. "project.create").
            description: Human-readable description.
            is_system: Whether this is a system permission.

        Returns:
            A new ``Permission`` instance with resource and action parsed.
        """
        parts = name.split(".", 1)
        resource = parts[0] if len(parts) > 0 else ""
        action = parts[1] if len(parts) > 1 else ""
        return cls(
            name=name,
            description=description,
            resource=resource,
            action=action,
            is_system=is_system,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "resource": self.resource,
            "action": self.action,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
