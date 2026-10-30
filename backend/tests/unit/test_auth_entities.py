"""Tests for IAM domain entities."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from src.core.enums import (
    ApiKeyStatus,
    AuditAction,
    AuthProvider,
    SessionStatus,
    ThemePreference,
    UserStatus,
)
from src.domain.entities.api_key import ApiKey
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.permission import Permission
from src.domain.entities.preferences import UserPreferences
from src.domain.entities.refresh_token import RefreshToken
from src.domain.entities.role import Role
from src.domain.entities.session import UserSession
from src.domain.entities.tokens import EmailVerificationToken, PasswordResetToken
from src.domain.entities.user import User


class TestUser:
    def test_creation_defaults(self):
        user = User(email="test@example.com", username="testuser")
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.status == UserStatus.PENDING
        assert user.auth_provider == AuthProvider.LOCAL
        assert user.email_verified is False
        assert user.two_factor_enabled is False
        assert user.role_ids == set()
        assert user.is_active is False
        assert user.is_deleted is False

    def test_full_name(self):
        user = User(email="t@e.com", username="t", first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"

    def test_full_name_empty(self):
        user = User(email="t@e.com", username="t")
        assert user.full_name == ""

    def test_activate(self):
        user = User(email="t@e.com", username="t")
        user.activate()
        assert user.is_active is True

    def test_deactivate(self):
        user = User(email="t@e.com", username="t", status=UserStatus.ACTIVE)
        user.deactivate()
        assert user.status == UserStatus.INACTIVE

    def test_suspend(self):
        user = User(email="t@e.com", username="t")
        user.suspend()
        assert user.status == UserStatus.SUSPENDED

    def test_lock(self):
        user = User(email="t@e.com", username="t")
        user.lock()
        assert user.is_locked is True

    def test_soft_delete(self):
        user = User(email="t@e.com", username="t")
        user.soft_delete()
        assert user.is_deleted is True
        assert user.status == UserStatus.DELETED
        assert user.deleted_at is not None

    def test_verify_email(self):
        user = User(email="t@e.com", username="t")
        user.verify_email()
        assert user.email_verified is True

    def test_record_login(self):
        user = User(email="t@e.com", username="t")
        assert user.last_login_at is None
        user.record_login()
        assert user.last_login_at is not None

    def test_update_profile(self):
        user = User(email="t@e.com", username="t")
        user.update_profile(first_name="Jane", timezone="America/New_York")
        assert user.first_name == "Jane"
        assert user.timezone == "America/New_York"

    def test_assign_and_revoke_role(self):
        role_id = uuid4()
        user = User(email="t@e.com", username="t")
        user.assign_role(role_id)
        assert user.has_role(role_id) is True
        user.revoke_role(role_id)
        assert user.has_role(role_id) is False

    def test_to_dict(self):
        user = User(email="t@e.com", username="t", first_name="A")
        d = user.to_dict()
        assert d["email"] == "t@e.com"
        assert d["status"] == "pending"


class TestRole:
    def test_creation(self):
        role = Role(name="admin", description="Administrator")
        assert role.name == "admin"
        assert role.is_system is False
        assert role.permission_ids == set()

    def test_grant_revoke_permission(self):
        perm_id = uuid4()
        role = Role(name="editor")
        role.grant_permission(perm_id)
        assert role.has_permission(perm_id) is True
        role.revoke_permission(perm_id)
        assert role.has_permission(perm_id) is False


class TestPermission:
    def test_creation(self):
        perm = Permission(name="project.create", description="Create projects")
        assert perm.name == "project.create"
        assert perm.resource == ""
        assert perm.action == ""

    def test_from_name(self):
        perm = Permission.from_name("video.publish", "Publish videos")
        assert perm.resource == "video"
        assert perm.action == "publish"


class TestUserSession:
    def test_creation(self):
        session = UserSession(user_id=uuid4(), token_jti="test-jti")
        assert session.is_active is True
        assert session.is_expired is False

    def test_revoke(self):
        session = UserSession(user_id=uuid4(), token_jti="jti")
        session.revoke()
        assert session.is_active is False

    def test_expired(self):
        from datetime import timedelta
        session = UserSession(
            user_id=uuid4(),
            token_jti="jti",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert session.is_expired is True

    def test_update_activity(self):
        session = UserSession(user_id=uuid4(), token_jti="jti")
        old_activity = session.last_activity_at
        session.update_activity(ip_address="10.0.0.1")
        assert session.ip_address == "10.0.0.1"
        assert session.last_activity_at >= old_activity


class TestApiKey:
    def test_creation(self):
        key = ApiKey(
            user_id=uuid4(),
            name="My Key",
            key_hash="abc123",
            key_prefix="avs_test123",
        )
        assert key.is_active is True
        assert key.status == ApiKeyStatus.ACTIVE

    def test_revoke(self):
        key = ApiKey(user_id=uuid4(), name="K", key_hash="h", key_prefix="p")
        key.revoke()
        assert key.is_active is False

    def test_expired(self):
        from datetime import timedelta
        key = ApiKey(
            user_id=uuid4(),
            name="K",
            key_hash="h",
            key_prefix="p",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert key.is_active is False

    def test_has_scope_no_restriction(self):
        key = ApiKey(user_id=uuid4(), name="K", key_hash="h", key_prefix="p")
        assert key.has_scope("anything") is True

    def test_has_scope_with_restriction(self):
        key = ApiKey(
            user_id=uuid4(), name="K", key_hash="h", key_prefix="p",
            scopes=["project.read"],
        )
        assert key.has_scope("project.read") is True
        assert key.has_scope("project.create") is False


class TestRefreshToken:
    def test_valid(self):
        token = RefreshToken(user_id=uuid4(), token_hash="h")
        assert token.is_valid is True

    def test_revoked(self):
        token = RefreshToken(user_id=uuid4(), token_hash="h")
        token.revoke()
        assert token.is_valid is False

    def test_expired(self):
        from datetime import timedelta
        token = RefreshToken(
            user_id=uuid4(),
            token_hash="h",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert token.is_valid is False


class TestPasswordResetToken:
    def test_valid(self):
        token = PasswordResetToken(user_id=uuid4(), token_hash="h")
        assert token.is_valid is True

    def test_used(self):
        token = PasswordResetToken(user_id=uuid4(), token_hash="h")
        token.mark_used()
        assert token.is_valid is False


class TestEmailVerificationToken:
    def test_valid(self):
        token = EmailVerificationToken(
            user_id=uuid4(), token_hash="h", email="t@e.com"
        )
        assert token.is_valid is True

    def test_used(self):
        token = EmailVerificationToken(
            user_id=uuid4(), token_hash="h", email="t@e.com"
        )
        token.mark_used()
        assert token.is_valid is False


class TestUserPreferences:
    def test_creation(self):
        prefs = UserPreferences(user_id=uuid4())
        assert prefs.theme == ThemePreference.SYSTEM
        assert prefs.email_notifications is True


class TestAuditLog:
    def test_creation(self):
        log = AuditLog(action=AuditAction.LOGIN, user_id=uuid4())
        assert log.action == AuditAction.LOGIN
        assert log.details == {}

    def test_with_details(self):
        log = AuditLog(
            action=AuditAction.LOGIN_FAILED,
            details={"reason": "bad password"},
        )
        assert log.details["reason"] == "bad password"
