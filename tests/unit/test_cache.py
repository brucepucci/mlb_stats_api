"""Tests for the ResponseCache class."""

from pathlib import Path

from mlb_stats.api.cache import ResponseCache
from mlb_stats.api.endpoints import CACHEABLE_TYPES


class TestResponseCache:
    """Tests for ResponseCache."""

    def test_cache_write_read_roundtrip(self, response_cache: ResponseCache) -> None:
        """Test that cached data can be written and read back."""
        data = {"gamePk": 12345, "status": "Final"}
        response_cache.set("game_feed", "12345", data)

        result = response_cache.get("game_feed", "12345")
        assert result == data

    def test_cache_returns_none_for_missing_key(
        self, response_cache: ResponseCache
    ) -> None:
        """Test that missing keys return None."""
        result = response_cache.get("game_feed", "nonexistent")
        assert result is None

    def test_cache_directory_structure(self, temp_cache_dir: Path) -> None:
        """Test that cache creates correct directory structure."""
        _cache = ResponseCache(temp_cache_dir)  # noqa: F841

        # Check that directories were created for cacheable types
        for cache_type in CACHEABLE_TYPES:
            assert (temp_cache_dir / cache_type).is_dir()

    def test_cache_rejects_non_cacheable_endpoints(
        self, response_cache: ResponseCache
    ) -> None:
        """Test that non-cacheable endpoints are not cached."""
        data = {"id": 123, "name": "Test"}

        # Players should not be cached
        result = response_cache.set("player", "123", data)
        assert result is False

        # Teams should not be cached
        result = response_cache.set("team", "123", data)
        assert result is False

        # Schedule should not be cached
        result = response_cache.set("schedule", "2024-07-01", data)
        assert result is False

    def test_cache_get_returns_none_for_non_cacheable(
        self, response_cache: ResponseCache
    ) -> None:
        """Test that get returns None for non-cacheable types."""
        result = response_cache.get("player", "123")
        assert result is None

    def test_cache_exists(self, response_cache: ResponseCache) -> None:
        """Test exists method."""
        data = {"test": "data"}
        response_cache.set("game_feed", "12345", data)

        assert response_cache.exists("game_feed", "12345") is True
        assert response_cache.exists("game_feed", "99999") is False
        assert response_cache.exists("player", "12345") is False  # Non-cacheable

    def test_cache_delete(self, response_cache: ResponseCache) -> None:
        """Test delete method."""
        data = {"test": "data"}
        response_cache.set("game_feed", "12345", data)

        assert response_cache.exists("game_feed", "12345") is True
        result = response_cache.delete("game_feed", "12345")
        assert result is True
        assert response_cache.exists("game_feed", "12345") is False

    def test_cache_delete_nonexistent(self, response_cache: ResponseCache) -> None:
        """Test delete returns False for nonexistent key."""
        result = response_cache.delete("game_feed", "nonexistent")
        assert result is False

    def test_all_cacheable_types_work(self, response_cache: ResponseCache) -> None:
        """Test that all cacheable types can be cached."""
        data = {"test": "data"}

        for cache_type in CACHEABLE_TYPES:
            result = response_cache.set(cache_type, "test_key", data)
            assert result is True, f"Failed to cache {cache_type}"

            retrieved = response_cache.get(cache_type, "test_key")
            assert retrieved == data, f"Failed to retrieve {cache_type}"
