"""Game data collector - orchestrates game sync with reference data."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.collectors.schedule import fetch_schedule
from mlb_stats.collectors.venue import sync_venue
from mlb_stats.db.queries import (
    delete_game_officials,
    upsert_game,
    upsert_game_official,
    upsert_team,
)
from mlb_stats.models.game import transform_game, transform_officials
from mlb_stats.models.team import transform_team

logger = logging.getLogger(__name__)


def _sync_team_from_response(conn: sqlite3.Connection, response: dict) -> None:
    """Sync team from an already-fetched API response.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    response : dict
        Already-fetched team API response
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    row = transform_team(response, fetched_at)
    upsert_team(conn, row)
    logger.info("Synced team %s: %s", row.get("id"), row.get("name"))


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
    Order of operations (for foreign key compliance):
    1. Sync game venue
    2. Fetch team data to get their home venue IDs
    3. Sync team home venues (teams table has FK to venues)
    4. Sync teams
    5. Insert game
    6. Delete then insert officials
    """
    logger.info("Syncing game %d", game_pk)

    try:
        # Fetch game feed (cached if Final)
        fetched_at = datetime.now(timezone.utc).isoformat()
        game_feed = client.get_game_feed(game_pk)

        # Extract IDs from game data
        game_data = game_feed.get("gameData", {})
        teams = game_data.get("teams", {})
        venue = game_data.get("venue", {})

        away_team_id = teams.get("away", {}).get("id")
        home_team_id = teams.get("home", {}).get("id")
        venue_id = venue.get("id")

        # Collect all venue IDs that need to be synced (game venue + team home venues)
        venue_ids_to_sync = set()
        if venue_id:
            venue_ids_to_sync.add(venue_id)

        # Fetch team data to get their home venue IDs
        team_responses = {}
        if away_team_id:
            team_responses[away_team_id] = client.get_team(away_team_id)
            away_team_venue = (
                team_responses[away_team_id]
                .get("teams", [{}])[0]
                .get("venue", {})
                .get("id")
            )
            if away_team_venue:
                venue_ids_to_sync.add(away_team_venue)

        if home_team_id and home_team_id != away_team_id:
            team_responses[home_team_id] = client.get_team(home_team_id)
            home_team_venue = (
                team_responses[home_team_id]
                .get("teams", [{}])[0]
                .get("venue", {})
                .get("id")
            )
            if home_team_venue:
                venue_ids_to_sync.add(home_team_venue)

        # Sync all venues first (before teams, due to FK)
        for vid in venue_ids_to_sync:
            sync_venue(client, conn, vid)

        # Now sync teams (using already-fetched responses)
        if away_team_id and away_team_id in team_responses:
            _sync_team_from_response(conn, team_responses[away_team_id])

        if (
            home_team_id
            and home_team_id != away_team_id
            and home_team_id in team_responses
        ):
            _sync_team_from_response(conn, team_responses[home_team_id])

        # Transform and upsert game
        game_row = transform_game(game_feed, fetched_at)
        upsert_game(conn, game_row)

        # Delete and re-insert officials for idempotent sync
        delete_game_officials(conn, game_pk)

        official_rows = transform_officials(game_feed, game_pk)
        for official_row in official_rows:
            upsert_game_official(conn, official_row)

        conn.commit()

        logger.info(
            "Synced game %d: %s @ %s (%s - %s)",
            game_pk,
            teams.get("away", {}).get("name", "Away"),
            teams.get("home", {}).get("name", "Home"),
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
