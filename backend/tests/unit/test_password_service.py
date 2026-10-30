"""Tests for the PasswordService."""

from __future__ import annotations

import pytest

from src.application.services.password_service import PasswordService
from src.domain.exceptions.auth_exceptions import WeakPasswordError


class TestPasswordService:
    @pytest.fixture
    def service(self):
        return PasswordService()

    def test_hash_password(self, service):
        hashed = service.hash_password("SecurePass123!")
        assert hashed != "SecurePass123!"
        assert hashed.startswith("$2")  # bcrypt hash prefix

    def test_verify_password_correct(self, service):
        hashed = service.hash_password("SecurePass123!")
        assert service.verify_password("SecurePass123!", hashed) is True

    def test_verify_password_incorrect(self, service):
        hashed = service.hash_password("SecurePass123!")
        assert service.verify_password("WrongPassword", hashed) is False

    def test_validate_strength_valid(self, service):
        service.validate_strength("SecurePass123!")

    def test_validate_strength_too_short(self, service):
        with pytest.raises(WeakPasswordError, match="8 characters"):
            service.validate_strength("Short1!")

    def test_validate_strength_no_uppercase(self, service):
        with pytest.raises(WeakPasswordError, match="uppercase"):
            service.validate_strength("lowercase123!")

    def test_validate_strength_no_lowercase(self, service):
        with pytest.raises(WeakPasswordError, match="lowercase"):
            service.validate_strength("UPPERCASE123!")

    def test_validate_strength_no_digit(self, service):
        with pytest.raises(WeakPasswordError, match="digit"):
            service.validate_strength("NoDigitsHere!")

    def test_validate_strength_no_special(self, service):
        with pytest.raises(WeakPasswordError, match="special"):
            service.validate_strength("NoSpecial123")

    def test_generate_temporary_password(self, service):
        pwd = service.generate_temporary_password()
        assert len(pwd) == 16
        assert pwd != service.generate_temporary_password()

    def test_generate_temporary_password_custom_length(self, service):
        pwd = service.generate_temporary_password(24)
        assert len(pwd) == 24

    def test_needs_rehash_false(self, service):
        hashed = service.hash_password("SecurePass123!")
        assert service.needs_rehash(hashed) is False
