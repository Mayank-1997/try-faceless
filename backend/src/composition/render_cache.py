"""Render Cache.

Caches completed render outputs for reuse.

Initial implementation:
- Completed render caching
- Composition hash
- Output reuse

Architecture supports future:
- Scene-level rendering
- Segment rendering
- Incremental rendering
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from src.composition.schema import CompositionDocument, RenderCacheEntry
from src.core.logging import get_logger


class RenderCache:
    """Caches rendered video outputs by composition hash.

    When a composition is rendered, the output is cached keyed by
    a deterministic hash of the composition.  If the same composition
    is rendered again, the cached output is reused.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._logger = get_logger(__name__)
        self._cache: dict[str, RenderCacheEntry] = {}
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0

    def compute_hash(self, composition: CompositionDocument) -> str:
        """Compute a deterministic hash for a composition.

        Args:
            composition: The composition document.

        Returns:
            SHA-256 hash string.
        """
        return composition.to_hash()

    def get(self, composition: CompositionDocument) -> RenderCacheEntry | None:
        """Look up a cached render by composition.

        Args:
            composition: The composition to look up.

        Returns:
            The cached ``RenderCacheEntry``, or ``None`` if not found.
        """
        h = self.compute_hash(composition)
        entry = self._cache.get(h)

        if entry is None:
            self._misses += 1
            return None

        entry.hit_count += 1
        self._hits += 1
        self._logger.info("render_cache_hit", hash=h[:16], hits=entry.hit_count)
        return entry

    def put(self, composition: CompositionDocument, output_path: str, output_size: int = 0) -> None:
        """Cache a render result.

        Args:
            composition: The composition that was rendered.
            output_path: Path to the rendered output.
            output_size: Output file size in bytes.
        """
        if len(self._cache) >= self._max_entries:
            self._evict_oldest()

        h = self.compute_hash(composition)
        self._cache[h] = RenderCacheEntry(
            composition_hash=h,
            output_path=output_path,
            output_size_bytes=output_size,
        )
        self._logger.info("render_cache_stored", hash=h[:16], output_path=output_path)

    def invalidate(self, composition: CompositionDocument) -> bool:
        """Remove a cached entry.

        Args:
            composition: The composition to invalidate.

        Returns:
            ``True`` if an entry was removed.
        """
        h = self.compute_hash(composition)
        if h in self._cache:
            del self._cache[h]
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

    def _evict_oldest(self) -> None:
        """Evict the oldest entry."""
        if not self._cache:
            return
        oldest = min(self._cache, key=lambda k: self._cache[k].created_at)
        del self._cache[oldest]
        self._logger.info("render_cache_evicted", hash=oldest[:16])
