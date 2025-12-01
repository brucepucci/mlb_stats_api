"""Game data collector - orchestrates game sync with reference data."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.collectors.schedule import fetch_schedule
from mlb_stats.db.queries import (
    delete_game_officials,
    upsert_game,
    upsert_game_official,
    upsert_team,
    upsert_venue,
)
from mlb_stats.models.game import transform_game, transform_officials
from mlb_stats.models.team import transform_team_from_game_feed
from mlb_stats.models.venue import transform_venue_from_game_feed

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
    Extracts all reference data (venues, teams) from the game feed itself,
    eliminating separate API calls. The game feed is cached for Final games.

    Order of operations (for foreign key compliance):
    1. Extract and sync game venue from gameData.venue
    2. Extract and sync teams from gameData.teams (venue_id refs game venue)
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
        venue_data = game_data.get("venue", {})

        away_team_data = teams.get("away", {})
        home_team_data = teams.get("home", {})

        # 1. Sync game venue (extracted from game feed - has full location data)
        if venue_data.get("id"):
            venue_row = transform_venue_from_game_feed(venue_data, fetched_at)
            upsert_venue(conn, venue_row)
            logger.debug("Synced venue %s: %s", venue_row.get("id"), venue_row.get("name"))

        # 2. Sync team home venues (minimal data - just id/name from game feed)
        # This is needed because teams table has FK to venues
        for team_data in [away_team_data, home_team_data]:
            team_venue = team_data.get("venue", {})
            if team_venue.get("id"):
                # Create minimal venue record if it doesn't exist
                # Full data will be synced when we encounter a game at that venue
                venue_row = transform_venue_from_game_feed(team_venue, fetched_at)
                upsert_venue(conn, venue_row)
                logger.debug(
                    "Synced team venue %s: %s",
                    venue_row.get("id"),
                    venue_row.get("name"),
                )

        # 3. Sync teams (extracted from game feed)
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

        # 4. Transform and upsert game
        game_row = transform_game(game_feed, fetched_at)
        upsert_game(conn, game_row)

        # 5. Delete and re-insert officials for idempotent sync
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


def sync_games_for_date_range(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    """Sync all games for date range.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    conn : sqlite3.Connection
        Database connection
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    progress_callback : callable, optional
        Called with (current, total) for progress updates

    Returns
    -------
    tuple[int, int]
        (success_count, failure_count)
    """
    # Fetch schedule to get gamePks
    game_pks = fetch_schedule(client, start_date, end_date)

    if not game_pks:
        logger.warning("No games found for date range %s to %s", start_date, end_date)
        return (0, 0)

    success_count = 0
    failure_count = 0

    for i, game_pk in enumerate(game_pks):
        if progress_callback:
            progress_callback(i + 1, len(game_pks))

        if sync_game(client, conn, game_pk):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        "Sync complete: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    return (success_count, failure_count)
