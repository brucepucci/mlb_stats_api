"""Boxscore data collector - orchestrates boxscore sync with player data."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.collectors.game import sync_game
from mlb_stats.collectors.player import sync_player
from mlb_stats.collectors.schedule import fetch_schedule
from mlb_stats.db.queries import (
    delete_game_batting,
    delete_game_pitching,
    get_game_pks_for_date_range,
    upsert_game_batting,
    upsert_game_pitching,
)
from mlb_stats.models.boxscore import (
    extract_player_ids,
    transform_batting,
    transform_pitching,
)

logger = logging.getLogger(__name__)


def sync_boxscore(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    game_pk: int,
) -> bool:
    """Fetch boxscore and sync batting/pitching stats with player data.

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
    Order of operations (for foreign key compliance):
    1. Fetch boxscore (cached if Final)
    2. Sync all players from boxscore (fresh fetch for each)
    3. Delete existing batting/pitching records for game
    4. Insert new batting/pitching records
    """
    logger.info("Syncing boxscore for game %d", game_pk)

    try:
        # Fetch boxscore (cached if Final)
        fetched_at = datetime.now(timezone.utc).isoformat()
        boxscore = client.get_boxscore(game_pk)

        # Check if game has valid boxscore data
        # Skip if no player data (game not started or postponed)
        teams = boxscore.get("teams", {})
        away_players = teams.get("away", {}).get("players", {})
        home_players = teams.get("home", {}).get("players", {})

        if not away_players and not home_players:
            logger.warning(
                "No player data in boxscore for game %d (game may not have started)",
                game_pk,
            )
            return False

        # Sync game first (for FK constraints)
        # This ensures the game record exists before inserting batting/pitching
        sync_game(client, conn, game_pk)

        # Extract and sync all players
        player_ids = extract_player_ids(boxscore)
        logger.debug("Found %d players in boxscore", len(player_ids))

        for player_id in player_ids:
            try:
                sync_player(client, conn, player_id)
            except Exception as e:
                logger.warning("Failed to sync player %d: %s", player_id, e)
                # Continue with other players

        # Transform batting and pitching data
        batting_rows = transform_batting(boxscore, game_pk, fetched_at)
        pitching_rows = transform_pitching(boxscore, game_pk, fetched_at)

        # Delete existing records for idempotent sync
        delete_game_batting(conn, game_pk)
        delete_game_pitching(conn, game_pk)

        # Insert new records
        for row in batting_rows:
            upsert_game_batting(conn, row)

        for row in pitching_rows:
            upsert_game_pitching(conn, row)

        conn.commit()

        logger.info(
            "Synced boxscore for game %d: %d batting, %d pitching records",
            game_pk,
            len(batting_rows),
            len(pitching_rows),
        )

        return True

    except Exception as e:
        logger.error("Failed to sync boxscore for game %d: %s", game_pk, e)
        conn.rollback()
        return False


def sync_boxscores_for_date_range(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    """Sync boxscores for all games in date range.

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

    Notes
    -----
    Gets gamePks from database first. If none found, fetches from
    schedule API (so games don't need to be synced first).
    """
    # Try to get gamePks from database first
    game_pks = get_game_pks_for_date_range(conn, start_date, end_date)

    # If no games in database, fetch from schedule API
    if not game_pks:
        logger.info(
            "No games in database for %s to %s, fetching from schedule API",
            start_date,
            end_date,
        )
        game_pks = fetch_schedule(client, start_date, end_date)

    if not game_pks:
        logger.warning("No games found for date range %s to %s", start_date, end_date)
        return (0, 0)

    logger.info("Syncing boxscores for %d games", len(game_pks))

    success_count = 0
    failure_count = 0

    for i, game_pk in enumerate(game_pks):
        if progress_callback:
            progress_callback(i + 1, len(game_pks))

        if sync_boxscore(client, conn, game_pk):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        "Boxscore sync complete: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    return (success_count, failure_count)
