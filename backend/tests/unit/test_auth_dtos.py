"""Tests for IAM DTOs — request validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.dto.auth_dtos import (
    ChangePasswordRequest,
    CreateApiKeyRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)


class TestRegisterRequest:
    def test_valid(self):
        req = RegisterRequest(
            email="test@example.com",
            username="testuser",
            password="SecurePass123!",
        )
        assert req.email == "test@example.com"

    def test_weak_password_no_uppercase(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@e.com", username="test", password="lowercase123!"
            )

    def test_weak_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@e.com", username="test", password="Short1!"
            )

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email", username="test", password="SecurePass123!"
            )

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@e.com", username="ab", password="SecurePass123!"
            )

    def test_username_invalid_chars(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="t@e.com", username="test user", password="SecurePass123!"
            )


class TestLoginRequest:
    def test_valid(self):
        req = LoginRequest(email="t@e.com", password="somepass")
        assert req.remember_me is False

    def test_remember_me(self):
        req = LoginRequest(email="t@e.com", password="p", remember_me=True)
        assert req.remember_me is True


class TestResetPasswordRequest:
    def test_valid(self):
        req = ResetPasswordRequest(token="abc", new_password="SecurePass123!")
        assert req.new_password == "SecurePass123!"

    def test_weak_password(self):
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="abc", new_password="weak")


class TestChangePasswordRequest:
    def test_valid(self):
        req = ChangePasswordRequest(
            current_password="OldPass123!",
            new_password="NewPass456!",
        )
        assert req.new_password == "NewPass456!"

    def test_weak_new_password(self):
        with pytest.raises(ValidationError):
            ChangePasswordRequest(
                current_password="old", new_password="weak"
            )


class TestUpdateProfileRequest:
    def test_all_none(self):
        req = UpdateProfileRequest()
        assert req.first_name is None
        assert req.timezone is None

    def test_partial_update(self):
        req = UpdateProfileRequest(first_name="Jane")
        assert req.first_name == "Jane"
        assert req.last_name is None


class TestCreateApiKeyRequest:
    def test_valid(self):
        req = CreateApiKeyRequest(name="My Key", scopes=["project.read"])
        assert req.name == "My Key"
        assert req.expires_in_days is None

    def test_with_expiry(self):
        req = CreateApiKeyRequest(name="K", expires_in_days=30)
        assert req.expires_in_days == 30

    def test_invalid_expiry_too_long(self):
        with pytest.raises(ValidationError):
            CreateApiKeyRequest(name="K", expires_in_days=400)

    def test_invalid_expiry_negative(self):
        with pytest.raises(ValidationError):
            CreateApiKeyRequest(name="K", expires_in_days=0)
