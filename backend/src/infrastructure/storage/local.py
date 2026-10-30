"""Local filesystem storage provider — concrete implementation of ``StorageProvider``.

Stores files on the local filesystem.  Used in development and for
self-hosted deployments.  Production deployments typically use S3 or GCS.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from src.core.exceptions import StorageError
from src.core.interfaces import HealthStatus, ProviderConfig, StorageProvider
from src.core.logging import get_logger


class LocalStorageProvider(StorageProvider):
    """Local filesystem implementation of the ``StorageProvider`` interface."""

    def __init__(self) -> None:
        self._base_path: Path = Path("/app/storage")
        self._logger = get_logger(__name__)
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "local"

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialise the local storage provider.

        Args:
            config: Provider configuration with ``base_path`` in ``extra``.
        """
        base_path = config.extra.get("base_path", "/app/storage")
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        self._logger.info(
            "local_storage_initialized",
            base_path=str(self._base_path),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise StorageError("Local storage provider is not initialised")

    def _full_path(self, key: str) -> Path:
        """Convert a storage key to a full filesystem path.

        Args:
            key: Storage key (e.g. "projects/abc/images/scene1.png").

        Returns:
            Full ``Path`` object.
        """
        return self._base_path / key

    async def upload(self, data: bytes, key: str, *, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to the local filesystem.

        Args:
            data: Raw bytes to store.
            key: Storage key / relative path.
            content_type: MIME type (stored as metadata, not used in local FS).

        Returns:
            File URI (``local://<base_path>/<key>``).
        """
        self._ensure_initialized()
        file_path = self._full_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_bytes(data)
            uri = f"local://{self._base_path}/{key}"
            return uri
        except OSError as exc:
            raise StorageError(f"Failed to write file '{key}': {exc}")

    async def download(self, key: str) -> bytes:
        """Download bytes from the local filesystem.

        Args:
            key: Storage key / relative path.

        Returns:
            The raw bytes stored at the given key.

        Raises:
            StorageError: If the file does not exist or cannot be read.
        """
        self._ensure_initialized()
        file_path = self._full_path(key)

        if not file_path.exists():
            raise StorageError(f"File not found: '{key}'")

        try:
            return file_path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Failed to read file '{key}': {exc}")

    async def delete(self, key: str) -> bool:
        """Delete a file from the local filesystem.

        Args:
            key: Storage key / relative path.

        Returns:
            ``True`` if deleted, ``False`` if it did not exist.
        """
        self._ensure_initialized()
        file_path = self._full_path(key)

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            return True
        except OSError as exc:
            raise StorageError(f"Failed to delete file '{key}': {exc}")

    async def exists(self, key: str) -> bool:
        """Check if a file exists on the local filesystem."""
        self._ensure_initialized()
        return self._full_path(key).exists()

    async def get_url(self, key: str, *, expires_in: int = 3600) -> str:
        """Get a accessible URL for a locally stored file.

        For local storage, this returns a file:// URI.  The ``expires_in``
        parameter is ignored (local files don't expire).

        Args:
            key: Storage key / relative path.
            expires_in: Ignored for local storage.

        Returns:
            ``file://<absolute_path>`` URI.
        """
        self._ensure_initialized()
        file_path = self._full_path(key)
        return f"file://{file_path.resolve()}"

    async def list_files(self, prefix: str, *, limit: int = 100) -> list[str]:
        """List files under a given prefix on the local filesystem.

        Args:
            prefix: Path prefix to search under.
            limit: Maximum number of results.

        Returns:
            List of storage keys (relative paths) matching the prefix.
        """
        self._ensure_initialized()
        search_path = self._full_path(prefix)

        if not search_path.exists():
            return []

        if search_path.is_file():
            return [prefix]

        results: list[str] = []
        for root, _, files in os.walk(search_path):
            for filename in files:
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(self._base_path)
                results.append(str(rel_path))
                if len(results) >= limit:
                    return results

        return results

    async def shutdown(self) -> None:
        """Release resources."""
        self._initialized = False
        self._logger.info("local_storage_shutdown")
