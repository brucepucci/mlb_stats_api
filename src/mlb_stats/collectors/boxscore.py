"""Boxscore data collector - orchestrates boxscore sync with player data."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.collectors.game import sync_game
from mlb_stats.collectors.play_by_play import sync_play_by_play
from mlb_stats.collectors.roster import sync_game_rosters
from mlb_stats.collectors.schedule import fetch_schedule
from mlb_stats.db.queries import (
    delete_game_batting,
    delete_game_pitching,
    get_game_pks_for_date_range,
    upsert_game_batting,
    upsert_game_pitching,
    upsert_player,
)
from mlb_stats.models.boxscore import (
    extract_player_ids,
    transform_batting,
    transform_pitching,
)
from mlb_stats.models.player import transform_player_from_game_feed

logger = logging.getLogger(__name__)


def _get_player_team_mapping(boxscore: dict) -> dict[int, int]:
    """Build mapping of player ID to team ID from boxscore.

    Parameters
    ----------
    boxscore : dict
        Boxscore data

    Returns
    -------
    dict[int, int]
        Mapping of player_id -> team_id
    """
    player_to_team = {}
    teams = boxscore.get("teams", {})

    for side in ("away", "home"):
        team_data = teams.get(side, {})
        team_id = team_data.get("team", {}).get("id")
        if not team_id:
            continue

        players = team_data.get("players", {})
        for player_key in players:
            # Player keys are like "ID660271"
            if player_key.startswith("ID"):
                try:
                    player_id = int(player_key[2:])
                    player_to_team[player_id] = team_id
                except ValueError:
                    pass

    return player_to_team


def sync_boxscore(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    game_pk: int,
) -> bool:
    """Fetch boxscore and sync all game stats including pitch-level data.

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
    Extracts player data from the game feed (cached for Final games),
    eliminating separate player API calls.

    Order of operations (for foreign key compliance):
    1. Sync game (extracts teams/venues from game feed)
    2. Extract and sync players from gameData.players
    3. Delete existing batting/pitching records for game
    4. Insert new batting/pitching records
    5. Sync play-by-play (pitches, at-bats, batted balls)
    """
    logger.info("Syncing boxscore for game %d", game_pk)

    try:
        fetched_at = datetime.now(timezone.utc).isoformat()

        # Fetch game feed (cached if Final) - has player data in gameData.players
        game_feed = client.get_game_feed(game_pk)

        # Fetch boxscore (cached if Final) - has batting/pitching stats
        boxscore = client.get_boxscore(game_pk)

        # Check if game has valid boxscore data
        teams = boxscore.get("teams", {})
        away_players = teams.get("away", {}).get("players", {})
        home_players = teams.get("home", {}).get("players", {})

        if not away_players and not home_players:
            logger.warning(
                "No player data in boxscore for game %d (game may not have started)",
                game_pk,
            )
            return False

        # 1. Sync game (extracts teams/venues from game feed)
        sync_game(client, conn, game_pk)

        # 2. Extract and sync players from game feed
        # Build player -> team mapping from boxscore
        player_to_team = _get_player_team_mapping(boxscore)

        # Get player data from gameData.players
        game_data_players = game_feed.get("gameData", {}).get("players", {})
        player_ids = extract_player_ids(boxscore)
        logger.debug("Found %d players in boxscore", len(player_ids))

        for player_id in player_ids:
            player_key = f"ID{player_id}"
            player_data = game_data_players.get(player_key, {})

            if player_data:
                # Get team association from boxscore
                team_id = player_to_team.get(player_id)
                player_row = transform_player_from_game_feed(
                    player_data, fetched_at, team_id
                )
                upsert_player(conn, player_row)
                logger.debug(
                    "Synced player %s: %s",
                    player_row.get("id"),
                    player_row.get("fullName"),
                )
            else:
                logger.warning(
                    "Player %d not found in gameData.players for game %d",
                    player_id,
                    game_pk,
                )

        # 3. Transform batting and pitching data
        batting_rows = transform_batting(boxscore, game_pk, fetched_at)
        pitching_rows = transform_pitching(boxscore, game_pk, fetched_at)

        # 4. Delete existing records for idempotent sync
        delete_game_batting(conn, game_pk)
        delete_game_pitching(conn, game_pk)

        # 5. Insert new records
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

        # 6. Sync play-by-play (pitches, at-bats, batted balls)
        sync_play_by_play(client, conn, game_pk)

        # 7. Sync rosters for both teams
        game_data = game_feed.get("gameData", {})
        game_date = game_data.get("datetime", {}).get("officialDate")
        away_team_id = teams.get("away", {}).get("team", {}).get("id")
        home_team_id = teams.get("home", {}).get("team", {}).get("id")

        if game_date and away_team_id and home_team_id:
            sync_game_rosters(
                client, conn, game_pk, game_date, away_team_id, home_team_id
            )
        else:
            logger.warning(
                "Missing data for roster sync (game %d): date=%s, away=%s, home=%s",
                game_pk,
                game_date,
                away_team_id,
                home_team_id,
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
    force_refresh: bool = False,
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
    force_refresh : bool
        If True, always fetch schedule from API instead of using database

    Returns
    -------
    tuple[int, int]
        (success_count, failure_count)

    Notes
    -----
    Gets gamePks from database first (unless force_refresh=True).
    If none found, fetches from schedule API.
    """
    game_pks = []

    # Try to get gamePks from database first (unless force_refresh)
    if not force_refresh:
        game_pks = get_game_pks_for_date_range(conn, start_date, end_date)

    # If no games in database (or force_refresh), fetch from schedule API
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
