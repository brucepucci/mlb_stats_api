"""Roster data collector - syncs team rosters for games."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import delete_game_rosters, upsert_game_roster
from mlb_stats.models.roster import transform_roster

logger = logging.getLogger(__name__)


def sync_game_rosters(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    game_pk: int,
    game_date: str,
    away_team_id: int,
    home_team_id: int,
) -> bool:
    """Sync active rosters for both teams in a game.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    game_pk : int
        Game primary key
    game_date : str
        Game date in YYYY-MM-DD format
    away_team_id : int
        Away team ID
    home_team_id : int
        Home team ID

    Returns
    -------
    bool
        True if sync succeeded, False otherwise
    """
    logger.info("Syncing rosters for game %d", game_pk)

    try:
        fetched_at = datetime.now(timezone.utc).isoformat()

        # Delete existing rosters for this game (idempotent sync)
        delete_game_rosters(conn, game_pk)

        total_roster_entries = 0

        # Sync both teams
        for team_id in [away_team_id, home_team_id]:
            roster_data = client.get_roster(team_id, game_date)
            roster_rows = transform_roster(roster_data, game_pk, team_id, fetched_at)

            for row in roster_rows:
                upsert_game_roster(conn, row)

            total_roster_entries += len(roster_rows)
            logger.debug(
                "Synced %d roster entries for team %d",
                len(roster_rows),
                team_id,
            )

        conn.commit()

        logger.info(
            "Synced rosters for game %d: %d total entries",
            game_pk,
            total_roster_entries,
        )
        return True

    except Exception as e:
        logger.error("Failed to sync rosters for game %d: %s", game_pk, e)
        conn.rollback()
        return False
