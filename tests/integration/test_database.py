"""Integration tests for database functionality."""

import sqlite3
from pathlib import Path

import pytest

from mlb_stats.db.connection import init_db
from mlb_stats.db.schema import SCHEMA_VERSION


class TestDatabaseConnection:
    """Tests for database connection configuration."""

    def test_foreign_keys_enabled(self, temp_db: sqlite3.Connection) -> None:
        """Test that foreign keys are enabled."""
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()[0]
        assert result == 1

    def test_wal_mode_enabled(self, temp_db: sqlite3.Connection) -> None:
        """Test that WAL journal mode is enabled."""
        cursor = temp_db.cursor()
        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()[0]
        assert result.lower() == "wal"

    def test_row_factory_set(self, temp_db: sqlite3.Connection) -> None:
        """Test that row_factory is set for dict-like access."""
        cursor = temp_db.cursor()
        cursor.execute("SELECT 1 as test_col")
        row = cursor.fetchone()
        assert row["test_col"] == 1


class TestForeignKeyConstraints:
    """Tests for foreign key constraint enforcement."""

    def test_games_team_foreign_key(self, temp_db: sqlite3.Connection) -> None:
        """Test that games table enforces team foreign key."""
        cursor = temp_db.cursor()

        # Try to insert a game with nonexistent team_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO games (
                    gamePk, season, gameType, gameDate,
                    away_team_id, home_team_id,
                    _fetched_at, _written_at, _git_hash, _version
                ) VALUES (
                    1, 2024, 'R', '2024-07-01',
                    999, 998,
                    '2024-07-01T00:00:00Z', '2024-07-01T00:00:00Z', 'abc123', '1.0.0'
                )
                """
            )

    def test_game_batting_player_foreign_key(self, temp_db: sqlite3.Connection) -> None:
        """Test that game_batting enforces player foreign key."""
        cursor = temp_db.cursor()

        # First create a team and game
        cursor.execute(
            """
            INSERT INTO teams (id, name, _fetched_at, _written_at, _git_hash, _version)
            VALUES (1, 'Test Team', '2024-01-01', '2024-01-01', 'abc', '1.0.0')
            """
        )
        cursor.execute(
            """
            INSERT INTO games (
                gamePk, season, gameType, gameDate,
                away_team_id, home_team_id,
                _fetched_at, _written_at, _git_hash, _version
            ) VALUES (
                1, 2024, 'R', '2024-07-01',
                1, 1,
                '2024-01-01', '2024-01-01', 'abc', '1.0.0'
            )
            """
        )
        temp_db.commit()

        # Try to insert batting record with nonexistent player
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO game_batting (
                    gamePk, player_id, team_id,
                    _fetched_at, _written_at, _git_hash, _version
                ) VALUES (
                    1, 999, 1,
                    '2024-01-01', '2024-01-01', 'abc', '1.0.0'
                )
                """
            )


class TestUpsertBehavior:
    """Tests for INSERT OR REPLACE behavior."""

    def test_insert_or_replace_updates_row(self, temp_db: sqlite3.Connection) -> None:
        """Test that INSERT OR REPLACE updates existing rows."""
        cursor = temp_db.cursor()

        # Insert a team
        cursor.execute(
            """
            INSERT INTO teams (id, name, _fetched_at, _written_at, _git_hash, _version)
            VALUES (1, 'Original Name', '2024-01-01', '2024-01-01', 'abc', '1.0.0')
            """
        )
        temp_db.commit()

        # Verify original name
        cursor.execute("SELECT name FROM teams WHERE id = 1")
        assert cursor.fetchone()[0] == "Original Name"

        # Update with INSERT OR REPLACE
        cursor.execute(
            """
            INSERT OR REPLACE INTO teams (id, name, _fetched_at, _written_at, _git_hash, _version)
            VALUES (1, 'Updated Name', '2024-01-02', '2024-01-02', 'def', '1.0.0')
            """
        )
        temp_db.commit()

        # Verify updated name
        cursor.execute("SELECT name FROM teams WHERE id = 1")
        assert cursor.fetchone()[0] == "Updated Name"

        # Verify only one row exists
        cursor.execute("SELECT COUNT(*) FROM teams WHERE id = 1")
        assert cursor.fetchone()[0] == 1


class TestSchemaIntegrity:
    """Tests for schema integrity."""

    def test_unique_constraints(self, temp_db: sqlite3.Connection) -> None:
        """Test that unique constraints are enforced."""
        cursor = temp_db.cursor()

        # Insert a team first
        cursor.execute(
            """
            INSERT INTO teams (id, name, _fetched_at, _written_at, _git_hash, _version)
            VALUES (1, 'Team', '2024-01-01', '2024-01-01', 'abc', '1.0.0')
            """
        )
        cursor.execute(
            """
            INSERT INTO games (
                gamePk, season, gameType, gameDate,
                away_team_id, home_team_id,
                _fetched_at, _written_at, _git_hash, _version
            ) VALUES (
                1, 2024, 'R', '2024-07-01', 1, 1,
                '2024-01-01', '2024-01-01', 'abc', '1.0.0'
            )
            """
        )
        temp_db.commit()

        # Insert first official
        cursor.execute(
            """
            INSERT INTO game_officials (
                gamePk, official_id, official_fullName, officialType,
                _written_at, _git_hash, _version
            ) VALUES (
                1, 100, 'John Umpire', 'Home Plate',
                '2024-01-01', 'abc', '1.0.0'
            )
            """
        )
        temp_db.commit()

        # Try to insert duplicate official type for same game
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO game_officials (
                    gamePk, official_id, official_fullName, officialType,
                    _written_at, _git_hash, _version
                ) VALUES (
                    1, 101, 'Jane Umpire', 'Home Plate',
                    '2024-01-01', 'abc', '1.0.0'
                )
                """
            )


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_creates_file(self, temp_db_path: Path) -> None:
        """Test that init_db creates the database file."""
        assert not temp_db_path.exists()
        conn = init_db(temp_db_path)
        conn.close()
        assert temp_db_path.exists()

    def test_init_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that init_db creates parent directories."""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        assert not db_path.parent.exists()
        conn = init_db(db_path)
        conn.close()
        assert db_path.exists()

    def test_init_idempotent(self, temp_db_path: Path) -> None:
        """Test that init_db can be called multiple times safely."""
        conn1 = init_db(temp_db_path)
        conn1.close()

        conn2 = init_db(temp_db_path)
        cursor = conn2.cursor()
        cursor.execute("SELECT value FROM _meta WHERE key = 'schema_version'")
        version = cursor.fetchone()[0]
        conn2.close()

        assert version == SCHEMA_VERSION
