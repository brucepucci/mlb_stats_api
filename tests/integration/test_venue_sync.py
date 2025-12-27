"""Integration tests for venue sync functionality."""

import json
import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.venue import sync_venue


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

        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute("SELECT name, city FROM venues WHERE id = 22")
        row = cursor.fetchone()

        assert row is not None
        assert row["name"] == "Dodger Stadium"
        assert row["city"] == "Los Angeles"

    @responses.activate
    def test_updates_existing_venue(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_venue: dict,
    ) -> None:
        """Test that sync_venue updates existing venue (upsert)."""
        # First insert
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22)

        # Modify capacity and re-sync
        modified_venue = json.loads(json.dumps(sample_venue))
        modified_venue["venues"][0]["fieldInfo"]["capacity"] = 60000
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=modified_venue,
            status=200,
        )
        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute("SELECT capacity FROM venues WHERE id = 22")
        row = cursor.fetchone()

        assert row["capacity"] == 60000

        # Verify only one row
        cursor = temp_db.execute("SELECT COUNT(*) FROM venues WHERE id = 22")
        count = cursor.fetchone()[0]
        assert count == 1

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

        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute(
            "SELECT _written_at, _git_hash, _version FROM venues WHERE id = 22"
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

        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute(
            """SELECT capacity, turfType, roofType,
                      leftLine, leftCenter, center, rightCenter, rightLine
               FROM venues WHERE id = 22"""
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

        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute(
            """SELECT city, state, stateAbbrev, country,
                      latitude, longitude, elevation
               FROM venues WHERE id = 22"""
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

        sync_venue(mock_client, temp_db, 22)

        cursor = temp_db.execute(
            """SELECT timeZone_id, timeZone_offset, timeZone_tz
               FROM venues WHERE id = 22"""
        )
        row = cursor.fetchone()

        assert row["timeZone_id"] == "America/Los_Angeles"
        assert row["timeZone_offset"] == -8
        assert row["timeZone_tz"] == "PST"
