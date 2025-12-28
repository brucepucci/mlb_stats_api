"""Game data collector - orchestrates game sync with reference data."""

import logging
import sqlite3
from datetime import datetime, timezone

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.collectors.venue import sync_venue
from mlb_stats.db.queries import (
    delete_game_officials,
    upsert_game,
    upsert_game_official,
    upsert_team,
)
from mlb_stats.models.game import transform_game, transform_officials
from mlb_stats.models.team import transform_team_from_game_feed

logger = logging.getLogger(__name__)


def sync_game(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    game_pk: int,
) -> bool:
    """Fetch game feed and sync game with reference data.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    game_pk : int
        Game primary key

    Returns
    -------
    bool
        True if sync succeeded, False otherwise

    Notes
    -----
    Extracts team and venue data from the game feed itself.
    The game feed is cached for Final games.

    Order of operations (for foreign key compliance):
    1. Extract and sync teams from gameData.teams
    2. Sync venue (fetch full details from API)
    3. Insert game
    4. Delete then insert officials
    """
    logger.info("Syncing game %d", game_pk)

    try:
        # Fetch game feed (cached if Final)
        fetched_at = datetime.now(timezone.utc).isoformat()
        game_feed = client.get_game_feed(game_pk)

        # Extract data from game feed
        game_data = game_feed.get("gameData", {})
        teams = game_data.get("teams", {})

        away_team_data = teams.get("away", {})
        home_team_data = teams.get("home", {})

        # 1. Sync teams (extracted from game feed)
        if away_team_data.get("id"):
            away_team_row = transform_team_from_game_feed(away_team_data, fetched_at)
            upsert_team(conn, away_team_row)
            logger.debug(
                "Synced team %s: %s",
                away_team_row.get("id"),
                away_team_row.get("name"),
            )

        if home_team_data.get("id"):
            home_team_row = transform_team_from_game_feed(home_team_data, fetched_at)
            upsert_team(conn, home_team_row)
            logger.debug(
                "Synced team %s: %s",
                home_team_row.get("id"),
                home_team_row.get("name"),
            )

        # 2. Sync venue (extract from game feed, fetch full details from API)
        # Extract game year from officialDate (required for venues composite PK)
        game_date = game_data.get("datetime", {}).get("officialDate", "")
        game_year = int(game_date[:4]) if len(game_date) >= 4 else None

        venue = game_data.get("venue", {})
        venue_id = venue.get("id")
        if venue_id and game_year:
            try:
                sync_venue(client, conn, venue_id, game_year)
                logger.debug("Synced venue %s: %s", venue_id, venue.get("name"))
            except Exception as e:
                logger.warning("Failed to sync venue %d: %s", venue_id, e)
                # Continue - game can still be synced with NULL venue_id
        elif venue_id and not game_year:
            logger.warning(
                "Cannot sync venue %d - game year could not be determined from date: %s",
                venue_id,
                game_date,
            )

        # 3. Transform and upsert game
        game_row = transform_game(game_feed, fetched_at)
        upsert_game(conn, game_row)

        # 4. Delete and re-insert officials for idempotent sync
        delete_game_officials(conn, game_pk)

        official_rows = transform_officials(game_feed, game_pk)
        for official_row in official_rows:
            upsert_game_official(conn, official_row)

        conn.commit()

        logger.info(
            "Synced game %d: %s @ %s (%s - %s)",
            game_pk,
            away_team_data.get("name", "Away"),
            home_team_data.get("name", "Home"),
            game_row.get("away_score"),
            game_row.get("home_score"),
        )

        return True

    except Exception as e:
        logger.error("Failed to sync game %d: %s", game_pk, e)
        conn.rollback()
        return False
