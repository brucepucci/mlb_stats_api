"""Integration tests for venue sync functionality."""

import sqlite3
from datetime import datetime, timezone

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.venue import sync_venue
from mlb_stats.db.queries import venue_needs_refresh

# Current year for year-based caching tests
CURRENT_YEAR = datetime.now(timezone.utc).year


class TestSyncVenue:
    """Tests for sync_venue function."""

    @responses.activate
    def test_inserts_venue(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue inserts venue record."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        cursor = temp_db.execute(
            "SELECT name, city, year FROM venues WHERE id = 22 AND year = ?",
            (CURRENT_YEAR,),
        )
        row = cursor.fetchone()

        assert row is not None
        assert row["name"] == "Dodger Stadium"
        assert row["city"] == "Los Angeles"
        assert row["year"] == CURRENT_YEAR

    @responses.activate
    def test_creates_separate_row_for_different_year(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue creates separate rows for different years."""
        # First insert for current year
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        # Sync for next year (should create a new row)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR + 1)

        # Verify two rows exist (one per year)
        cursor = temp_db.execute("SELECT COUNT(*) FROM venues WHERE id = 22")
        count = cursor.fetchone()[0]
        assert count == 2

        # Verify both years are present
        cursor = temp_db.execute("SELECT year FROM venues WHERE id = 22 ORDER BY year")
        years = [row["year"] for row in cursor.fetchall()]
        assert years == [CURRENT_YEAR, CURRENT_YEAR + 1]

    @responses.activate
    def test_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that synced venue includes write metadata."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        cursor = temp_db.execute(
            "SELECT _written_at, _git_hash, _version FROM venues WHERE id = 22 AND year = ?",
            (CURRENT_YEAR,),
        )
        row = cursor.fetchone()

        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None

    @responses.activate
    def test_stores_field_info(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue stores field dimensions and info."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        cursor = temp_db.execute(
            """SELECT capacity, turfType, roofType,
                      leftLine, leftCenter, center, rightCenter, rightLine
               FROM venues WHERE id = 22 AND year = ?""",
            (CURRENT_YEAR,),
        )
        row = cursor.fetchone()

        assert row["capacity"] == 56000
        assert row["turfType"] == "Grass"
        assert row["roofType"] == "Open"
        assert row["leftLine"] == 330
        assert row["leftCenter"] == 385
        assert row["center"] == 395
        assert row["rightCenter"] == 385
        assert row["rightLine"] == 330

    @responses.activate
    def test_stores_location_info(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue stores location data."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        cursor = temp_db.execute(
            """SELECT city, state, stateAbbrev, country,
                      latitude, longitude, elevation
               FROM venues WHERE id = 22 AND year = ?""",
            (CURRENT_YEAR,),
        )
        row = cursor.fetchone()

        assert row["city"] == "Los Angeles"
        assert row["state"] == "California"
        assert row["stateAbbrev"] == "CA"
        assert row["country"] == "USA"
        assert row["latitude"] == 34.07368
        assert row["longitude"] == -118.24053
        assert row["elevation"] == 515

    @responses.activate
    def test_stores_timezone_info(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue stores timezone data."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        cursor = temp_db.execute(
            """SELECT timeZone_id, timeZone_offset, timeZone_tz
               FROM venues WHERE id = 22 AND year = ?""",
            (CURRENT_YEAR,),
        )
        row = cursor.fetchone()

        assert row["timeZone_id"] == "America/Los_Angeles"
        assert row["timeZone_offset"] == -8
        assert row["timeZone_tz"] == "PST"

    @responses.activate
    def test_skips_api_call_when_same_year(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue skips API call when venue exists for same year."""
        # First sync (API call made)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        # Verify API was called
        assert len(responses.calls) == 1

        # Second sync for same year (should skip API call)
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        # Verify no additional API call
        assert len(responses.calls) == 1

    @responses.activate
    def test_makes_api_call_when_different_year(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue makes API call for different year."""
        # First sync for current year
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)
        assert len(responses.calls) == 1

        # Second sync for next year (should make new API call)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR + 1)
        assert len(responses.calls) == 2


class TestVenueNeedsRefresh:
    """Tests for venue_needs_refresh function."""

    def test_returns_true_when_venue_not_in_db(
        self,
        temp_db: sqlite3.Connection,
    ) -> None:
        """Test that venue_needs_refresh returns True for non-existent venue."""
        assert venue_needs_refresh(temp_db, 999, CURRENT_YEAR) is True

    @responses.activate
    def test_returns_false_when_venue_exists_for_year(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that venue_needs_refresh returns False when venue exists for year."""
        # Insert venue for current year
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        # Check for same year (should not need refresh)
        assert venue_needs_refresh(temp_db, 22, CURRENT_YEAR) is False

    @responses.activate
    def test_returns_true_when_venue_not_exists_for_year(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that venue_needs_refresh returns True when venue doesn't exist for year."""
        # Insert venue for current year
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22, CURRENT_YEAR)

        # Check for different years (should need refresh - separate rows per year)
        assert venue_needs_refresh(temp_db, 22, CURRENT_YEAR + 1) is True
        assert venue_needs_refresh(temp_db, 22, CURRENT_YEAR - 1) is True
