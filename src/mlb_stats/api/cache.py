"""File-based JSON cache for MLB Stats API responses.

Only caches immutable game data (game feed, boxscore, play-by-play).
Reference data (teams, venues, players, schedule) is NEVER cached.
"""

import json
import logging
from pathlib import Path
from typing import Any

from mlb_stats.api.endpoints import CACHEABLE_TYPES

logger = logging.getLogger(__name__)


class ResponseCache:
    """File-based JSON cache for API responses.

    Only supports caching for specific endpoint types (game data).
    Reference data is never cached to ensure freshness.

    Parameters
    ----------
    cache_dir : str or Path
        Directory to store cached responses.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create cache directory structure."""
        for cache_type in CACHEABLE_TYPES:
            (self.cache_dir / cache_type).mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, endpoint_type: str, key: str) -> Path:
        """Get the file path for a cached response.

        Parameters
        ----------
        endpoint_type : str
            Type of endpoint (e.g., 'game_feed', 'boxscore')
        key : str
            Cache key (usually gamePk)

        Returns
        -------
        Path
            Path to the cache file
        """
        return self.cache_dir / endpoint_type / f"{key}.json"

    def get(self, endpoint_type: str, key: str) -> dict[str, Any] | None:
        """Retrieve a cached response.

        Parameters
        ----------
        endpoint_type : str
            Type of endpoint (e.g., 'game_feed', 'boxscore')
        key : str
            Cache key (usually gamePk)

        Returns
        -------
        dict or None
            Cached JSON data, or None if not cached or endpoint type
            is not cacheable.
        """
        if endpoint_type not in CACHEABLE_TYPES:
            logger.debug(
                "Endpoint type '%s' is not cacheable, skipping cache lookup",
                endpoint_type,
            )
            return None

        cache_path = self._get_cache_path(endpoint_type, key)

        if not cache_path.exists():
            logger.debug("Cache miss for %s/%s", endpoint_type, key)
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Cache hit for %s/%s", endpoint_type, key)
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to read cache file %s: %s",
                cache_path,
                e,
            )
            return None

    def set(self, endpoint_type: str, key: str, data: dict[str, Any]) -> bool:
        """Store a response in the cache.

        Only stores data for cacheable endpoint types.

        Parameters
        ----------
        endpoint_type : str
            Type of endpoint (e.g., 'game_feed', 'boxscore')
        key : str
            Cache key (usually gamePk)
        data : dict
            JSON data to cache

        Returns
        -------
        bool
            True if cached successfully, False otherwise.
        """
        if endpoint_type not in CACHEABLE_TYPES:
            logger.debug(
                "Endpoint type '%s' is not cacheable, skipping cache write",
                endpoint_type,
            )
            return False

        cache_path = self._get_cache_path(endpoint_type, key)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, separators=(",", ":"))
            logger.debug("Cached response for %s/%s", endpoint_type, key)
            return True
        except OSError as e:
            logger.warning(
                "Failed to write cache file %s: %s",
                cache_path,
                e,
            )
            return False

    def exists(self, endpoint_type: str, key: str) -> bool:
        """Check if a response is cached.

        Parameters
        ----------
        endpoint_type : str
            Type of endpoint
        key : str
            Cache key

        Returns
        -------
        bool
            True if cached, False otherwise.
        """
        if endpoint_type not in CACHEABLE_TYPES:
            return False
        return self._get_cache_path(endpoint_type, key).exists()

    def delete(self, endpoint_type: str, key: str) -> bool:
        """Delete a cached response.

        Parameters
        ----------
        endpoint_type : str
            Type of endpoint
        key : str
            Cache key

        Returns
        -------
        bool
            True if deleted, False if not found.
        """
        cache_path = self._get_cache_path(endpoint_type, key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug("Deleted cache for %s/%s", endpoint_type, key)
            return True
        return False
