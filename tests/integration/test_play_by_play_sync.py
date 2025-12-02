"""Integration tests for play-by-play sync functionality."""

import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.play_by_play import sync_play_by_play


class TestSyncPlayByPlay:
    """Tests for sync_play_by_play function."""

    @responses.activate
    def test_syncs_pitches_and_at_bats(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that sync_play_by_play creates pitch and at-bat records."""
        # Mock game feed with play data
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        # First sync teams and players (required for foreign keys)
        _setup_teams_and_players(temp_db)

        result = sync_play_by_play(mock_client, temp_db, 745927)

        assert result is True

        # Verify at-bat records created (2 at-bats in sample)
        cursor = temp_db.execute("SELECT COUNT(*) FROM at_bats WHERE gamePk = 745927")
        at_bat_count = cursor.fetchone()[0]
        assert at_bat_count == 2

        # Verify pitch records created (6 pitches: 4 + 2)
        cursor = temp_db.execute("SELECT COUNT(*) FROM pitches WHERE gamePk = 745927")
        pitch_count = cursor.fetchone()[0]
        assert pitch_count == 6

        # Verify batted ball record created (1 ball in play)
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM batted_balls WHERE gamePk = 745927"
        )
        batted_ball_count = cursor.fetchone()[0]
        assert batted_ball_count == 1

    @responses.activate
    def test_pitch_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that pitch records have correct data."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        _setup_teams_and_players(temp_db)

        sync_play_by_play(mock_client, temp_db, 745927)

        # Check first pitch
        cursor = temp_db.execute(
            """
            SELECT gamePk, atBatIndex, pitchNumber, inning, halfInning,
                   batter_id, pitcher_id, call_code, type_code, startSpeed,
                   spinRate, plateX, plateZ
            FROM pitches
            WHERE gamePk = 745927 AND atBatIndex = 0 AND pitchNumber = 1
            """
        )
        row = cursor.fetchone()

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 0
        assert row["pitchNumber"] == 1
        assert row["inning"] == 1
        assert row["halfInning"] == "top"
        assert row["batter_id"] == 660271
        assert row["pitcher_id"] == 543243
        assert row["call_code"] == "B"
        assert row["type_code"] == "FF"
        assert row["startSpeed"] == 95.0
        assert row["spinRate"] == 2400
        assert row["plateX"] == -1.5
        assert row["plateZ"] == 3.3

    @responses.activate
    def test_at_bat_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that at-bat records have correct data."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        _setup_teams_and_players(temp_db)

        sync_play_by_play(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT gamePk, atBatIndex, inning, halfInning,
                   batter_id, pitcher_id, event, eventType, pitchCount
            FROM at_bats
            WHERE gamePk = 745927 AND atBatIndex = 0
            """
        )
        row = cursor.fetchone()

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 0
        assert row["inning"] == 1
        assert row["halfInning"] == "top"
        assert row["batter_id"] == 660271
        assert row["pitcher_id"] == 543243
        assert row["event"] == "Strikeout"
        assert row["eventType"] == "strikeout"
        assert row["pitchCount"] == 4

    @responses.activate
    def test_batted_ball_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that batted ball records have correct data."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        _setup_teams_and_players(temp_db)

        sync_play_by_play(mock_client, temp_db, 745927)

        cursor = temp_db.execute(
            """
            SELECT gamePk, atBatIndex, pitchNumber, batter_id, pitcher_id,
                   launchSpeed, launchAngle, totalDistance, trajectory, event
            FROM batted_balls
            WHERE gamePk = 745927
            """
        )
        row = cursor.fetchone()

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 1
        assert row["pitchNumber"] == 2
        assert row["batter_id"] == 543243
        assert row["pitcher_id"] == 660271
        assert row["launchSpeed"] == 95.0
        assert row["launchAngle"] == 15
        assert row["totalDistance"] == 250
        assert row["trajectory"] == "line_drive"
        assert row["event"] == "Single"

    @responses.activate
    def test_no_play_data_returns_false(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test that empty play data returns False."""
        game_feed = {
            "gamePk": 745927,
            "gameData": {},
            "liveData": {"plays": {"allPlays": []}},
        }

        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=game_feed,
            status=200,
        )

        result = sync_play_by_play(mock_client, temp_db, 745927)

        assert result is False

    @responses.activate
    def test_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that all records include write metadata."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        _setup_teams_and_players(temp_db)

        sync_play_by_play(mock_client, temp_db, 745927)

        # Check pitch metadata
        cursor = temp_db.execute(
            """
            SELECT _written_at, _git_hash, _version, _fetched_at
            FROM pitches WHERE gamePk = 745927 LIMIT 1
            """
        )
        row = cursor.fetchone()
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None
        assert row["_fetched_at"] is not None

        # Check at_bat metadata
        cursor = temp_db.execute(
            """
            SELECT _written_at, _git_hash, _version, _fetched_at
            FROM at_bats WHERE gamePk = 745927 LIMIT 1
            """
        )
        row = cursor.fetchone()
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None
        assert row["_fetched_at"] is not None

        # Check batted_ball metadata
        cursor = temp_db.execute(
            """
            SELECT _written_at, _git_hash, _version, _fetched_at
            FROM batted_balls WHERE gamePk = 745927 LIMIT 1
            """
        )
        row = cursor.fetchone()
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None
        assert row["_fetched_at"] is not None


class TestIdempotentPlayByPlaySync:
    """Tests for idempotent re-sync behavior."""

    @responses.activate
    def test_resync_is_idempotent(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_game_feed: dict,
    ) -> None:
        """Test that re-syncing doesn't create duplicates."""
        # Mock twice for two syncs
        for _ in range(2):
            responses.add(
                responses.GET,
                f"{BASE_URL}v1.1/game/745927/feed/live",
                json=sample_game_feed,
                status=200,
            )

        _setup_teams_and_players(temp_db)

        # First sync
        sync_play_by_play(mock_client, temp_db, 745927)

        # Second sync
        sync_play_by_play(mock_client, temp_db, 745927)

        # Should still have same counts
        cursor = temp_db.execute("SELECT COUNT(*) FROM at_bats WHERE gamePk = 745927")
        assert cursor.fetchone()[0] == 2

        cursor = temp_db.execute("SELECT COUNT(*) FROM pitches WHERE gamePk = 745927")
        assert cursor.fetchone()[0] == 6

        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM batted_balls WHERE gamePk = 745927"
        )
        assert cursor.fetchone()[0] == 1


