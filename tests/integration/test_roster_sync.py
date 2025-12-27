"""Integration tests for roster sync functionality."""

import sqlite3

import responses

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL
from mlb_stats.collectors.roster import sync_game_rosters


class TestSyncGameRosters:
    """Tests for sync_game_rosters function."""

    def _setup_prerequisite_data(self, conn: sqlite3.Connection) -> None:
        """Insert teams and game required for roster sync tests."""
        # Insert teams
        conn.execute(
            """
            INSERT INTO teams (id, name, abbreviation, _fetched_at, _written_at, _git_hash, _version)
            VALUES (119, 'Los Angeles Dodgers', 'LAD', '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        conn.execute(
            """
            INSERT INTO teams (id, name, abbreviation, _fetched_at, _written_at, _git_hash, _version)
            VALUES (137, 'San Francisco Giants', 'SF', '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        # Insert game
        conn.execute(
            """
            INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id,
                _fetched_at, _written_at, _git_hash, _version)
            VALUES (745927, 2024, 'R', '2024-07-01', 137, 119,
                '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        conn.commit()

    def _mock_player_api(self, player_id: int, full_name: str) -> None:
        """Add mock response for player API endpoint."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/{player_id}",
            json={
                "people": [
                    {
                        "id": player_id,
                        "fullName": full_name,
                        "firstName": full_name.split()[0],
                        "lastName": full_name.split()[-1],
                        "active": True,
                        "primaryPosition": {"code": "1", "name": "Pitcher"},
                        "batSide": {"code": "R", "description": "Right"},
                        "pitchHand": {"code": "R", "description": "Right"},
                    }
                ]
            },
            status=200,
        )

    @responses.activate
    def test_syncs_rosters_for_both_teams(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_roster: dict,
    ) -> None:
        """Test that roster sync creates roster entries for both teams."""
        self._setup_prerequisite_data(temp_db)

        # Mock roster endpoints for both teams
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json=sample_roster,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json=sample_roster,
            status=200,
        )

        # Mock player API calls for all roster players
        self._mock_player_api(660271, "Shohei Ohtani")
        self._mock_player_api(543243, "Test Pitcher")
        self._mock_player_api(592450, "Mookie Betts")
        # Each team has same roster, so we need to mock twice
        self._mock_player_api(660271, "Shohei Ohtani")
        self._mock_player_api(543243, "Test Pitcher")
        self._mock_player_api(592450, "Mookie Betts")

        result = sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        assert result is True

        # Verify roster entries created for both teams
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_rosters WHERE gamePk = 745927"
        )
        assert cursor.fetchone()[0] == 6  # 3 players per team x 2 teams

    @responses.activate
    def test_syncs_players_before_roster_insert(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_roster: dict,
    ) -> None:
        """Test that players are synced before roster rows are inserted (FK compliance)."""
        self._setup_prerequisite_data(temp_db)

        # Mock roster endpoint (just one team for simplicity)
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json=sample_roster,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json={"roster": []},  # Empty roster for home team
            status=200,
        )

        # Mock player API calls
        self._mock_player_api(660271, "Shohei Ohtani")
        self._mock_player_api(543243, "Test Pitcher")
        self._mock_player_api(592450, "Mookie Betts")

        result = sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        assert result is True

        # Verify players exist in players table (synced by roster collector)
        cursor = temp_db.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        assert player_count == 3

        # Verify specific player data
        cursor = temp_db.execute("SELECT fullName FROM players WHERE id = 660271")
        row = cursor.fetchone()
        assert row["fullName"] == "Shohei Ohtani"

    @responses.activate
    def test_resync_is_idempotent(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_roster: dict,
    ) -> None:
        """Test that re-syncing rosters doesn't create duplicates."""
        self._setup_prerequisite_data(temp_db)

        # Mock endpoints twice for two syncs
        for _ in range(2):
            responses.add(
                responses.GET,
                f"{BASE_URL}v1/teams/137/roster/active",
                json=sample_roster,
                status=200,
            )
            responses.add(
                responses.GET,
                f"{BASE_URL}v1/teams/119/roster/active",
                json=sample_roster,
                status=200,
            )
            # Mock player API calls
            self._mock_player_api(660271, "Shohei Ohtani")
            self._mock_player_api(543243, "Test Pitcher")
            self._mock_player_api(592450, "Mookie Betts")
            self._mock_player_api(660271, "Shohei Ohtani")
            self._mock_player_api(543243, "Test Pitcher")
            self._mock_player_api(592450, "Mookie Betts")

        # First sync
        sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        # Second sync
        sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        # Should still have only 6 roster entries (3 per team)
        cursor = temp_db.execute(
            "SELECT COUNT(*) FROM game_rosters WHERE gamePk = 745927"
        )
        assert cursor.fetchone()[0] == 6

    @responses.activate
    def test_roster_record_has_correct_data(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_roster: dict,
    ) -> None:
        """Test that roster records have correct data from API."""
        self._setup_prerequisite_data(temp_db)

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json=sample_roster,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json={"roster": []},
            status=200,
        )

        self._mock_player_api(660271, "Shohei Ohtani")
        self._mock_player_api(543243, "Test Pitcher")
        self._mock_player_api(592450, "Mookie Betts")

        sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        cursor = temp_db.execute(
            """
            SELECT player_id, team_id, jerseyNumber, position_code,
                   position_name, position_abbreviation, status_code
            FROM game_rosters
            WHERE gamePk = 745927 AND player_id = 660271
            """
        )
        row = cursor.fetchone()

        assert row["player_id"] == 660271
        assert row["team_id"] == 137  # Away team
        assert row["jerseyNumber"] == "17"
        assert row["position_code"] == "Y"
        assert row["position_name"] == "Two-Way Player"
        assert row["position_abbreviation"] == "TWP"
        assert row["status_code"] == "A"

    @responses.activate
    def test_roster_includes_write_metadata(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        sample_roster: dict,
    ) -> None:
        """Test that roster records include write metadata."""
        self._setup_prerequisite_data(temp_db)

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json=sample_roster,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json={"roster": []},
            status=200,
        )

        self._mock_player_api(660271, "Shohei Ohtani")
        self._mock_player_api(543243, "Test Pitcher")
        self._mock_player_api(592450, "Mookie Betts")

        sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        cursor = temp_db.execute(
            """
            SELECT _fetched_at, _written_at, _git_hash, _version
            FROM game_rosters
            WHERE gamePk = 745927
            LIMIT 1
            """
        )
        row = cursor.fetchone()

        assert row["_fetched_at"] is not None
        assert row["_written_at"] is not None
        assert row["_git_hash"] is not None
        assert row["_version"] is not None

    @responses.activate
    def test_empty_roster_logs_warning(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
        caplog,
    ) -> None:
        """Test that empty roster logs a warning."""
        self._setup_prerequisite_data(temp_db)

        # Mock empty rosters for both teams
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json={"roster": []},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json={"roster": []},
            status=200,
        )

        result = sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        assert result is True  # Still succeeds, just logs warning

        # Verify warning was logged
        assert "No roster entries found for game 745927" in caplog.text

    @responses.activate
    def test_api_error_returns_false(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test that API errors return False."""
        self._setup_prerequisite_data(temp_db)

        # Mock API error
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json={"error": "Server error"},
            status=500,
        )

        result = sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        assert result is False


class TestRosterPlayerSync:
    """Tests specifically for player sync during roster sync."""

    def _setup_prerequisite_data(self, conn: sqlite3.Connection) -> None:
        """Insert teams and game required for roster sync tests."""
        conn.execute(
            """
            INSERT INTO teams (id, name, abbreviation, _fetched_at, _written_at, _git_hash, _version)
            VALUES (119, 'Los Angeles Dodgers', 'LAD', '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        conn.execute(
            """
            INSERT INTO teams (id, name, abbreviation, _fetched_at, _written_at, _git_hash, _version)
            VALUES (137, 'San Francisco Giants', 'SF', '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        conn.execute(
            """
            INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id,
                _fetched_at, _written_at, _git_hash, _version)
            VALUES (745927, 2024, 'R', '2024-07-01', 137, 119,
                '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')
            """
        )
        conn.commit()

    @responses.activate
    def test_roster_only_player_gets_synced(
        self,
        temp_db: sqlite3.Connection,
        mock_client: MLBStatsClient,
    ) -> None:
        """Test that players only on roster (not in boxscore) get synced.

        This is the critical fix - bench players who don't play but are
        on the roster should have their player record created to satisfy
        the foreign key constraint.
        """
        self._setup_prerequisite_data(temp_db)

        # Roster with a player who might not be in boxscore
        bench_player_roster = {
            "roster": [
                {
                    "person": {"id": 999999, "fullName": "Bench Player"},
                    "jerseyNumber": "99",
                    "position": {
                        "code": "7",
                        "name": "Left Field",
                        "type": "Outfielder",
                        "abbreviation": "LF",
                    },
                    "status": {"code": "A", "description": "Active"},
                }
            ]
        }

        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/137/roster/active",
            json=bench_player_roster,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/teams/119/roster/active",
            json={"roster": []},
            status=200,
        )

        # Mock player API for bench player
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/999999",
            json={
                "people": [
                    {
                        "id": 999999,
                        "fullName": "Bench Player",
                        "firstName": "Bench",
                        "lastName": "Player",
                        "active": True,
                        "primaryPosition": {"code": "7", "name": "Left Field"},
                        "batSide": {"code": "R", "description": "Right"},
                        "pitchHand": {"code": "R", "description": "Right"},
                    }
                ]
            },
            status=200,
        )

        result = sync_game_rosters(mock_client, temp_db, 745927, "2024-07-01", 137, 119)

        assert result is True

        # Verify player was synced (this would fail before the fix)
        cursor = temp_db.execute("SELECT fullName FROM players WHERE id = 999999")
        row = cursor.fetchone()
        assert row is not None
        assert row["fullName"] == "Bench Player"

        # Verify roster entry was created (this would fail FK constraint before fix)
        cursor = temp_db.execute(
            "SELECT player_id FROM game_rosters WHERE gamePk = 745927 AND player_id = 999999"
        )
        row = cursor.fetchone()
        assert row is not None
