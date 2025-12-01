"""Team data collector - fetches and syncs team records on-demand."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import upsert_team
from mlb_stats.models.team import transform_team

logger = logging.getLogger(__name__)


def sync_team(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    team_id: int,
) -> None:
    """Fetch team from API and upsert. Always fresh, never cached.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    team_id : int
        MLB team ID

    Notes
    -----
    Reference data is always fetched fresh (not cached) to ensure
    mutable fields like venue_id stay current.
    """
    logger.debug("Syncing team %d", team_id)

    # Fetch from API (not cached)
    fetched_at = datetime.now(timezone.utc).isoformat()
    response = client.get_team(team_id)

    # Transform to row
    row = transform_team(response, fetched_at)

    # Upsert (adds write metadata)
    upsert_team(conn, row)

    logger.info("Synced team %d: %s", team_id, row.get("name"))
