"""Tests for the metadata utility functions."""

from datetime import datetime, timezone

from mlb_stats.utils.metadata import get_git_hash, get_write_metadata


class TestGetGitHash:
    """Tests for get_git_hash function."""

    def test_returns_string(self) -> None:
        """Test that get_git_hash returns a string."""
        result = get_git_hash()
        assert isinstance(result, str)

    def test_returns_non_empty(self) -> None:
        """Test that get_git_hash returns a non-empty string."""
        result = get_git_hash()
        assert len(result) > 0

    def test_returns_valid_hash_or_unknown(self) -> None:
        """Test that result is either a valid hash or 'unknown'."""
        result = get_git_hash()
        # Either 'unknown' or a short hex hash (typically 7 chars)
        if result != "unknown":
            assert len(result) >= 7
            assert all(c in "0123456789abcdef" for c in result)


class TestGetWriteMetadata:
    """Tests for get_write_metadata function."""

    def test_contains_required_keys(self) -> None:
        """Test that metadata contains all required keys."""
        metadata = get_write_metadata()
        assert "_written_at" in metadata
        assert "_git_hash" in metadata
        assert "_version" in metadata

    def test_written_at_is_valid_iso8601(self) -> None:
        """Test that _written_at is a valid ISO8601 timestamp."""
        metadata = get_write_metadata()
        written_at = metadata["_written_at"]

        # Should be parseable as ISO8601
        parsed = datetime.fromisoformat(written_at.replace("Z", "+00:00"))
        assert parsed is not None

    def test_version_is_string(self) -> None:
        """Test that _version is a string."""
        metadata = get_write_metadata()
        assert isinstance(metadata["_version"], str)
        assert len(metadata["_version"]) > 0

    def test_git_hash_is_string(self) -> None:
        """Test that _git_hash is a string."""
        metadata = get_write_metadata()
        assert isinstance(metadata["_git_hash"], str)

    def test_written_at_is_recent(self) -> None:
        """Test that _written_at is a recent timestamp."""
        before = datetime.now(timezone.utc).isoformat()
        metadata = get_write_metadata()
        after = datetime.now(timezone.utc).isoformat()

        written_at = metadata["_written_at"]

        # All should be comparable as ISO8601 strings
        assert before[:19] <= written_at[:19] <= after[:19]
