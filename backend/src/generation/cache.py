"""Cache Manager.

Intelligent generation caching to avoid duplicate API calls.

Cache key is composed of:
- Prompt
- Provider
- Model
- Aspect ratio
- Resolution
- Duration
- Seed
- Style
- Prompt version

If an identical generation already exists, the cached asset is reused
instead of making a new API call.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.logging import get_logger
from src.generation.schema import CacheEntry, CacheKey, GeneratedAsset


class CacheManager:
    """Manages generation cache for deduplication.

    Stores cached assets keyed by a deterministic hash of generation
    parameters.  When a request matches a cached entry, the asset is
    reused without calling the provider.
    """

    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 86400) -> None:
        self._logger = get_logger(__name__)
        self._cache: dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def make_key(self, request: Any, *, provider: str = "", model: str = "") -> CacheKey:
        """Create a cache key from a generation request.

        Args:
            request: The generation request (GenerationRequest or compatible).
            provider: Provider name (from the job, not the request).
            model: Model name (from the job, not the request).

        Returns:
            A ``CacheKey`` instance.
        """
        return CacheKey(
            prompt=getattr(request, "prompt", ""),
            provider=provider or getattr(request, "provider", ""),
            model=model or getattr(request, "model", ""),
            aspect_ratio=getattr(request, "aspect_ratio", "16:9"),
            resolution=getattr(request, "resolution", "1920x1080"),
            duration_seconds=getattr(request, "duration_seconds", None),
            seed=getattr(request, "seed", None),
            style=getattr(request, "style", None),
            prompt_version=getattr(request, "prompt_version", "1.0.0"),
        )

    def get(self, key: CacheKey) -> GeneratedAsset | None:
        """Look up a cached asset by key.

        Args:
            key: The cache key.

        Returns:
            The cached ``GeneratedAsset``, or ``None`` if not found or expired.
        """
        key_hash = key.to_hash()
        entry = self._cache.get(key_hash)

        if entry is None:
            self._misses += 1
            return None

        # Check TTL
        now = datetime.now(timezone.utc)
        age = (now - entry.created_at).total_seconds()
        if age > self._ttl_seconds:
            del self._cache[key_hash]
            self._misses += 1
            self._logger.info("cache_expired", key_hash=key_hash[:16])
            return None

        entry.hit_count += 1
        self._hits += 1
        self._logger.info("cache_hit", key_hash=key_hash[:16], hit_count=entry.hit_count)
        return entry.asset

    def put(self, key: CacheKey, asset: GeneratedAsset) -> None:
        """Store an asset in the cache.

        Args:
            key: The cache key.
            asset: The generated asset to cache.
        """
        if len(self._cache) >= self._max_entries:
            self._evict_oldest()

        key_hash = key.to_hash()
        self._cache[key_hash] = CacheEntry(
            key_hash=key_hash,
            asset=asset,
        )
        self._logger.info("cache_stored", key_hash=key_hash[:16])

    def invalidate(self, key: CacheKey) -> bool:
        """Remove a specific entry from the cache.

        Args:
            key: The cache key to invalidate.

        Returns:
            ``True`` if an entry was removed.
        """
        key_hash = key.to_hash()
        if key_hash in self._cache:
            del self._cache[key_hash]
            return True
        return False

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Number of cached entries."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (0.0 to 1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def hits(self) -> int:
        """Total cache hits."""
        return self._hits

    @property
    def misses(self) -> int:
        """Total cache misses."""
        return self._misses

    def _evict_oldest(self) -> None:
        """Evict the oldest entry when cache is full."""
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self._logger.info("cache_evicted", key_hash=oldest_key[:16])
