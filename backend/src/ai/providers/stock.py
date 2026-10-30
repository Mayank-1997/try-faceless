"""Free stock image and video providers (Pexels, Pixabay, Unsplash).

These providers search and download free media from stock services.
They implement the same interfaces as Imagen and Veo so the gateways
can use them transparently.  Cost is always $0.00.

Supported services in priority order:
1. Pexels (requires API key)
2. Pixabay (requires API key)
3. Unsplash -- images only (requires API key)
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import quote

import httpx

from src.core.enums import AIProvider
from src.core.exceptions import AIProviderError, ProviderNotInitializedError
from src.core.interfaces import HealthStatus, ImageProvider, ProviderConfig, VideoProvider
from src.core.logging import get_logger


def _clean_query(prompt: str) -> str:
    """Turn a long visual description into a short search query."""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", prompt)
    words = [w for w in text.split() if w]
    return " ".join(words) or "nature"


class _StockClient:
    """Async HTTP client that tries Pexels, Pixabay, and Unsplash."""

    def __init__(
        self,
        pexels_key: str,
        pixabay_key: str,
        unsplash_key: str,
        max_results: int,
        timeout: int,
    ) -> None:
        self._pexels_key = pexels_key
        self._pixabay_key = pixabay_key
        self._unsplash_key = unsplash_key
        self._max_results = max(1, min(max_results, 20))
        self._timeout = timeout
        self._logger = get_logger(__name__)

    async def _get(self, url: str, headers: dict[str, str] | None = None) -> bytes:
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers or {})
            response.raise_for_status()
            return response.content

    async def _get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        data = await self._get(url, headers)
        import json

        return json.loads(data.decode("utf-8"))

    # -------------------------------------------------------------------
    # Pexels
    # -------------------------------------------------------------------
    async def _search_pexels_images(self, query: str) -> list[dict[str, Any]]:
        if not self._pexels_key:
            return []
        url = (
            f"https://api.pexels.com/v1/search?query={quote(query)}"
            f"&per_page={self._max_results}&orientation=landscape"
        )
        try:
            data = await self._get_json(url, {"Authorization": self._pexels_key})
            return [p for p in data.get("photos", []) if p.get("src", {}).get("large2x") or p.get("src", {}).get("large")]
        except Exception as exc:
            self._logger.warning("pexels_image_search_failed", error=str(exc))
            return []

    async def _search_pexels_videos(self, query: str) -> list[dict[str, Any]]:
        if not self._pexels_key:
            return []
        url = (
            f"https://api.pexels.com/videos/search?query={quote(query)}"
            f"&per_page={self._max_results}&orientation=landscape"
        )
        try:
            data = await self._get_json(url, {"Authorization": self._pexels_key})
            return [v for v in data.get("videos", []) if v.get("video_files")]
        except Exception as exc:
            self._logger.warning("pexels_video_search_failed", error=str(exc))
            return []

    # -------------------------------------------------------------------
    # Pixabay
    # -------------------------------------------------------------------
    async def _search_pixabay_images(self, query: str) -> list[dict[str, Any]]:
        if not self._pixabay_key:
            return []
        url = (
            f"https://pixabay.com/api/?key={quote(self._pixabay_key)}"
            f"&q={quote(query)}&image_type=photo&per_page={self._max_results}"
            f"&orientation=horizontal&safesearch=true"
        )
        try:
            data = await self._get_json(url)
            return [p for p in data.get("hits", []) if p.get("largeImageURL")]
        except Exception as exc:
            self._logger.warning("pixabay_image_search_failed", error=str(exc))
            return []

    async def _search_pixabay_videos(self, query: str) -> list[dict[str, Any]]:
        if not self._pixabay_key:
            return []
        url = (
            f"https://pixabay.com/api/videos/?key={quote(self._pixabay_key)}"
            f"&q={quote(query)}&per_page={self._max_results}"
        )
        try:
            data = await self._get_json(url)
            hits = data.get("hits", [])
            valid = []
            for h in hits:
                videos = h.get("videos", {})
                if videos.get("large", {}).get("url") or videos.get("medium", {}).get("url") or videos.get("small", {}).get("url"):
                    valid.append(h)
            return valid
        except Exception as exc:
            self._logger.warning("pixabay_video_search_failed", error=str(exc))
            return []

    # -------------------------------------------------------------------
    # Unsplash (images only)
    # -------------------------------------------------------------------
    async def _search_unsplash_images(self, query: str) -> list[dict[str, Any]]:
        if not self._unsplash_key:
            return []
        url = (
            f"https://api.unsplash.com/search/photos?query={quote(query)}"
            f"&per_page={self._max_results}&orientation=landscape"
        )
        try:
            data = await self._get_json(url, {"Authorization": f"Client-ID {self._unsplash_key}"})
            return [p for p in data.get("results", []) if p.get("urls", {}).get("regular")]
        except Exception as exc:
            self._logger.warning("unsplash_image_search_failed", error=str(exc))
            return []

    async def download_image(self, prompt: str) -> bytes:
        """Find and download a free stock image."""
        query = _clean_query(prompt)
        self._logger.info("stock_image_search", query=query)

        # Pexels
        for result in await self._search_pexels_images(query):
            url = result.get("src", {}).get("large2x") or result.get("src", {}).get("large")
            try:
                return await self._get(str(url))
            except Exception as exc:
                self._logger.warning("pexels_image_download_failed", url=url, error=str(exc))

        # Pixabay
        for result in await self._search_pixabay_images(query):
            url = result.get("largeImageURL")
            try:
                return await self._get(str(url))
            except Exception as exc:
                self._logger.warning("pixabay_image_download_failed", url=url, error=str(exc))

        # Unsplash
        for result in await self._search_unsplash_images(query):
            url = result.get("urls", {}).get("regular")
            try:
                return await self._get(str(url))
            except Exception as exc:
                self._logger.warning("unsplash_image_download_failed", url=url, error=str(exc))

        raise AIProviderError("stock_image", "No free stock image found for the prompt")

    async def download_video(self, prompt: str) -> bytes:
        """Find and download a free stock video."""
        query = _clean_query(prompt)
        self._logger.info("stock_video_search", query=query)

        # Pexels
        for result in await self._search_pexels_videos(query):
            files = result.get("video_files", [])
            files = sorted(
                files,
                key=lambda f: f.get("width", 0),
                reverse=True,
            )
            for vf in files:
                if not vf.get("link"):
                    continue
                try:
                    return await self._get(str(vf["link"]))
                except Exception as exc:
                    self._logger.warning("pexels_video_download_failed", url=vf.get("link"), error=str(exc))

        # Pixabay
        for result in await self._search_pixabay_videos(query):
            videos = result.get("videos", {})
            for key in ("large", "medium", "small"):
                url = videos.get(key, {}).get("url")
                if not url:
                    continue
                try:
                    return await self._get(str(url))
                except Exception as exc:
                    self._logger.warning("pixabay_video_download_failed", url=url, error=str(exc))

        raise AIProviderError("stock_video", "No free stock video found for the prompt")


class StockImageProvider(ImageProvider):
    """Free stock image provider (Pexels, Pixabay, Unsplash)."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._client: _StockClient | None = None
        self._logger = get_logger(__name__)
        self._initialized = False

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.STOCK_IMAGE

    async def initialize(self, config: ProviderConfig) -> None:
        self._config = config
        extra = config.extra or {}
        self._client = _StockClient(
            pexels_key=extra.get("pexels_api_key", ""),
            pixabay_key=extra.get("pixabay_api_key", ""),
            unsplash_key=extra.get("unsplash_api_key", ""),
            max_results=extra.get("max_results", 5),
            timeout=extra.get("request_timeout", 20),
        )
        self._initialized = True
        self._logger.info(
            "stock_image_provider_initialized",
            pexels=bool(extra.get("pexels_api_key")),
            pixabay=bool(extra.get("pixabay_api_key")),
            unsplash=bool(extra.get("unsplash_api_key")),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._client is None:
            raise ProviderNotInitializedError(self.provider_name.value)

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1920,
        height: int = 1080,
        negative_prompt: str | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Download a free stock image matching the prompt."""
        self._ensure_initialized()
        assert self._client is not None
        return await self._client.download_image(prompt)

    def calculate_cost(self, width: int, height: int) -> float:
        """Free stock media costs $0.00."""
        return 0.0

    async def health_check(self) -> HealthStatus:
        """Stock provider is healthy if at least one API key is configured."""
        if self._client is None:
            return HealthStatus.NOT_INITIALIZED
        return HealthStatus.HEALTHY

    async def shutdown(self) -> None:
        self._initialized = False
        self._client = None


class StockVideoProvider(VideoProvider):
    """Free stock video provider (Pexels, Pixabay)."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._client: _StockClient | None = None
        self._logger = get_logger(__name__)
        self._initialized = False

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.STOCK_VIDEO

    async def initialize(self, config: ProviderConfig) -> None:
        self._config = config
        extra = config.extra or {}
        self._client = _StockClient(
            pexels_key=extra.get("pexels_api_key", ""),
            pixabay_key=extra.get("pixabay_api_key", ""),
            unsplash_key="",  # no videos on Unsplash
            max_results=extra.get("max_results", 5),
            timeout=extra.get("request_timeout", 20),
        )
        self._initialized = True
        self._logger.info(
            "stock_video_provider_initialized",
            pexels=bool(extra.get("pexels_api_key")),
            pixabay=bool(extra.get("pixabay_api_key")),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._client is None:
            raise ProviderNotInitializedError(self.provider_name.value)

    async def generate_video(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Download a free stock video matching the prompt."""
        self._ensure_initialized()
        assert self._client is not None
        return await self._client.download_video(prompt)

    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        """Free stock media costs $0.00."""
        return 0.0

    async def health_check(self) -> HealthStatus:
        """Stock provider is healthy if at least one API key is configured."""
        if self._client is None:
            return HealthStatus.NOT_INITIALIZED
        return HealthStatus.HEALTHY

    async def shutdown(self) -> None:
        self._initialized = False
        self._client = None
