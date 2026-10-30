"""API Management Service.

Supports:
- API Keys
- Rate limits
- Quotas
- Usage reports
- Developer Portal (future)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.platform.schema import ApiKeyInfo, ApiKeyScope, Quota, RateLimitConfig, UsageResourceType
from src.core.logging import get_logger


class ApiManagementService:
    """Manages API keys, rate limits, and quotas.

    Provides CRUD for API keys, rate limit enforcement, and quota
    tracking. Developer portal is deferred to a future phase.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._api_keys: dict[UUID, ApiKeyInfo] = {}
        self._key_values: dict[UUID, str] = {}  # key_id -> actual key string
        self._rate_limits: dict[str, RateLimitConfig] = {}  # user_id -> config
        self._quotas: dict[str, dict[UsageResourceType, Quota]] = {}  # user_id -> quotas
        self._request_counts: dict[str, list[datetime]] = {}  # user_id -> request timestamps

    def create_api_key(
        self,
        user_id: str,
        name: str,
        *,
        org_id: str = "",
        scopes: list[ApiKeyScope] | None = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_day: int = 10000,
        expires_in_days: int | None = None,
    ) -> tuple[ApiKeyInfo, str]:
        """Create a new API key.

        Args:
            user_id: The user ID.
            name: A friendly name for the key.
            org_id: Optional organization ID.
            scopes: Permission scopes.
            rate_limit_per_minute: Rate limit per minute.
            rate_limit_per_day: Rate limit per day.
            expires_in_days: Optional expiration in days.

        Returns:
            A tuple of (``ApiKeyInfo``, actual_key_string).
        """
        import secrets

        key_info = ApiKeyInfo(
            user_id=user_id,
            org_id=org_id,
            name=name,
            scopes=scopes or [ApiKeyScope.READ],
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_day=rate_limit_per_day,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days) if expires_in_days else None,
        )

        key_string = f"sk_{secrets.token_urlsafe(32)}"
        self._api_keys[key_info.id] = key_info
        self._key_values[key_info.id] = key_string

        self._logger.info("api_key_created", key_id=str(key_info.id), user_id=user_id, name=name)
        return key_info, key_string

    def get_api_key(self, key_id: UUID) -> ApiKeyInfo | None:
        """Get API key info by ID.

        Args:
            key_id: The key ID.

        Returns:
            The ``ApiKeyInfo`` if found.
        """
        return self._api_keys.get(key_id)

    def get_api_key_by_value(self, key_string: str) -> ApiKeyInfo | None:
        """Get API key info by the actual key string.

        Args:
            key_string: The API key string.

        Returns:
            The ``ApiKeyInfo`` if found and valid.
        """
        for key_id, value in self._key_values.items():
            if value == key_string:
                info = self._api_keys.get(key_id)
                if info and info.is_active and not info.is_expired:
                    info.last_used_at = datetime.now(timezone.utc)
                    return info
        return None

    def list_api_keys(self, user_id: str) -> list[ApiKeyInfo]:
        """List API keys for a user.

        Args:
            user_id: The user ID.

        Returns:
            List of ``ApiKeyInfo``.
        """
        return [k for k in self._api_keys.values() if k.user_id == user_id]

    def revoke_api_key(self, key_id: UUID) -> bool:
        """Revoke an API key.

        Args:
            key_id: The key ID.

        Returns:
            ``True`` if revoked.
        """
        key = self._api_keys.get(key_id)
        if key is None:
            return False
        key.is_active = False
        self._logger.info("api_key_revoked", key_id=str(key_id))
        return True

    def delete_api_key(self, key_id: UUID) -> bool:
        """Delete an API key.

        Args:
            key_id: The key ID.

        Returns:
            ``True`` if deleted.
        """
        if key_id in self._api_keys:
            del self._api_keys[key_id]
            self._key_values.pop(key_id, None)
            return True
        return False

    def check_rate_limit(self, user_id: str) -> bool:
        """Check if a user is within rate limits.

        Args:
            user_id: The user ID.

        Returns:
            ``True`` if within rate limits.
        """
        config = self._rate_limits.get(user_id, RateLimitConfig())
        now = datetime.now(timezone.utc)

        # Get or initialize request timestamps
        timestamps = self._request_counts.get(user_id, [])

        # Filter to last minute
        minute_ago = now - timedelta(minutes=1)
        recent_minute = [t for t in timestamps if t > minute_ago]

        if len(recent_minute) >= config.requests_per_minute:
            return False

        # Filter to last day
        day_ago = now - timedelta(days=1)
        recent_day = [t for t in timestamps if t > day_ago]

        if len(recent_day) >= config.requests_per_day:
            return False

        # Record this request
        timestamps.append(now)
        self._request_counts[user_id] = timestamps

        return True

    def set_rate_limit(self, user_id: str, config: RateLimitConfig) -> None:
        """Set rate limit configuration for a user.

        Args:
            user_id: The user ID.
            config: The rate limit config.
        """
        self._rate_limits[user_id] = config
        self._logger.info("rate_limit_set", user_id=user_id, rpm=config.requests_per_minute)

    def get_rate_limit(self, user_id: str) -> RateLimitConfig:
        """Get rate limit configuration for a user.

        Args:
            user_id: The user ID.

        Returns:
            The ``RateLimitConfig``.
        """
        return self._rate_limits.get(user_id, RateLimitConfig())

    def set_quota(
        self,
        user_id: str,
        resource_type: UsageResourceType,
        limit: float,
        *,
        org_id: str = "",
        period: str = "monthly",
    ) -> Quota:
        """Set a usage quota for a user.

        Args:
            user_id: The user ID.
            resource_type: The resource type.
            limit: The quota limit.
            org_id: Optional org ID.
            period: Quota period.

        Returns:
            The ``Quota``.
        """
        quota = Quota(
            user_id=user_id,
            org_id=org_id,
            resource_type=resource_type,
            limit=limit,
            period=period,
            reset_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        if user_id not in self._quotas:
            self._quotas[user_id] = {}
        self._quotas[user_id][resource_type] = quota
        self._logger.info("quota_set", user_id=user_id, resource=resource_type.value, limit=limit)
        return quota

    def get_quota(self, user_id: str, resource_type: UsageResourceType) -> Quota | None:
        """Get a quota for a user and resource type.

        Args:
            user_id: The user ID.
            resource_type: The resource type.

        Returns:
            The ``Quota`` if set.
        """
        return self._quotas.get(user_id, {}).get(resource_type)

    def record_quota_usage(self, user_id: str, resource_type: UsageResourceType, amount: float) -> Quota | None:
        """Record usage against a quota.

        Args:
            user_id: The user ID.
            resource_type: The resource type.
            amount: The amount used.

        Returns:
            The updated ``Quota``, or ``None`` if no quota set.
        """
        quota = self.get_quota(user_id, resource_type)
        if quota is None:
            return None
        quota.used += amount
        self._logger.info(
            "quota_usage_recorded",
            user_id=user_id,
            resource=resource_type.value,
            used=quota.used,
            limit=quota.limit,
        )
        return quota

    def check_quota(self, user_id: str, resource_type: UsageResourceType, amount: float = 1.0) -> bool:
        """Check if usage is within quota.

        Args:
            user_id: The user ID.
            resource_type: The resource type.
            amount: The amount to check.

        Returns:
            ``True`` if within quota.
        """
        quota = self.get_quota(user_id, resource_type)
        if quota is None:
            return True  # No quota set — unlimited
        return quota.used + amount <= quota.limit

    def get_usage_report(self, user_id: str) -> dict[str, Any]:
        """Get a usage report for a user.

        Args:
            user_id: The user ID.

        Returns:
            A dict with API key info, rate limits, and quotas.
        """
        return {
            "api_keys": [
                {
                    "id": str(k.id),
                    "name": k.name,
                    "is_active": k.is_active,
                    "scopes": [s.value for s in k.scopes],
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                }
                for k in self.list_api_keys(user_id)
            ],
            "rate_limit": {
                "requests_per_minute": self.get_rate_limit(user_id).requests_per_minute,
                "requests_per_day": self.get_rate_limit(user_id).requests_per_day,
            },
            "quotas": {
                rt.value: {
                    "limit": q.limit,
                    "used": q.used,
                    "remaining": q.remaining,
                    "usage_percentage": q.usage_percentage,
                }
                for rt, q in self._quotas.get(user_id, {}).items()
            },
        }

    @property
    def api_key_count(self) -> int:
        """Number of API keys."""
        return len(self._api_keys)

    def clear(self) -> None:
        """Clear all data (primarily for testing)."""
        self._api_keys.clear()
        self._key_values.clear()
        self._rate_limits.clear()
        self._quotas.clear()
        self._request_counts.clear()
