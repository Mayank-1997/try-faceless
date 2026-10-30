"""Password service — hashing, verification, and strength validation.

Uses passlib with bcrypt (already in dependencies). The architecture
is Argon2-ready — switching the hashing scheme only requires changing
the ``CryptContext`` configuration.
"""

from __future__ import annotations

import re
import secrets

from passlib.context import CryptContext

from src.core.logging import get_logger
from src.domain.exceptions.auth_exceptions import WeakPasswordError


class PasswordService:
    """Service for password hashing, verification, and validation.

    Uses bcrypt by default. To switch to Argon2, change the
    ``CryptContext`` schemes list to ``["argon2", "bcrypt"]``.
    """

    def __init__(self) -> None:
        self._pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12,
        )
        self._logger = get_logger(__name__)

    def hash_password(self, password: str) -> str:
        """Hash a plain-text password.

        Args:
            password: The plain-text password.

        Returns:
            The hashed password string.
        """
        return self._pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against a hash.

        Args:
            plain_password: The plain-text password to check.
            hashed_password: The stored hash.

        Returns:
            ``True`` if the password matches, ``False`` otherwise.
        """
        return self._pwd_context.verify(plain_password, hashed_password)

    def validate_strength(self, password: str) -> None:
        """Validate that a password meets strength requirements.

        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (recommended)

        Args:
            password: The password to validate.

        Raises:
            WeakPasswordError: If the password is too weak.
        """
        issues: list[str] = []

        if len(password) < 8:
            issues.append("at least 8 characters")
        if not re.search(r"[A-Z]", password):
            issues.append("at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            issues.append("at least one lowercase letter")
        if not re.search(r"\d", password):
            issues.append("at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            issues.append("at least one special character")

        if issues:
            raise WeakPasswordError(", ".join(issues))

    def generate_temporary_password(self, length: int = 16) -> str:
        """Generate a cryptographically secure temporary password.

        Args:
            length: Desired password length (default 16).

        Returns:
            A random password string.
        """
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if a password hash needs to be rehashed (e.g. after scheme upgrade).

        Args:
            hashed_password: The stored hash.

        Returns:
            ``True`` if the hash should be regenerated.
        """
        return self._pwd_context.needs_update(hashed_password)
