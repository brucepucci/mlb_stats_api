"""Integration tests for boxscore sync functionality."""

import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.boxscore import sync_boxscore, sync_boxscores_for_date_range
from mlb_stats.collectors.player import sync_player
from mlb_stats.collectors.team import sync_team
from mlb_stats.collectors.venue import sync_venue


def _setup_team_119(mock_client: MLBStatsClient, temp_db: sqlite3.Connection) -> None:
    """Set up team 119 (Dodgers) with its venue for FK constraints."""
    # Mock venue
    responses.add(
        responses.GET,
        f"{BASE_URL}v1/venues/22",
        json={"venues": [{"id": 22, "name": "Dodger Stadium"}]},
        status=200,
    )
    sync_venue(mock_client, temp_db, 22)

    # Mock team
    responses.add(
        responses.GET,
        f"{BASE_URL}v1/teams/119",
        json={
            "teams": [
                {
                    "id": 119,
                    "name": "Los Angeles Dodgers",
                    "active": True,
                    "venue": {"id": 22},
                }
            ]
        },
        status=200,
    )
    sync_team(mock_client, temp_db, 119)
    temp_db.commit()


def _setup_teams_only(mock_client: MLBStatsClient, temp_db: sqlite3.Connection) -> None:
    """Set up both teams (137 Giants and 119 Dodgers) without inserting a game."""
    # Mock venue
    responses.add(
        responses.GET,
        f"{BASE_URL}v1/venues/22",
        json={"venues": [{"id": 22, "name": "Dodger Stadium"}]},
        status=200,
    )
    sync_venue(mock_client, temp_db, 22)

    # Mock Giants team
    responses.add(
        responses.GET,
        f"{BASE_URL}v1/teams/137",
        json={
            "teams": [
                {
                    "id": 137,
                    "name": "San Francisco Giants",
                    "active": True,
                }
            ]
        },
        status=200,
    )
    sync_team(mock_client, temp_db, 137)

    # Mock Dodgers team
    responses.add(
        responses.GET,
        f"{BASE_URL}v1/teams/119",
        json={
            "teams": [
                {
                    "id": 119,
                    "name": "Los Angeles Dodgers",
                    "active": True,
                    "venue": {"id": 22},
                }
            ]
        },
        status=200,
    )
    sync_team(mock_client, temp_db, 119)
    temp_db.commit()


def _setup_both_teams(mock_client: MLBStatsClient, temp_db: sqlite3.Connection) -> None:
    """Set up both teams (137 Giants and 119 Dodgers) AND a game for boxscore FK constraints."""
    _setup_teams_only(mock_client, temp_db)

    # Insert game record (game_batting/game_pitching have FK to games)
    from datetime import datetime, timezone

    from mlb_stats.utils.metadata import get_write_metadata

    game_row = {
        "gamePk": 745927,
        "gameDate": "2024-07-01",
        "gameType": "R",
        "season": 2024,
        "abstractGameState": "Final",
        "detailedState": "Final",
        "away_team_id": 137,
        "home_team_id": 119,
        "venue_id": 22,
        "_fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    game_row.update(get_write_metadata())
    columns = ", ".join(game_row.keys())
    placeholders = ", ".join("?" for _ in game_row)
    temp_db.execute(
        f"INSERT OR REPLACE INTO games ({columns}) VALUES ({placeholders})",
        list(game_row.values()),
    )
    temp_db.commit()


class TestSyncPlayer:
    """Tests for sync_player function."""

    @responses.activate
    def test_inserts_player(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_player: dict,
    ) -> None:
        """Test that sync_player inserts player record."""
        # Set up team for FK constraint
        _setup_team_119(mock_client, temp_db)

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=sample_player,
            status=200,
        )

        sync_player(mock_client, temp_db, 660271)
        temp_db.commit()

        cursor = temp_db.execute("SELECT fullName FROM players WHERE id = 660271")
        row = cursor.fetchone()

        assert row is not None
        assert row["fullName"] == "Shohei Ohtani"

    @responses.activate
    def test_updates_existing_player(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_player: dict,
    ) -> None:
        """Test that sync_player updates existing player (upsert)."""
        # Set up team for FK constraint
        _setup_team_119(mock_client, temp_db)

        # First insert
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=sample_player,
            status=200,
        )
        sync_player(mock_client, temp_db, 660271)
        temp_db.commit()

        # Modify and re-sync
        import json

        modified_player = json.loads(json.dumps(sample_player))
        modified_player["people"][0]["primaryNumber"] = "99"
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=modified_player,
            status=200,
        )
        sync_player(mock_client, temp_db, 660271)
        temp_db.commit()

        cursor = temp_db.execute("SELECT primaryNumber FROM players WHERE id = 660271")
        row = cursor.fetchone()

        assert row["primaryNumber"] == "99"

        # Verify only one row
        cursor = temp_db.execute("SELECT COUNT(*) FROM players WHERE id = 660271")
        count = cursor.fetchone()[0]
        assert count == 1

    @responses.activate
    def test_player_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_player: dict,
    ) -> None:
        """Test that synced player includes write metadata."""
        # Set up team for FK constraint
        _setup_team_119(mock_client, temp_db)

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=sample_player,
            status=200,
        )

        sync_player(mock_client, temp_db, 660271)
        temp_db.commit()

        cursor = temp_db.execute(
            "SELECT _written_at, _git_hash, _version FROM players WHERE id = 660271"
        )
        row = cursor.fetchone()

        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None


