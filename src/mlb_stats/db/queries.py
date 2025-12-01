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
        Venue row data
    """
    row = row.copy()
    row.update(get_write_metadata())
    _upsert(conn, "venues", row)


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
