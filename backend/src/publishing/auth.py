"""Authentication Manager.

Provides provider authentication abstraction supporting:
- OAuth2
- API Keys
- Refresh Tokens
- Credential Storage
- Future providers
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.publishing.schema import AuthCredential, AuthMethod, PlatformConfig, PublishingPlatform
from src.core.logging import get_logger


class AuthenticationManager:
    """Manages authentication credentials for publishing platforms.

    Stores and retrieves credentials, handles token refresh, and
    supports multiple authentication methods.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._credentials: dict[str, AuthCredential] = {}  # key = "{platform}:{user_id}"

    def _make_key(self, platform: PublishingPlatform, user_id: str = "default") -> str:
        """Create a storage key for a credential."""
        return f"{platform.value}:{user_id}"

    async def store_credential(self, credential: AuthCredential, user_id: str = "default") -> None:
        """Store an authentication credential.

        Args:
            credential: The credential to store.
            user_id: User identifier for multi-user support.
        """
        key = self._make_key(credential.platform, user_id)
        credential.updated_at = datetime.now(timezone.utc)
        self._credentials[key] = credential
        self._logger.info(
            "credential_stored",
            platform=credential.platform.value,
            user_id=user_id,
            method=credential.auth_method.value,
        )

    async def get_credential(self, platform: PublishingPlatform, user_id: str = "default") -> AuthCredential | None:
        """Retrieve a stored credential.

        Args:
            platform: The publishing platform.
            user_id: User identifier.

        Returns:
            The stored ``AuthCredential``, or ``None`` if not found.
        """
        key = self._make_key(platform, user_id)
        return self._credentials.get(key)

    async def delete_credential(self, platform: PublishingPlatform, user_id: str = "default") -> bool:
        """Delete a stored credential.

        Args:
            platform: The publishing platform.
            user_id: User identifier.

        Returns:
            ``True`` if a credential was deleted.
        """
        key = self._make_key(platform, user_id)
        if key in self._credentials:
            del self._credentials[key]
            self._logger.info("credential_deleted", platform=platform.value, user_id=user_id)
            return True
        return False

    async def refresh_credential(
        self, platform: PublishingPlatform, config: PlatformConfig, user_id: str = "default"
    ) -> AuthCredential | None:
        """Refresh an expired credential.

        Args:
            platform: The publishing platform.
            config: Platform configuration with refresh token.
            user_id: User identifier.

        Returns:
            A refreshed ``AuthCredential``, or ``None`` if refresh failed.
        """
        credential = await self.get_credential(platform, user_id)
        if credential is None:
            self._logger.warning("credential_not_found_for_refresh", platform=platform.value)
            return None

        if not credential.is_expired:
            return credential

        if not credential.refresh_token:
            self._logger.warning("no_refresh_token", platform=platform.value)
            return None

        # Simulate token refresh (real implementation would call the platform API)
        new_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        credential.access_token = f"refreshed_{credential.access_token[:8]}"
        credential.token_expiry = new_expiry
        credential.updated_at = datetime.now(timezone.utc)

        await self.store_credential(credential, user_id)
        self._logger.info("credential_refreshed", platform=platform.value, user_id=user_id)
        return credential

    async def authenticate(
        self, platform: PublishingPlatform, config: PlatformConfig, user_id: str = "default"
    ) -> AuthCredential:
        """Authenticate with a platform and store the credential.

        Args:
            platform: The publishing platform.
            config: Platform configuration with credentials.
            user_id: User identifier.

        Returns:
            An ``AuthCredential`` with tokens.

        Raises:
            ValueError: If authentication fails.
        """
        if not config.client_id and not config.api_key:
            raise ValueError(f"Missing credentials for {platform.value}")

        # Determine auth method
        if config.refresh_token:
            auth_method = AuthMethod.REFRESH_TOKEN
        elif config.client_id and config.client_secret:
            auth_method = AuthMethod.OAUTH2
        elif config.api_key:
            auth_method = AuthMethod.API_KEY
        else:
            auth_method = AuthMethod.CUSTOM

        # Simulate OAuth2 flow (real implementation would redirect to OAuth URL)
        credential = AuthCredential(
            platform=platform,
            auth_method=auth_method,
            access_token=f"access_{platform.value}_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            refresh_token=config.refresh_token or f"refresh_{platform.value}_{user_id}",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=config.scopes,
            metadata={"client_id": config.client_id},
        )

        await self.store_credential(credential, user_id)
        self._logger.info(
            "authenticated",
            platform=platform.value,
            user_id=user_id,
            method=auth_method.value,
        )
        return credential

    async def validate_credential(
        self, platform: PublishingPlatform, user_id: str = "default"
    ) -> bool:
        """Validate that a credential exists and is not expired.

        Args:
            platform: The publishing platform.
            user_id: User identifier.

        Returns:
            ``True`` if the credential is valid.
        """
        credential = await self.get_credential(platform, user_id)
        if credential is None:
            return False
        return credential.is_valid

    @property
    def credential_count(self) -> int:
        """Number of stored credentials."""
        return len(self._credentials)

    def list_platforms(self, user_id: str = "default") -> list[PublishingPlatform]:
        """List all platforms with stored credentials for a user.

        Args:
            user_id: User identifier.

        Returns:
            List of platforms with credentials.
        """
        prefix = f":{user_id}"
        platforms: list[PublishingPlatform] = []
        for key in self._credentials:
            if key.endswith(prefix):
                platform_str = key.replace(prefix, "")
                try:
                    platforms.append(PublishingPlatform(platform_str))
                except ValueError:
                    pass
        return platforms