class TestSyncBoxscore:
    """Tests for sync_boxscore function."""

    @responses.activate
    def test_syncs_boxscore_with_players(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_boxscore: dict,
    ) -> None:
        """Test that sync_boxscore creates batting/pitching records."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock boxscore endpoint
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints for each player in boxscore
        # Players have no currentTeam_id in this simple test
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
            status=200,
        )

        result = sync_boxscore(mock_client, temp_db, 745927)

        assert result is True

        # Verify batting records created
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_batting WHERE gamePk = 745927"
        )
        batting_count = cursor.fetchone()[0]
        assert batting_count == 1  # One batter in sample

        # Verify pitching records created
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_pitching WHERE gamePk = 745927"
        )
        pitching_count = cursor.fetchone()[0]
        assert pitching_count == 1  # One pitcher in sample

        # Verify players synced
        cursor = temp_db.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        assert player_count == 2

    @responses.activate
    def test_empty_boxscore_returns_false(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test that empty boxscore returns False."""
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
        sample_boxscore: dict,
    ) -> None:
        """Test that batting records have correct data."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock boxscore endpoint
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT player_id, team_id, battingOrder, hits, homeRuns, rbi, avg
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
        assert row["avg"] == ".500"

    @responses.activate
    def test_pitching_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_boxscore: dict,
    ) -> None:
        """Test that pitching records have correct data."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock boxscore endpoint
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
            status=200,
        )

        sync_boxscore(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT player_id, team_id, isStartingPitcher, strikeOuts, era, note
            FROM game_pitching
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()

        assert row["player_id"] == 543243
        assert row["team_id"] == 119  # Home team
        assert row["isStartingPitcher"] == 1
        assert row["strikeOuts"] == 8
        assert row["era"] == "3.00"
        assert row["note"] == "W"

    @responses.activate
    def test_boxscore_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_boxscore: dict,
    ) -> None:
        """Test that batting/pitching records include write metadata."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock boxscore endpoint
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
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


class TestIdempotentBoxscoreSync:
    """Tests for idempotent re-sync behavior."""

    @responses.activate
    def test_resync_is_idempotent(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_boxscore: dict,
    ) -> None:
        """Test that re-syncing boxscore doesn't create duplicates."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock boxscore endpoint (twice)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints (twice each)
        for _ in range(2):
            responses.add(
                responses.GET,
                f"{BASE_URL}v1/people/660271",
                json={
                    "people": [
                        {"id": 660271, "fullName": "Shohei Ohtani", "active": True}
                    ]
                },
                status=200,
            )
            responses.add(
                responses.GET,
                f"{BASE_URL}v1/people/543243",
                json={
                    "people": [
                        {"id": 543243, "fullName": "Test Pitcher", "active": True}
                    ]
                },
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
        sample_boxscore: dict,
        sample_game_feed: dict,
    ) -> None:
        """Test that schedule API is used when no games in database."""
        # Set up teams only (no game) so schedule API gets called
        _setup_teams_only(mock_client, temp_db)

        # Mock schedule
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )

        # Mock game_feed (sync_game is called by sync_boxscore)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        # Mock team endpoints (sync_game fetches teams)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137",
            json={"teams": [{"id": 137, "name": "Giants", "active": True}]},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119",
            json={"teams": [{"id": 119, "name": "Dodgers", "active": True}]},
            status=200,
        )

        # Mock boxscore
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
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
        sample_boxscore: dict,
    ) -> None:
        """Test that progress callback is invoked."""
        # Set up teams for FK constraints
        _setup_both_teams(mock_client, temp_db)

        # Mock schedule
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )

        # Mock boxscore
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/game/745927/boxscore",
            json=sample_boxscore,
            status=200,
        )

        # Mock player endpoints
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json={
                "people": [{"id": 660271, "fullName": "Shohei Ohtani", "active": True}]
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/543243",
            json={
                "people": [{"id": 543243, "fullName": "Test Pitcher", "active": True}]
            },
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
