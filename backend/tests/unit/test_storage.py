"""Tests for the Local Storage Provider."""

from __future__ import annotations

import pytest

from src.core.exceptions import StorageError
from src.core.interfaces import ProviderConfig
from src.infrastructure.storage.local import LocalStorageProvider


@pytest.fixture
async def storage_provider(tmp_path):
    """Create and initialise a local storage provider in a temp directory."""
    provider = LocalStorageProvider()
    await provider.initialize(
        ProviderConfig(
            api_key="",
            model="local",
            extra={"base_path": str(tmp_path)},
        )
    )
    yield provider
    await provider.shutdown()


class TestLocalStorageProvider:
    @pytest.mark.asyncio
    async def test_upload_and_download(self, storage_provider):
        data = b"Hello, World!"
        uri = await storage_provider.upload(data, "test/file.txt")
        assert "local://" in uri

        downloaded = await storage_provider.download("test/file.txt")
        assert downloaded == data

    @pytest.mark.asyncio
    async def test_exists(self, storage_provider):
        await storage_provider.upload(b"data", "check/file.bin")
        assert await storage_provider.exists("check/file.bin") is True
        assert await storage_provider.exists("check/nonexistent.bin") is False

    @pytest.mark.asyncio
    async def test_delete(self, storage_provider):
        await storage_provider.upload(b"data", "delete/me.txt")
        assert await storage_provider.delete("delete/me.txt") is True
        assert await storage_provider.exists("delete/me.txt") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage_provider):
        assert await storage_provider.delete("nonexistent/file.txt") is False

    @pytest.mark.asyncio
    async def test_download_nonexistent_raises(self, storage_provider):
        with pytest.raises(StorageError):
            await storage_provider.download("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_get_url(self, storage_provider):
        await storage_provider.upload(b"data", "url/test.txt")
        url = await storage_provider.get_url("url/test.txt")
        assert url.startswith("file://")

    @pytest.mark.asyncio
    async def test_list_files(self, storage_provider):
        await storage_provider.upload(b"a", "list/a.txt")
        await storage_provider.upload(b"b", "list/b.txt")
        await storage_provider.upload(b"c", "list/sub/c.txt")

        files = await storage_provider.list_files("list")
        assert len(files) == 3
        assert "list/a.txt" in files

    @pytest.mark.asyncio
    async def test_list_files_nonexistent_prefix(self, storage_provider):
        files = await storage_provider.list_files("nonexistent")
        assert files == []

    @pytest.mark.asyncio
    async def test_list_files_with_limit(self, storage_provider):
        for i in range(10):
            await storage_provider.upload(b"x", f"limit/file_{i}.txt")

        files = await storage_provider.list_files("limit", limit=5)
        assert len(files) == 5

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self, storage_provider):
        await storage_provider.upload(b"deep", "a/b/c/d/file.txt")
        assert await storage_provider.exists("a/b/c/d/file.txt") is True

    def test_provider_name(self, storage_provider):
        assert storage_provider.provider_name == "local"
