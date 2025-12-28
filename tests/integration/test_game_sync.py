"""Integration tests for game sync functionality."""

import json
import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.game import sync_game
from mlb_stats.collectors.schedule import fetch_schedule
from mlb_stats.collectors.team import sync_team


class TestSyncTeam:
    """Tests for sync_team function."""

    @responses.activate
    def test_inserts_team(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_team: dict,
    ) -> None:
        """Test that sync_team inserts team record."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119",
            json=sample_team,
            status=200,
        )

        sync_team(mock_client, temp_db, 119)

        cursor = temp_db.execute("SELECT name FROM teams WHERE id = 119")
        row = cursor.fetchone()

        assert row is not None
        assert row["name"] == "Los Angeles Dodgers"

    @responses.activate
    def test_updates_existing_team(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_team: dict,
    ) -> None:
        """Test that sync_team updates existing team (upsert)."""
        # First insert
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119",
            json=sample_team,
            status=200,
        )
        sync_team(mock_client, temp_db, 119)

        # Modify and re-sync
        modified_team = json.loads(json.dumps(sample_team))
        modified_team["teams"][0]["name"] = "Updated Dodgers"
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119",
            json=modified_team,
            status=200,
        )
        sync_team(mock_client, temp_db, 119)

        cursor = temp_db.execute("SELECT name FROM teams WHERE id = 119")
        row = cursor.fetchone()

        assert row["name"] == "Updated Dodgers"

        # Verify only one row
        cursor = temp_db.execute("SELECT COUNT(*) FROM teams WHERE id = 119")
        count = cursor.fetchone()[0]
        assert count == 1

    @responses.activate
    def test_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_team: dict,
    ) -> None:
        """Test that synced team includes write metadata."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119",
            json=sample_team,
            status=200,
        )

        sync_team(mock_client, temp_db, 119)

        cursor = temp_db.execute(
            "SELECT _written_at, _git_hash, _version FROM teams WHERE id = 119"
        )
        row = cursor.fetchone()

        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None


class TestFetchSchedule:
    """Tests for fetch_schedule function."""

    @responses.activate
    def test_extracts_game_pks(
        self,
        mock_client: MLBStatsClient,
        sample_schedule: dict,
    ) -> None:
        """Test that fetch_schedule extracts game PKs."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )

        game_pks = fetch_schedule(mock_client, "2024-07-01", "2024-07-01")

        assert 745927 in game_pks

    @responses.activate
    def test_empty_schedule(
        self,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test fetch_schedule with no games."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        game_pks = fetch_schedule(mock_client, "2024-12-25", "2024-12-25")

        assert game_pks == []


class TestSyncGame:
    """Tests for sync_game function."""

    @responses.activate
    def test_syncs_game_with_references(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_venue: dict,
    ) -> None:
        """Test that sync_game creates game with team and venue references.

        Teams are extracted from the game feed itself, eliminating separate API calls.
        Venue is fetched from the API for full details.
        """
        # Mock game feed (contains teams and players)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )
        # Mock venue API call
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        result = sync_game(mock_client, temp_db, 745927)

        assert result is True

        # Verify game inserted
        cursor = temp_db.execute(
            "SELECT gamePk, venue_id FROM games WHERE gamePk = 745927"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["venue_id"] == 22

        # Verify teams inserted as side effect (extracted from game feed)
        cursor = temp_db.execute("SELECT COUNT(*) FROM teams")
        assert cursor.fetchone()[0] == 2

        # Verify venue inserted
        cursor = temp_db.execute("SELECT name FROM venues WHERE id = 22")
        assert cursor.fetchone()["name"] == "Dodger Stadium"

    @responses.activate
    def test_game_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_venue: dict,
    ) -> None:
        """Test that synced game includes write metadata."""
        # Mock game feed (contains teams and players)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )
        # Mock venue API call
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        sync_game(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            "SELECT _written_at, _git_hash, _version FROM games WHERE gamePk = 745927"
        )
        row = cursor.fetchone()

        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None


class TestIdempotentSync:
    """Tests for idempotent re-sync behavior."""

    @responses.activate
    def test_resync_updates_written_at(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_venue: dict,
    ) -> None:
        """Test that re-syncing updates _written_at timestamp."""
        # Mock game feed (twice - once for each sync)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        # First sync
        sync_game(mock_client, temp_db, 745927)
        cursor = temp_db.execute("SELECT _written_at FROM games WHERE gamePk = 745927")
        first_written_at = cursor.fetchone()["_written_at"]

        # Second sync
        import time

        time.sleep(0.01)  # Small delay to ensure different timestamp
        sync_game(mock_client, temp_db, 745927)
        cursor = temp_db.execute("SELECT _written_at FROM games WHERE gamePk = 745927")
        second_written_at = cursor.fetchone()["_written_at"]

        # Timestamps should be different
        assert second_written_at != first_written_at

        # Should still be only one row
        cursor = temp_db.execute("SELECT COUNT(*) FROM games WHERE gamePk = 745927")
        assert cursor.fetchone()[0] == 1
