"""Database connection management for MLB Stats Collector."""

import logging
import sqlite3
from pathlib import Path

from mlb_stats.db.schema import SCHEMA_VERSION, create_tables

logger = logging.getLogger(__name__)


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a SQLite database connection with proper configuration.

    Configures the connection with:
    - Foreign keys enabled
    - WAL journal mode for better concurrency
    - 64MB cache size for performance

    Parameters
    ----------
    db_path : str or Path
        Path to the SQLite database file

    Returns
    -------
    sqlite3.Connection
        Configured database connection
    """
    db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows

    # Configure pragmas for performance and safety
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache

    logger.debug("Connected to database: %s", db_path)

    return conn


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """Initialize the database with all tables.

    Creates all tables and sets the schema version in _meta.

    Parameters
    ----------
    db_path : str or Path
        Path to the SQLite database file

    Returns
    -------
    sqlite3.Connection
        Configured database connection with tables created
    """
    conn = get_connection(db_path)

    # Create all tables
    create_tables(conn)

    # Set schema version
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
        ("schema_version", SCHEMA_VERSION),
    )
    conn.commit()

    logger.info(
        "Database initialized at %s with schema version %s", db_path, SCHEMA_VERSION
    )

    return conn


def get_schema_version(conn: sqlite3.Connection) -> str | None:
    """Get the schema version from the database.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection

    Returns
    -------
    str or None
        Schema version string, or None if not set
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM _meta WHERE key = ?", ("schema_version",))
        row = cursor.fetchone()
        return row["value"] if row else None
    except sqlite3.OperationalError:
        # Table doesn't exist
        return None


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists in the database.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    table_name : str
        Name of the table to check

    Returns
    -------
    bool
        True if table exists
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None
