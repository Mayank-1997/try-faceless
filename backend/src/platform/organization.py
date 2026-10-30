"""Organization Management Service.

Supports:
- Organizations
- Teams
- Members
- Roles
- Permissions
- Invitations
- Ownership transfer
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.platform.schema import (
    ActivityFeedItem,
    Approval,
    Comment,
    Invitation,
    InvitationStatus,
    OrgRole,
    Organization,
    ProjectShare,
    TeamMember,
)
from src.core.logging import get_logger


class OrganizationService:
    """Manages organizations, teams, members, and invitations.

    Provides full CRUD for organizations and their members, with
    role-based access control and invitation management.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._orgs: dict[UUID, Organization] = {}
        self._members: dict[UUID, list[TeamMember]] = {}  # org_id -> members
        self._invitations: dict[UUID, Invitation] = {}
        self._shares: list[ProjectShare] = []
        self._comments: list[Comment] = []
        self._approvals: list[Approval] = []
        self._activity: list[ActivityFeedItem] = []

    def create_organization(
        self,
        name: str,
        owner_id: str,
        *,
        slug: str = "",
        max_members: int = 10,
    ) -> Organization:
        """Create a new organization.

        Args:
            name: Organization name.
            owner_id: Owner user ID.
            slug: URL-friendly slug (auto-generated if empty).
            max_members: Maximum member count.

        Returns:
            The created ``Organization``.
        """
        org = Organization(
            name=name,
            slug=slug or name.lower().replace(" ", "-"),
            owner_id=owner_id,
            max_members=max_members,
            member_count=1,
        )
        self._orgs[org.id] = org

        # Add owner as first member
        member = TeamMember(
            org_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER,
        )
        self._members[org.id] = [member]

        self._logger.info("org_created", org_id=str(org.id), name=name, owner=owner_id)
        self._add_activity(org.id, owner_id, "org_created", "organization", str(org.id), f"Created organization '{name}'")
        return org

    def get_organization(self, org_id: UUID) -> Organization | None:
        """Get an organization by ID."""
        return self._orgs.get(org_id)

    def get_organization_by_slug(self, slug: str) -> Organization | None:
        """Get an organization by slug."""
        for org in self._orgs.values():
            if org.slug == slug:
                return org
        return None

    def list_organizations(self, user_id: str | None = None) -> list[Organization]:
        """List organizations, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by membership.

        Returns:
            List of organizations.
        """
        if user_id is None:
            return list(self._orgs.values())
        result: list[Organization] = []
        for org_id, members in self._members.items():
            if any(m.user_id == user_id for m in members):
                org = self._orgs.get(org_id)
                if org:
                    result.append(org)
        return result

    def update_organization(self, org_id: UUID, **kwargs: Any) -> Organization | None:
        """Update an organization.

        Args:
            org_id: The organization ID.
            **kwargs: Fields to update.

        Returns:
            The updated ``Organization`` if found.
        """
        org = self._orgs.get(org_id)
        if org is None:
            return None
        for key, value in kwargs.items():
            if hasattr(org, key):
                setattr(org, key, value)
        self._logger.info("org_updated", org_id=str(org_id))
        return org

    def delete_organization(self, org_id: UUID) -> bool:
        """Delete an organization.

        Args:
            org_id: The organization ID.

        Returns:
            ``True`` if deleted.
        """
        if org_id not in self._orgs:
            return False
        del self._orgs[org_id]
        self._members.pop(org_id, None)
        self._logger.info("org_deleted", org_id=str(org_id))
        return True

    def get_members(self, org_id: UUID) -> list[TeamMember]:
        """Get all members of an organization.

        Args:
            org_id: The organization ID.

        Returns:
            List of ``TeamMember``.
        """
        return list(self._members.get(org_id, []))

    def get_member(self, org_id: UUID, user_id: str) -> TeamMember | None:
        """Get a specific member.

        Args:
            org_id: The organization ID.
            user_id: The user ID.

        Returns:
            The ``TeamMember`` if found.
        """
        for m in self._members.get(org_id, []):
            if m.user_id == user_id:
                return m
        return None

    def add_member(self, org_id: UUID, user_id: str, role: OrgRole = OrgRole.MEMBER, invited_by: str = "") -> TeamMember | None:
        """Add a member to an organization.

        Args:
            org_id: The organization ID.
            user_id: The user ID to add.
            role: The role to assign.
            invited_by: Who invited this member.

        Returns:
            The ``TeamMember`` if added, ``None`` if org not found or already a member.
        """
        org = self._orgs.get(org_id)
        if org is None:
            return None

        if self.get_member(org_id, user_id) is not None:
            return None

        if org.member_count >= org.max_members:
            return None

        member = TeamMember(
            org_id=org_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self._members.setdefault(org_id, []).append(member)
        org.member_count = len(self._members[org_id])

        self._logger.info("member_added", org_id=str(org_id), user_id=user_id, role=role.value)
        self._add_activity(org_id, user_id, "member_added", "organization", str(org_id), f"Member {user_id} added with role {role.value}")
        return member

    def remove_member(self, org_id: UUID, user_id: str) -> bool:
        """Remove a member from an organization.

        Args:
            org_id: The organization ID.
            user_id: The user ID to remove.

        Returns:
            ``True`` if removed.
        """
        members = self._members.get(org_id, [])
        for i, m in enumerate(members):
            if m.user_id == user_id:
                if m.role == OrgRole.OWNER:
                    return False  # Can't remove owner
                members.pop(i)
                org = self._orgs.get(org_id)
                if org:
                    org.member_count = len(members)
                self._logger.info("member_removed", org_id=str(org_id), user_id=user_id)
                return True
        return False

    def update_member_role(self, org_id: UUID, user_id: str, role: OrgRole) -> TeamMember | None:
        """Update a member's role.

        Args:
            org_id: The organization ID.
            user_id: The user ID.
            role: The new role.

        Returns:
            The updated ``TeamMember`` if found.
        """
        member = self.get_member(org_id, user_id)
        if member is None:
            return None
        member.role = role
        self._logger.info("member_role_updated", org_id=str(org_id), user_id=user_id, role=role.value)
        return member

    def transfer_ownership(self, org_id: UUID, new_owner_id: str) -> bool:
        """Transfer organization ownership.

        Args:
            org_id: The organization ID.
            new_owner_id: The user ID of the new owner.

        Returns:
            ``True`` if transfer was successful.
        """
        old_owner = None
        new_member = self.get_member(org_id, new_owner_id)
        if new_member is None:
            return False

        for m in self._members.get(org_id, []):
            if m.role == OrgRole.OWNER:
                old_owner = m
                break

        if old_owner:
            old_owner.role = OrgRole.ADMIN
        new_member.role = OrgRole.OWNER

        org = self._orgs.get(org_id)
        if org:
            org.owner_id = new_owner_id

        self._logger.info("ownership_transferred", org_id=str(org_id), new_owner=new_owner_id)
        return True

    def create_invitation(
        self,
        org_id: UUID,
        email: str,
        role: OrgRole = OrgRole.MEMBER,
        invited_by: str = "",
        expires_in_days: int = 7,
    ) -> Invitation | None:
        """Create an organization invitation.

        Args:
            org_id: The organization ID.
            email: Invitee email.
            role: Role to assign on acceptance.
            invited_by: Who sent the invitation.
            expires_in_days: Days until expiration.

        Returns:
            The ``Invitation`` if created.
        """
        if org_id not in self._orgs:
            return None

        import secrets
        invitation = Invitation(
            org_id=org_id,
            email=email,
            role=role,
            invited_by=invited_by,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
        )
        self._invitations[invitation.id] = invitation
        self._logger.info("invitation_created", org_id=str(org_id), email=email)
        return invitation

    def accept_invitation(self, invitation_id: UUID, user_id: str) -> TeamMember | None:
        """Accept an invitation.

        Args:
            invitation_id: The invitation ID.
            user_id: The accepting user's ID.

        Returns:
            The ``TeamMember`` if accepted.
        """
        invitation = self._invitations.get(invitation_id)
        if invitation is None or not invitation.is_pending:
            return None

        member = self.add_member(invitation.org_id, user_id, invitation.role, invitation.invited_by)
        if member is not None:
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.now(timezone.utc)
            self._logger.info("invitation_accepted", invitation_id=str(invitation_id))
        return member

    def decline_invitation(self, invitation_id: UUID) -> bool:
        """Decline an invitation."""
        invitation = self._invitations.get(invitation_id)
        if invitation is None or not invitation.is_pending:
            return False
        invitation.status = InvitationStatus.DECLINED
        return True

    def revoke_invitation(self, invitation_id: UUID) -> bool:
        """Revoke an invitation."""
        invitation = self._invitations.get(invitation_id)
        if invitation is None:
            return False
        invitation.status = InvitationStatus.REVOKED
        return True

    def get_invitation(self, invitation_id: UUID) -> Invitation | None:
        """Get an invitation by ID."""
        return self._invitations.get(invitation_id)

    def list_invitations(self, org_id: UUID) -> list[Invitation]:
        """List invitations for an organization."""
        return [i for i in self._invitations.values() if i.org_id == org_id]

    # -----------------------------------------------------------------------
    # Team Collaboration
    # -----------------------------------------------------------------------
    def share_project(self, project_id: str, shared_by: str, shared_with: str, role: OrgRole = OrgRole.VIEWER) -> ProjectShare:
        """Share a project with a team member.

        Args:
            project_id: The project ID.
            shared_by: Who is sharing.
            shared_with: Who receives the share.
            role: Access role.

        Returns:
            The ``ProjectShare``.
        """
        share = ProjectShare(
            project_id=project_id,
            shared_by=shared_by,
            shared_with=shared_with,
            role=role,
        )
        self._shares.append(share)
        self._logger.info("project_shared", project_id=project_id, shared_with=shared_with)
        return share

    def get_project_shares(self, project_id: str) -> list[ProjectShare]:
        """Get all shares for a project."""
        return [s for s in self._shares if s.project_id == project_id]

    def add_comment(self, project_id: str, user_id: str, content: str, *, scene_id: str = "") -> Comment:
        """Add a comment to a project or scene.

        Args:
            project_id: The project ID.
            user_id: The commenting user.
            content: Comment content.
            scene_id: Optional scene ID.

        Returns:
            The ``Comment``.
        """
        comment = Comment(
            project_id=project_id,
            scene_id=scene_id,
            user_id=user_id,
            content=content,
        )
        self._comments.append(comment)
        self._logger.info("comment_added", project_id=project_id, user_id=user_id)
        return comment

    def get_comments(self, project_id: str) -> list[Comment]:
        """Get comments for a project."""
        return [c for c in self._comments if c.project_id == project_id]

    def resolve_comment(self, comment_id: UUID) -> bool:
        """Mark a comment as resolved."""
        for c in self._comments:
            if c.id == comment_id:
                c.resolved = True
                return True
        return False

    def create_approval(
        self, project_id: str, requested_by: str, requested_to: str, *, scene_id: str = ""
    ) -> Approval:
        """Create an approval request.

        Args:
            project_id: The project ID.
            requested_by: Who is requesting approval.
            requested_to: Who should approve.
            scene_id: Optional scene ID.

        Returns:
            The ``Approval``.
        """
        approval = Approval(
            project_id=project_id,
            scene_id=scene_id,
            requested_by=requested_by,
            requested_to=requested_to,
        )
        self._approvals.append(approval)
        self._logger.info("approval_created", project_id=project_id)
        return approval

    def resolve_approval(self, approval_id: UUID, status: str, comment: str = "") -> Approval | None:
        """Resolve an approval request.

        Args:
            approval_id: The approval ID.
            status: "approved" or "rejected".
            comment: Optional resolution comment.

        Returns:
            The resolved ``Approval`` if found.
        """
        for a in self._approvals:
            if a.id == approval_id:
                a.status = status
                a.comment = comment
                a.resolved_at = datetime.now(timezone.utc)
                self._logger.info("approval_resolved", approval_id=str(approval_id), status=status)
                return a
        return None

    def get_approvals(self, project_id: str) -> list[Approval]:
        """Get approvals for a project."""
        return [a for a in self._approvals if a.project_id == project_id]

    def get_activity_feed(self, org_id: UUID, limit: int = 50) -> list[ActivityFeedItem]:
        """Get activity feed for an organization.

        Args:
            org_id: The organization ID.
            limit: Maximum items to return.

        Returns:
            List of ``ActivityFeedItem``.
        """
        items = [a for a in self._activity if a.org_id == str(org_id)]
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    def _add_activity(
        self,
        org_id: UUID,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        description: str,
    ) -> None:
        """Add an item to the activity feed."""
        self._activity.append(ActivityFeedItem(
            org_id=str(org_id),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
        ))

    @property
    def org_count(self) -> int:
        """Number of organizations."""
        return len(self._orgs)

    @property
    def invitation_count(self) -> int:
        """Number of invitations."""
        return len(self._invitations)
