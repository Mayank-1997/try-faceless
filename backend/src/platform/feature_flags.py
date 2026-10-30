"""Feature Flag Service.

Supports:
- Feature toggles
- Beta features
- User-level features
- Organization-level features
- A/B testing
- Future experimentation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.platform.schema import FeatureFlag, FeatureFlagScope, FeatureFlagType
from src.core.logging import get_logger


class FeatureFlagService:
    """Manages feature flags with multi-scope support.

    Supports global, user-level, organization-level, and plan-level
    feature flags with boolean, percentage, and variant types.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._flags: dict[str, FeatureFlag] = {}

    def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag.

        Args:
            flag: The flag to create.

        Returns:
            The created flag.

        Raises:
            ValueError: If a flag with the same key already exists.
        """
        if flag.key in self._flags:
            raise ValueError(f"Feature flag '{flag.key}' already exists")

        self._flags[flag.key] = flag
        self._logger.info("flag_created", key=flag.key, scope=flag.scope.value)
        return flag

    def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag by key.

        Args:
            key: The flag key.

        Returns:
            The ``FeatureFlag`` if found, ``None`` otherwise.
        """
        return self._flags.get(key)

    def update_flag(self, key: str, **kwargs: Any) -> FeatureFlag | None:
        """Update a feature flag.

        Args:
            key: The flag key.
            **kwargs: Fields to update.

        Returns:
            The updated flag if found.
        """
        flag = self._flags.get(key)
        if flag is None:
            return None
        for k, v in kwargs.items():
            if hasattr(flag, k):
                setattr(flag, k, v)
        flag.updated_at = datetime.now(timezone.utc)
        self._logger.info("flag_updated", key=key)
        return flag

    def delete_flag(self, key: str) -> bool:
        """Delete a feature flag.

        Args:
            key: The flag key.

        Returns:
            ``True`` if deleted.
        """
        if key in self._flags:
            del self._flags[key]
            self._logger.info("flag_deleted", key=key)
            return True
        return False

    def is_enabled(
        self,
        key: str,
        *,
        user_id: str = "",
        org_id: str = "",
        plan_type: str = "",
    ) -> bool:
        """Check if a feature flag is enabled for a given context.

        Args:
            key: The flag key.
            user_id: Optional user ID for user-level flags.
            org_id: Optional org ID for org-level flags.
            plan_type: Optional plan type for plan-level flags.

        Returns:
            ``True`` if the flag is enabled for this context.
        """
        flag = self._flags.get(key)
        if flag is None:
            return False

        if not flag.enabled:
            return False

        if flag.scope == FeatureFlagScope.GLOBAL:
            return True

        if flag.scope == FeatureFlagScope.USER:
            if user_id and user_id in flag.user_ids:
                return True
            return False

        if flag.scope == FeatureFlagScope.ORGANIZATION:
            if org_id and org_id in flag.org_ids:
                return True
            return False

        if flag.scope == FeatureFlagScope.PLAN:
            if plan_type and plan_type in flag.plan_types:
                return True
            return False

        return flag.enabled

    def get_variant(
        self,
        key: str,
        *,
        user_id: str = "",
    ) -> str | None:
        """Get the A/B testing variant for a user.

        Args:
            key: The flag key.
            user_id: User ID for variant assignment.

        Returns:
            The variant name, or ``None`` if not a variant flag.
        """
        flag = self._flags.get(key)
        if flag is None or flag.flag_type != FeatureFlagType.VARIANT:
            return None

        if not flag.variants:
            return None

        # Deterministic assignment based on user_id hash
        if user_id:
            import hashlib
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            variant_keys = list(flag.variants.keys())
            if variant_keys:
                return variant_keys[hash_val % len(variant_keys)]

        # Default to first variant
        return next(iter(flag.variants.keys()), None)

    def get_percentage_rollout(self, key: str, user_id: str = "") -> bool:
        """Check if a user is in the percentage rollout.

        Args:
            key: The flag key.
            user_id: User ID for deterministic assignment.

        Returns:
            ``True`` if the user is in the rollout percentage.
        """
        flag = self._flags.get(key)
        if flag is None or flag.flag_type != FeatureFlagType.PERCENTAGE:
            return False

        if flag.percentage >= 100.0:
            return True
        if flag.percentage <= 0.0:
            return False

        if user_id:
            import hashlib
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            return (hash_val % 100) < flag.percentage

        return False

    def enable_for_user(self, key: str, user_id: str) -> bool:
        """Enable a flag for a specific user.

        Args:
            key: The flag key.
            user_id: The user ID.

        Returns:
            ``True`` if successful.
        """
        flag = self._flags.get(key)
        if flag is None:
            return False
        if user_id not in flag.user_ids:
            flag.user_ids.append(user_id)
        return True

    def disable_for_user(self, key: str, user_id: str) -> bool:
        """Disable a flag for a specific user.

        Args:
            key: The flag key.
            user_id: The user ID.

        Returns:
            ``True`` if successful.
        """
        flag = self._flags.get(key)
        if flag is None:
            return False
        if user_id in flag.user_ids:
            flag.user_ids.remove(user_id)
        return True

    def enable_for_org(self, key: str, org_id: str) -> bool:
        """Enable a flag for a specific organization.

        Args:
            key: The flag key.
            org_id: The organization ID.

        Returns:
            ``True`` if successful.
        """
        flag = self._flags.get(key)
        if flag is None:
            return False
        if org_id not in flag.org_ids:
            flag.org_ids.append(org_id)
        return True

    def list_flags(self, scope: FeatureFlagScope | None = None) -> list[FeatureFlag]:
        """List all feature flags, optionally filtered by scope.

        Args:
            scope: Optional scope filter.

        Returns:
            List of ``FeatureFlag``.
        """
        if scope is None:
            return list(self._flags.values())
        return [f for f in self._flags.values() if f.scope == scope]

    @property
    def flag_count(self) -> int:
        """Number of feature flags."""
        return len(self._flags)

    def clear(self) -> None:
        """Clear all flags (primarily for testing)."""
        self._flags.clear()