def _setup_teams_and_players(conn: sqlite3.Connection) -> None:
    """Helper to set up required reference data for foreign keys."""
    # Insert teams
    conn.execute(
        """
        INSERT OR REPLACE INTO teams (id, name, _fetched_at, _written_at, _git_hash, _version)
        VALUES (137, 'San Francisco Giants', '2024-01-01', '2024-01-01', 'test', '1.0.0'),
               (119, 'Los Angeles Dodgers', '2024-01-01', '2024-01-01', 'test', '1.0.0')
        """
    )

    # Insert players
    conn.execute(
        """
        INSERT OR REPLACE INTO players (id, fullName, _fetched_at, _written_at, _git_hash, _version)
        VALUES (660271, 'Shohei Ohtani', '2024-01-01', '2024-01-01', 'test', '1.0.0'),
               (543243, 'Test Pitcher', '2024-01-01', '2024-01-01', 'test', '1.0.0')
        """
    )

    # Insert game (required for pitch foreign key)
    conn.execute(
        """
        INSERT OR REPLACE INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id,
                                      _fetched_at, _written_at, _git_hash, _version)
        VALUES (745927, 2024, 'R', '2024-07-01', 137, 119, '2024-01-01', '2024-01-01', 'test', '1.0.0')
        """
    )

    conn.commit()
