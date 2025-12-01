"""Player data collector - fetches and syncs player records on-demand."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import upsert_player
from mlb_stats.models.player import transform_player

logger = logging.getLogger(__name__)


def sync_player(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    person_id: int,
) -> None:
    """Fetch player from API and upsert. Always fresh, never cached.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    person_id : int
        MLB player ID (personId)

    Notes
    -----
    Reference data is always fetched fresh (not cached) to ensure
    mutable fields like lastPlayedDate, currentTeam_id stay current.
    """
    logger.debug("Syncing player %d", person_id)

    # Fetch from API (not cached)
    fetched_at = datetime.now(timezone.utc).isoformat()
    response = client.get_player(person_id)

    # Transform to row
    row = transform_player(response, fetched_at)

    # Upsert (adds write metadata)
    upsert_player(conn, row)

    logger.info("Synced player %d: %s", person_id, row.get("fullName"))
