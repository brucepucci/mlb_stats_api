"""Venue data collector - fetches and syncs venue records on-demand."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import upsert_venue
from mlb_stats.models.venue import transform_venue

logger = logging.getLogger(__name__)


def sync_venue(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    venue_id: int,
) -> None:
    """Fetch venue from API and upsert. Always fresh, never cached.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    venue_id : int
        MLB venue ID

    Notes
    -----
    Reference data is always fetched fresh (not cached) to ensure
    mutable fields like name (sponsor changes) stay current.
    """
    logger.debug("Syncing venue %d", venue_id)

    # Fetch from API (not cached)
    fetched_at = datetime.now(timezone.utc).isoformat()
    response = client.get_venue(venue_id)

    # Transform to row
    row = transform_venue(response, fetched_at)

    # Upsert (adds write metadata)
    upsert_venue(conn, row)

    logger.info("Synced venue %d: %s", venue_id, row.get("name"))
