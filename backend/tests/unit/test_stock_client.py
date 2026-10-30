"""Unit tests for _StockClient — mocked HTTP, no real API calls.

Covers:
- Search request formation (URL, auth headers) via httpx.MockTransport
- Provider fallback order (Pexels -> Pixabay -> Unsplash)
- Video file selection (highest resolution first)
- No-keys behaviour (no HTTP calls, clear error)
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.ai.providers.stock import _clean_query, _StockClient


def _make_client(
    pexels: str = "pexels-key",
    pixabay: str = "pixabay-key",
    unsplash: str = "unsplash-key",
) -> _StockClient:
    return _StockClient(
        pexels_key=pexels,
        pixabay_key=pixabay,
        unsplash_key=unsplash,
        max_results=3,
        timeout=5,
    )


def _patched_transport(handler):
    """Patch httpx.AsyncClient so every request goes through MockTransport."""
    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def patched(*args, **kwargs):
        kwargs.pop("transport", None)
        return original_client(transport=transport, **kwargs)

    return patch.object(httpx, "AsyncClient", side_effect=patched)


class TestCleanQuery:
    def test_truncates_to_12_words(self):
        prompt = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen"
        assert _clean_query(prompt).count(" ") == 11  # 12 words

    def test_strips_punctuation(self):
        assert _clean_query("stormy, dark: ocean! (waves)") == "stormy dark ocean waves"

    def test_defaults_to_nature(self):
        assert _clean_query("!!! ???") == "nature"


class TestNoKeys:
    async def test_search_makes_no_http_calls(self):
        client = _make_client(pexels="", pixabay="", unsplash="")
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={})

        with _patched_transport(handler):
            images = await client._search_pexels_images("test")
            videos = await client._search_pexels_videos("test")
            pixa = await client._search_pixabay_images("test")

        assert images == [] and videos == [] and pixa == []
        assert requests == []  # keys missing -> short-circuit, no HTTP

    async def test_download_image_raises(self):
        from src.core.exceptions import AIProviderError

        client = _make_client(pexels="", pixabay="", unsplash="")
        with pytest.raises(AIProviderError, match="No free stock image"):
            await client.download_image("tropical beach")

    async def test_download_video_raises(self):
        from src.core.exceptions import AIProviderError

        client = _make_client(pexels="", pixabay="", unsplash="")
        with pytest.raises(AIProviderError, match="No free stock video"):
            await client.download_video("ocean waves")


class TestPexels:
    async def test_image_search_request_and_auth(self):
        client = _make_client()
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if "api.pexels.com" in request.url.host:
                return httpx.Response(200, json={
                    "photos": [{"src": {"large2x": "https://images.pexels.com/1.jpg"}}],
                })
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0jpeg-bytes")

        with _patched_transport(handler):
            data = await client.download_image("tropical island beach")

        # Search request correctness
        search = requests[0]
        assert search.url.host == "api.pexels.com"
        assert search.url.path == "/v1/search"
        assert "query=tropical" in str(search.url)
        assert "orientation=landscape" in str(search.url)
        assert search.headers["Authorization"] == "pexels-key"

        # Download request + returned bytes
        assert requests[1].url.host == "images.pexels.com"
        assert data == b"\xff\xd8\xff\xe0jpeg-bytes"

    async def test_video_download_picks_highest_resolution(self):
        client = _make_client()
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if "api.pexels.com" in request.url.host:
                return httpx.Response(200, json={
                    "videos": [{
                        "video_files": [
                            {"width": 640, "link": "https://vod.pexels.com/small.mp4"},
                            {"width": 1920, "link": "https://vod.pexels.com/large.mp4"},
                        ],
                    }],
                })
            return httpx.Response(200, content=b"\x00\x00\x00\x18ftypmp42")

        with _patched_transport(handler):
            data = await client.download_video("ocean waves aerial")

        # The 1920-width file must be preferred over the 640 one
        download_urls = [str(r.url) for r in requests[1:]]
        assert "https://vod.pexels.com/large.mp4" in download_urls
        assert "https://vod.pexels.com/small.mp4" not in download_urls
        assert data == b"\x00\x00\x00\x18ftypmp42"


class TestFallback:
    async def test_pexels_empty_falls_back_to_pixabay(self):
        client = _make_client()
        hosts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            hosts.append(request.url.host)
            if request.url.host == "api.pexels.com":
                return httpx.Response(200, json={"photos": []})  # no results
            if request.url.host == "pixabay.com":
                return httpx.Response(200, json={
                    "hits": [{"largeImageURL": "https://cdn.pixabay.com/1.jpg"}],
                })
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0pixabay-jpeg")

        with _patched_transport(handler):
            data = await client.download_image("misty ruins")

        # Order: pexels search first, then pixabay search, then pixabay CDN
        assert hosts == ["api.pexels.com", "pixabay.com", "cdn.pixabay.com"]
        assert data == b"\xff\xd8\xff\xe0pixabay-jpeg"

    async def test_pexels_and_pixabay_empty_falls_back_to_unsplash(self):
        client = _make_client()
        hosts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            hosts.append(request.url.host)
            if request.url.host == "api.pexels.com":
                return httpx.Response(200, json={"photos": []})
            if request.url.host == "pixabay.com":
                return httpx.Response(200, json={"hits": []})
            if request.url.host == "api.unsplash.com":
                return httpx.Response(200, json={
                    "results": [{"urls": {"regular": "https://images.unsplash.com/1.jpg"}}],
                })
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0unsplash-jpeg")

        with _patched_transport(handler):
            data = await client.download_image("foggy forest")

        assert hosts == [
            "api.pexels.com",
            "pixabay.com",
            "api.unsplash.com",
            "images.unsplash.com",
        ]
        assert data == b"\xff\xd8\xff\xe0unsplash-jpeg"

    async def test_unsplash_uses_client_id_header(self):
        client = _make_client()
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "api.pexels.com":
                return httpx.Response(200, json={"photos": []})
            if request.url.host == "pixabay.com":
                return httpx.Response(200, json={"hits": []})
            if request.url.host == "api.unsplash.com":
                return httpx.Response(200, json={
                    "results": [{"urls": {"regular": "https://images.unsplash.com/1.jpg"}}],
                })
            return httpx.Response(200, content=b"\xff\xd8\xff\xe0unsplash-jpeg")

        with _patched_transport(handler):
            await client.download_image("foggy forest")

        unsplash_req = next(r for r in requests if r.url.host == "api.unsplash.com")
        assert unsplash_req.headers["Authorization"] == "Client-ID unsplash-key"

    async def test_video_falls_back_to_pixabay(self):
        client = _make_client()
        hosts: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            hosts.append(request.url.host)
            if request.url.host == "api.pexels.com":
                return httpx.Response(200, json={"videos": []})
            if request.url.host == "pixabay.com":
                return httpx.Response(200, json={
                    "hits": [{
                        "videos": {
                            "large": {"url": "https://i.pixabay.com/large.mp4"},
                            "medium": {"url": "https://i.pixabay.com/medium.mp4"},
                        },
                    }],
                })
            return httpx.Response(200, content=b"\x00\x00\x00\x18ftypmp42")

        with _patched_transport(handler):
            data = await client.download_video("rescue boat")

        # Pexels first (empty), then pixabay search, then the LARGE file
        assert hosts == [
            "api.pexels.com",
            "pixabay.com",
            "i.pixabay.com",
        ]
        assert data == b"\x00\x00\x00\x18ftypmp42"
