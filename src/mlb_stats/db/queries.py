"""Database query helpers for upsert operations."""

import sqlite3

from mlb_stats.utils.metadata import get_write_metadata


def upsert_team(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace team record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Team row data (must include all required columns)
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "teams", row)


def upsert_venue(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace venue record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Venue row data (must include all required columns)
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "venues", row)


def venue_needs_refresh(conn: sqlite3.Connection, venue_id: int, year: int) -> bool:
    """Check if venue needs to be fetched from API.

    Returns True if venue doesn't exist in DB for the given year.
    Venues are stored per-year (composite PK of id, year) to track
    changes between seasons (renovations, capacity changes, etc.).

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    venue_id : int
        MLB venue ID
    year : int
        Year to check for venue data

    Returns
    -------
    bool
        True if venue should be fetched, False if data exists for this year
    """
    cursor = conn.execute(
        "SELECT 1 FROM venues WHERE id = ? AND year = ?",
        (venue_id, year),
    )
    return cursor.fetchone() is None


def upsert_game(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace game record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Game row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "games", row)


def upsert_game_official(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace game official record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Game official row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "game_officials", row)


def delete_game_officials(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all officials for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM game_officials WHERE gamePk = ?", (gamePk,))


def get_game_pks_for_date_range(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> list[int]:
    """Get gamePks already in database for date range.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)

    Returns
    -------
    list[int]
        List of gamePk values
    """
    cursor = conn.execute(
        "SELECT gamePk FROM games WHERE gameDate BETWEEN ? AND ?",
        (start_date, end_date),
    )
    return [row[0] for row in cursor.fetchall()]


def upsert_player(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace player record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Player row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "players", row)


def get_missing_player_ids(
    conn: sqlite3.Connection, player_ids: list[int]
) -> list[int]:
    """Return player IDs that don't exist in the players table.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    player_ids : list[int]
        List of player IDs to check

    Returns
    -------
    list[int]
        Player IDs not found in the database
    """
    if not player_ids:
        return []
    placeholders = ",".join("?" * len(player_ids))
    cursor = conn.execute(
        f"SELECT id FROM players WHERE id IN ({placeholders})",
        tuple(player_ids),
    )
    existing = {row[0] for row in cursor.fetchall()}
    return [pid for pid in player_ids if pid not in existing]


def upsert_game_batting(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace game_batting record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Game batting row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "game_batting", row)


def upsert_game_pitching(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace game_pitching record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Game pitching row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "game_pitching", row)


def delete_game_batting(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all batting records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM game_batting WHERE gamePk = ?", (gamePk,))


def delete_game_pitching(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all pitching records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM game_pitching WHERE gamePk = ?", (gamePk,))


def upsert_pitch(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace pitch record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Pitch row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "pitches", row)


def upsert_at_bat(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace at_bat record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        At-bat row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "at_bats", row)


def upsert_batted_ball(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace batted_ball record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Batted ball row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "batted_balls", row)


def delete_pitches(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all pitch records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM pitches WHERE gamePk = ?", (gamePk,))


def delete_at_bats(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all at_bat records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM at_bats WHERE gamePk = ?", (gamePk,))


def delete_batted_balls(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all batted_ball records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM batted_balls WHERE gamePk = ?", (gamePk,))


def upsert_game_roster(conn: sqlite3.Connection, row: dict) -> None:
    """Insert or replace game_roster record with write metadata.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    row : dict
        Game roster row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "game_rosters", row)


def delete_game_rosters(conn: sqlite3.Connection, gamePk: int) -> None:
    """Delete all roster records for a game.

    Used before re-inserting to ensure idempotent sync.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    gamePk : int
        Game primary key
    """
    conn.execute("DELETE FROM game_rosters WHERE gamePk = ?", (gamePk,))


def _upsert(conn: sqlite3.Connection, table: str, row: dict) -> None:
    """Generic INSERT OR REPLACE helper.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    table : str
        Table name
    row : dict
        Row data as column:value dict
    """
    columns = ", ".join(row.keys())
    placeholders = ", ".join("?" for _ in row)
    sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
    conn.execute(sql, list(row.values()))
