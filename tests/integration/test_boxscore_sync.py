"""Integration tests for boxscore sync functionality."""

import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.boxscore import sync_boxscore, sync_boxscores_for_date_range


class TestSyncBoxscore:
    """Tests for sync_boxscore function."""

    @responses.activate
    def test_syncs_boxscore_with_players(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that sync_boxscore creates batting/pitching records."""
        # Mock game feed (has teams and players)
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

        # Mock boxscore (has batting/pitching stats)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        result = sync_boxscore(mock_client, temp_db, 745927)

        assert result is True

        # Verify batting records created
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_batting WHERE gamePk = 745927"
        )
        batting_count = cursor.fetchone()[0]
        assert batting_count == 1

        # Verify pitching records created
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_pitching WHERE gamePk = 745927"
        )
        pitching_count = cursor.fetchone()[0]
        assert pitching_count == 1

        # Verify players synced (from game feed)
        cursor = temp_db.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        assert player_count == 2

        # Verify teams synced (from game feed)
        cursor = temp_db.execute("SELECT COUNT(*) FROM teams")
        team_count = cursor.fetchone()[0]
        assert team_count == 2

    @responses.activate
    def test_empty_boxscore_returns_false(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_venue: dict,
    ) -> None:
        """Test that empty boxscore returns False."""
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
            f"{BASE_URL}v1/game/745927/boxscore",
            json={"teams": {"away": {"players": {}}, "home": {"players": {}}}},
            status=200,
        )

        result = sync_boxscore(mock_client, temp_db, 745927)

        assert result is False

    @responses.activate
    def test_batting_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that batting records have correct data."""
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
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT player_id, team_id, battingOrder, hits, homeRuns, rbi
            FROM game_batting
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()

        assert row["player_id"] == 660271
        assert row["team_id"] == 137  # Away team
        assert row["battingOrder"] == 100
        assert row["hits"] == 2
        assert row["homeRuns"] == 1
        assert row["rbi"] == 2

    @responses.activate
    def test_pitching_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that pitching records have correct data."""
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
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT player_id, team_id, isStartingPitcher, strikeOuts, note
            FROM game_pitching
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()

        assert row["player_id"] == 543243
        assert row["team_id"] == 119  # Home team
        assert row["isStartingPitcher"] == 1
        assert row["strikeOuts"] == 8
        assert row["note"] == "(W, 5-2)"

    @responses.activate
    def test_boxscore_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that batting/pitching records include write metadata."""
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
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        # Check batting metadata
        cursor = temp_db.execute(
            """
            SELECT _written_at, _git_hash, _version
            FROM game_batting
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None

        # Check pitching metadata
        cursor = temp_db.execute(
            """
            SELECT _written_at, _git_hash, _version
            FROM game_pitching
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None

    @responses.activate
    def test_player_data_extracted_from_game_feed(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that player data is correctly extracted from game feed."""
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
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        # Check player data was extracted correctly
        cursor = temp_db.execute(
            "SELECT fullName, birthCity, birthCountry, primaryPosition_code "
            "FROM players WHERE id = 660271"
        )
        row = cursor.fetchone()

        assert row["fullName"] == "Shohei Ohtani"
        assert row["birthCity"] == "Oshu"
        assert row["birthCountry"] == "Japan"
        assert row["primaryPosition_code"] == "Y"  # Two-way player


class TestIdempotentBoxscoreSync:
    """Tests for idempotent re-sync behavior."""

    @responses.activate
    def test_resync_is_idempotent(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that re-syncing boxscore doesn't create duplicates."""
        # Mock endpoints twice
        for _ in range(2):
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
                f"{BASE_URL}v1/game/745927/boxscore",
                json=sample_boxscore,
                status=200,
            )

        # First sync
        sync_boxscore(mock_client, temp_db, 745927)

        # Second sync
        sync_boxscore(mock_client, temp_db, 745927)

        # Should still have only one batting record per player
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_batting WHERE gamePk = 745927"
        )
        assert cursor.fetchone()[0] == 1

        # Should still have only one pitching record per player
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_pitching WHERE gamePk = 745927"
        )
        assert cursor.fetchone()[0] == 1


class TestSyncBoxscoresForDateRange:
    """Tests for sync_boxscores_for_date_range function."""

    @responses.activate
    def test_fetches_from_schedule_when_no_games_in_db(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_schedule: dict,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that schedule API is used when no games in database."""
        # Mock schedule
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )

        # Mock game feed
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        # Mock venue
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/venues/22",
            json=sample_venue,
            status=200,
        )

        # Mock boxscore
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        success, failures = sync_boxscores_for_date_range(
            mock_client, temp_db, "2024-07-01", "2024-07-01"
        )

        assert success == 1
        assert failures == 0

        # Schedule should have been called
        schedule_calls = [
            c for c in responses.calls if "schedule" in str(c.request.url)
        ]
        assert len(schedule_calls) == 1

    @responses.activate
    def test_empty_date_range(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test sync with no games in date range."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        success, failures = sync_boxscores_for_date_range(
            mock_client, temp_db, "2024-12-25", "2024-12-25"
        )

        assert success == 0
        assert failures == 0

    @responses.activate
    def test_progress_callback_called(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_schedule: dict,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that progress callback is invoked."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
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

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        progress_calls = []

        def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        sync_boxscores_for_date_range(
            mock_client,
            temp_db,
            "2024-07-01",
            "2024-07-01",
            progress_callback=track_progress,
        )

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)

    @responses.activate
    def test_force_refresh_always_calls_schedule_api(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_schedule: dict,
        sample_game_feed: dict,
        sample_boxscore: dict,
        sample_venue: dict,
    ) -> None:
        """Test that force_refresh=True always fetches from schedule API."""
        # First sync without force_refresh to populate DB
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
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
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        sync_boxscores_for_date_range(mock_client, temp_db, "2024-07-01", "2024-07-01")

        # Now DB has game 745927. Without force_refresh, schedule API wouldn't be called.
        # With force_refresh=True, schedule API should be called again.

        # Add mocks for second sync
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
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
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Count schedule calls before
        schedule_calls_before = len(
            [c for c in responses.calls if "schedule" in str(c.request.url)]
        )

        # Sync with force_refresh
        success, failures = sync_boxscores_for_date_range(
            mock_client,
            temp_db,
            "2024-07-01",
            "2024-07-01",
            force_refresh=True,
        )

        assert success == 1
        assert failures == 0

        # Verify schedule API was called again (force_refresh bypassed DB check)
        schedule_calls_after = len(
            [c for c in responses.calls if "schedule" in str(c.request.url)]
        )
        assert schedule_calls_after == schedule_calls_before + 1
