"""Tests for the database schema."""

import sqlite3

import pytest

from mlb_stats.db.connection import get_schema_version, table_exists
from mlb_stats.db.schema import SCHEMA_VERSION, get_table_names


class TestCreateTables:
    """Tests for create_tables function."""

    def test_all_tables_created(self, temp_db: sqlite3.Connection) -> None:
        """Test that all 10 tables plus _meta are created."""
        cursor = temp_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        # Exclude sqlite_sequence (internal SQLite table for AUTOINCREMENT)
        tables = {row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"}

        expected_tables = set(get_table_names())
        assert tables == expected_tables

    def test_meta_table_has_schema_version(self, temp_db: sqlite3.Connection) -> None:
        """Test that _meta table has schema_version."""
        version = get_schema_version(temp_db)
        assert version == SCHEMA_VERSION

    def test_table_count(self, temp_db: sqlite3.Connection) -> None:
        """Test that exactly 11 tables are created (excluding SQLite internals)."""
        cursor = temp_db.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' "
            "AND name != 'sqlite_sequence'"
        )
        count = cursor.fetchone()[0]
        assert count == 11  # 10 data tables + _meta

    def test_indices_created(self, temp_db: sqlite3.Connection) -> None:
        """Test that indices are created."""
        cursor = temp_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indices = [row[0] for row in cursor.fetchall()]

        # Check some key indices exist
        assert "idx_games_date" in indices
        assert "idx_pitches_gamepk" in indices
        assert "idx_game_batting_player" in indices


class TestTableExists:
    """Tests for table_exists function."""

    def test_existing_table(self, temp_db: sqlite3.Connection) -> None:
        """Test that existing tables are detected."""
        assert table_exists(temp_db, "games") is True
        assert table_exists(temp_db, "pitches") is True
        assert table_exists(temp_db, "_meta") is True

    def test_nonexistent_table(self, temp_db: sqlite3.Connection) -> None:
        """Test that nonexistent tables return False."""
        assert table_exists(temp_db, "nonexistent") is False


class TestSchemaVersion:
    """Tests for schema versioning."""

    def test_schema_version_format(self) -> None:
        """Test that schema version is semver format."""
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_schema_version_returns_correct_value(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that get_schema_version returns the correct value."""
        version = get_schema_version(temp_db)
        assert version == SCHEMA_VERSION


class TestTableStructure:
    """Tests for individual table structures."""

    def test_games_table_columns(self, temp_db: sqlite3.Connection) -> None:
        """Test that games table has required columns."""
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA table_info(games)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "gamePk",
            "season",
            "gameType",
            "gameDate",
            "away_team_id",
            "home_team_id",
            "_written_at",
            "_git_hash",
            "_version",
        }
        assert required_columns.issubset(columns)

    def test_pitches_table_has_statcast_columns(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that pitches table has Statcast columns."""
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA table_info(pitches)")
        columns = {row[1] for row in cursor.fetchall()}

        statcast_columns = {
            "spinRate",
            "spinDirection",
            "extension",
            "plateTime",
            "breakAngle",
            "breakLength",
        }
        assert statcast_columns.issubset(columns)

    def test_batted_balls_table_columns(self, temp_db: sqlite3.Connection) -> None:
        """Test that batted_balls table has required columns."""
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA table_info(batted_balls)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "gamePk",
            "launchSpeed",
            "launchAngle",
            "totalDistance",
            "trajectory",
        }
        assert required_columns.issubset(columns)

    def test_all_tables_have_write_metadata(self, temp_db: sqlite3.Connection) -> None:
        """Test that all tables have write metadata columns."""
        # Exclude _meta which has different structure
        tables = [t for t in get_table_names() if t != "_meta"]

        for table in tables:
            cursor = temp_db.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {row[1] for row in cursor.fetchall()}

            assert "_written_at" in columns, f"{table} missing _written_at"
            assert "_git_hash" in columns, f"{table} missing _git_hash"
            assert "_version" in columns, f"{table} missing _version"


