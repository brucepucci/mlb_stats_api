"""Database connection and schema management."""

from mlb_stats.db.connection import get_connection, init_db
from mlb_stats.db.schema import SCHEMA_VERSION, create_tables

__all__ = ["get_connection", "init_db", "create_tables", "SCHEMA_VERSION"]
