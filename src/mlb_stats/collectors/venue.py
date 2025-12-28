"""Venue data collector - fetches and syncs venue records on-demand."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import upsert_venue, venue_needs_refresh
from mlb_stats.models.venue import transform_venue

logger = logging.getLogger(__name__)


def sync_venue(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    venue_id: int,
    game_year: int,
) -> None:
    """Fetch venue from API and upsert.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    venue_id : int
        MLB venue ID
    game_year : int
        Year of the game being synced. Venue data is only fetched if the
        venue doesn't exist for this year. This is also used as the year
        in the venues table composite PK (id, year).

    Notes
    -----
    Venues are stored per-year to track changes between seasons (renovations,
    capacity changes, outfield wall adjustments). Year-based storage ensures
    accurate venue data for each season while avoiding redundant API calls
    within a season.
    """
    # Check if we can skip the API call (venue already exists for this year)
    if not venue_needs_refresh(conn, venue_id, game_year):
        logger.debug(
            "Venue %d already exists for year %d, skipping API call",
            venue_id,
            game_year,
        )
        return

    logger.debug("Syncing venue %d for year %d", venue_id, game_year)

    # Fetch from API
    fetched_at = datetime.now(timezone.utc).isoformat()
    response = client.get_venue(venue_id)

    # Transform to row (with year for composite PK)
    row = transform_venue(response, fetched_at, game_year)

    # Upsert (adds write metadata)
    upsert_venue(conn, row)

    logger.info("Synced venue %d for year %d: %s", venue_id, game_year, row.get("name"))