class TestBooleanConstraints:
    """Tests for CHECK constraints on boolean INTEGER fields."""

    def test_teams_active_accepts_valid_values(self, temp_db: sqlite3.Connection) -> None:
        """Test that teams.active accepts 0 and 1."""
        cursor = temp_db.cursor()

        # Test valid value 1
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        # Test valid value 0
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (2, 'Test Team 2', 0, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        temp_db.commit()

        # Verify both were inserted
        cursor.execute("SELECT COUNT(*) FROM teams")
        assert cursor.fetchone()[0] == 2

    def test_teams_active_rejects_invalid_values(self, temp_db: sqlite3.Connection) -> None:
        """Test that teams.active rejects values other than 0 and 1."""
        cursor = temp_db.cursor()

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
                "VALUES (1, 'Test Team', 2, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
            )

    def test_players_active_accepts_valid_values(self, temp_db: sqlite3.Connection) -> None:
        """Test that players.active accepts 0 and 1."""
        cursor = temp_db.cursor()

        # Insert test data
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Player', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (2, 'Test Player 2', 0, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        temp_db.commit()

        cursor.execute("SELECT COUNT(*) FROM players")
        assert cursor.fetchone()[0] == 2

    def test_players_active_rejects_invalid_values(self, temp_db: sqlite3.Connection) -> None:
        """Test that players.active rejects values other than 0 and 1."""
        cursor = temp_db.cursor()

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
                "VALUES (1, 'Test Player', -1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
            )

    def test_game_pitching_isStartingPitcher_accepts_valid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that game_pitching.isStartingPitcher accepts 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Pitcher', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        # Test valid value 1
        cursor.execute(
            "INSERT INTO game_pitching (gamePk, player_id, team_id, isStartingPitcher, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 1, 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        temp_db.commit()

        cursor.execute("SELECT isStartingPitcher FROM game_pitching WHERE gamePk = 1")
        assert cursor.fetchone()[0] == 1

    def test_game_pitching_isStartingPitcher_rejects_invalid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that game_pitching.isStartingPitcher rejects values other than 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Pitcher', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO game_pitching (gamePk, player_id, team_id, isStartingPitcher, "
                "_fetched_at, _written_at, _git_hash, _version) "
                "VALUES (1, 1, 1, 5, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
            )

    def test_pitches_boolean_fields_accept_valid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that pitches boolean fields accept 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Player', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        # Test valid values
        cursor.execute(
            "INSERT INTO pitches (gamePk, atBatIndex, pitchNumber, inning, halfInning, "
            "batter_id, pitcher_id, isInPlay, isStrike, isBall, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 0, 1, 1, 'top', 1, 1, 1, 0, 0, "
            "'2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        temp_db.commit()

        cursor.execute("SELECT isInPlay, isStrike, isBall FROM pitches WHERE gamePk = 1")
        result = cursor.fetchone()
        assert result == (1, 0, 0)

    def test_pitches_isInPlay_rejects_invalid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that pitches.isInPlay rejects values other than 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Player', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO pitches (gamePk, atBatIndex, pitchNumber, inning, halfInning, "
                "batter_id, pitcher_id, isInPlay, isStrike, isBall, "
                "_fetched_at, _written_at, _git_hash, _version) "
                "VALUES (1, 0, 1, 1, 'top', 1, 1, 3, 0, 0, "
                "'2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
            )

    def test_at_bats_boolean_fields_accept_valid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that at_bats boolean fields accept 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Player', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        # Test valid values
        cursor.execute(
            "INSERT INTO at_bats (gamePk, atBatIndex, inning, halfInning, batter_id, pitcher_id, "
            "isComplete, hasReview, hasOut, isScoringPlay, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 0, 1, 'top', 1, 1, 1, 0, 1, 0, "
            "'2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        temp_db.commit()

        cursor.execute(
            "SELECT isComplete, hasReview, hasOut, isScoringPlay FROM at_bats WHERE gamePk = 1"
        )
        result = cursor.fetchone()
        assert result == (1, 0, 1, 0)

    def test_at_bats_isComplete_rejects_invalid_values(
        self, temp_db: sqlite3.Connection
    ) -> None:
        """Test that at_bats.isComplete rejects values other than 0 and 1."""
        cursor = temp_db.cursor()

        # Create prerequisite data
        cursor.execute(
            "INSERT INTO teams (id, name, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Team', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO players (id, fullName, active, _fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 'Test Player', 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )
        cursor.execute(
            "INSERT INTO games (gamePk, season, gameType, gameDate, away_team_id, home_team_id, "
            "_fetched_at, _written_at, _git_hash, _version) "
            "VALUES (1, 2024, 'R', '2024-01-01', 1, 1, '2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
        )

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO at_bats (gamePk, atBatIndex, inning, halfInning, batter_id, pitcher_id, "
                "isComplete, hasReview, hasOut, isScoringPlay, "
                "_fetched_at, _written_at, _git_hash, _version) "
                "VALUES (1, 0, 1, 'top', 1, 1, 99, 0, 1, 0, "
                "'2024-01-01T00:00:00Z', '2024-01-01T00:00:00Z', 'abc123', '1.0.0')"
            )
