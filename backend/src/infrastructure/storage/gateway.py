"""Storage Gateway — unified interface for file storage operations.

The application never writes directly to disk.  All file operations go
through the Storage Gateway, which delegates to the configured storage
provider (Local, S3, GCS, Azure Blob, MinIO).

Architecture::

    Service → StorageGateway → StorageProvider (Local/S3/GCS/MinIO)
"""

from __future__ import annotations

from typing import Any

from src.core.exceptions import StorageError
from src.core.interfaces import HealthStatus, StorageProvider
from src.core.logging import get_logger


class StorageGateway:
    """Unified gateway for file storage operations.

    Wraps a single ``StorageProvider`` instance and adds structured
    logging and error handling.  Future versions may support multi-
    backend routing (e.g. hot assets on S3, cold assets on GCS).
    """

    def __init__(self, provider: StorageProvider) -> None:
        """Create the Storage Gateway.

        Args:
            provider: The initialised storage provider instance.
        """
        self._provider = provider
        self._logger = get_logger(__name__)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialise the gateway."""
        self._initialized = True
        self._logger.info(
            "storage_gateway_initialized",
            provider=self._provider.provider_name,
        )

    async def upload(
        self,
        data: bytes,
        key: str,
        *,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to storage.

        Args:
            data: Raw bytes to store.
            key: Storage key / path.
            content_type: MIME type of the content.

        Returns:
            Storage URI for the uploaded file.
        """
        self._ensure_initialized()
        try:
            uri = await self._provider.upload(data, key, content_type=content_type)
            self._logger.info(
                "storage_upload_success",
                key=key,
                size_bytes=len(data),
                content_type=content_type,
                uri=uri,
            )
            return uri
        except Exception as exc:
            self._logger.error("storage_upload_failed", key=key, error=str(exc))
            raise StorageError(f"Upload failed for key '{key}': {exc}")

    async def download(self, key: str) -> bytes:
        """Download bytes from storage.

        Args:
            key: Storage key / path.

        Returns:
            The raw bytes stored at the given key.
        """
        self._ensure_initialized()
        try:
            data = await self._provider.download(key)
            self._logger.info(
                "storage_download_success",
                key=key,
                size_bytes=len(data),
            )
            return data
        except Exception as exc:
            self._logger.error("storage_download_failed", key=key, error=str(exc))
            raise StorageError(f"Download failed for key '{key}': {exc}")

    async def delete(self, key: str) -> bool:
        """Delete a file from storage.

        Args:
            key: Storage key / path.

        Returns:
            ``True`` if deleted, ``False`` if it did not exist.
        """
        self._ensure_initialized()
        try:
            result = await self._provider.delete(key)
            self._logger.info("storage_delete_success", key=key, deleted=result)
            return result
        except Exception as exc:
            self._logger.error("storage_delete_failed", key=key, error=str(exc))
            raise StorageError(f"Delete failed for key '{key}': {exc}")

    async def exists(self, key: str) -> bool:
        """Check if a file exists in storage."""
        self._ensure_initialized()
        return await self._provider.exists(key)

    async def get_url(self, key: str, *, expires_in: int = 3600) -> str:
        """Get a accessible URL for a stored file.

        Args:
            key: Storage key / path.
            expires_in: URL validity duration in seconds.

        Returns:
            A URL that can be used to access the file.
        """
        self._ensure_initialized()
        return await self._provider.get_url(key, expires_in=expires_in)

    async def list_files(self, prefix: str, *, limit: int = 100) -> list[str]:
        """List files under a given prefix.

        Args:
            prefix: Path prefix to search under.
            limit: Maximum number of results.

        Returns:
            List of storage keys matching the prefix.
        """
        self._ensure_initialized()
        return await self._provider.list_files(prefix, limit=limit)

    async def health_check(self) -> HealthStatus:
        """Check storage provider health."""
        self._ensure_initialized()
        return HealthStatus(
            healthy=True,
            service="storage",
            details={"provider": self._provider.provider_name},
        )

    async def shutdown(self) -> None:
        """Release resources."""
        if hasattr(self._provider, "shutdown"):
            await self._provider.shutdown()
        self._initialized = False
        self._logger.info("storage_gateway_shutdown")

    @property
    def provider_name(self) -> str:
        """Return the underlying provider name."""
        return self._provider.provider_name

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise StorageError("Storage Gateway is not initialised")
