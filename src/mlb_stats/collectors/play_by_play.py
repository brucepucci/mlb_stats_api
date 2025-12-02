"""Play-by-play data collector - orchestrates pitch, at-bat, and batted ball sync."""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.queries import (
    delete_at_bats,
    delete_batted_balls,
    delete_pitches,
    get_game_pks_for_date_range,
    upsert_at_bat,
    upsert_batted_ball,
    upsert_pitch,
)
from mlb_stats.models.pitch import (
    extract_batted_ball_event,
    extract_pitches_from_play,
    transform_at_bat,
    transform_batted_ball,
    transform_pitch,
)

logger = logging.getLogger(__name__)


def sync_play_by_play(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    game_pk: int,
) -> bool:
    """Fetch play-by-play and sync pitches, at-bats, and batted balls.

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
    Uses game feed (already cached from boxscore sync) to get play data.

    Order of operations (for foreign key compliance):
    1. Fetch game feed
    2. Validate game has play data
    3. Delete existing pitch/at-bat/batted-ball records for idempotent sync
    4. Insert at-bats, pitches, and batted balls
    5. Commit transaction
    """
    logger.info("Syncing play-by-play for game %d", game_pk)

    try:
        fetched_at = datetime.now(timezone.utc).isoformat()

        # Fetch game feed (already cached if Final from boxscore sync)
        game_feed = client.get_game_feed(game_pk)

        # Get plays from liveData
        live_data = game_feed.get("liveData", {})
        plays = live_data.get("plays", {})
        all_plays = plays.get("allPlays", [])

        if not all_plays:
            logger.warning(
                "No play data for game %d (game may not have started)",
                game_pk,
            )
            return False

        # Delete existing records for idempotent sync
        # Order matters due to foreign key: batted_balls -> pitches
        delete_batted_balls(conn, game_pk)
        delete_pitches(conn, game_pk)
        delete_at_bats(conn, game_pk)

        # Track counts for logging
        at_bat_count = 0
        pitch_count = 0
        batted_ball_count = 0

        # Process each play
        for play in all_plays:
            # Skip incomplete plays that aren't at-bats
            result_type = play.get("result", {}).get("type")
            if result_type != "atBat":
                continue

            # Insert at-bat record
            at_bat_row = transform_at_bat(play, game_pk, fetched_at)
            upsert_at_bat(conn, at_bat_row)
            at_bat_count += 1

            # Get pitch events from this play
            pitch_events = extract_pitches_from_play(play)

            for event in pitch_events:
                # Insert pitch record
                pitch_row = transform_pitch(play, event, game_pk, fetched_at)
                upsert_pitch(conn, pitch_row)
                pitch_count += 1

            # Check for batted ball (in-play event with hitData)
            batted_ball_event = extract_batted_ball_event(play)
            if batted_ball_event:
                batted_ball_row = transform_batted_ball(
                    play, batted_ball_event, game_pk, fetched_at
                )
                upsert_batted_ball(conn, batted_ball_row)
                batted_ball_count += 1

        conn.commit()

        logger.info(
            "Synced play-by-play for game %d: %d at-bats, %d pitches, %d batted balls",
            game_pk,
            at_bat_count,
            pitch_count,
            batted_ball_count,
        )

        return True

    except Exception as e:
        logger.error("Failed to sync play-by-play for game %d: %s", game_pk, e)
        conn.rollback()
        return False


def sync_play_by_play_for_date_range(
    client: MLBStatsClient,
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    """Sync play-by-play for all games in date range.

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
    Gets gamePks from database (assumes games are already synced).
    """
    # Get gamePks from database
    game_pks = get_game_pks_for_date_range(conn, start_date, end_date)

    if not game_pks:
        logger.warning("No games found for date range %s to %s", start_date, end_date)
        return (0, 0)

    logger.info("Syncing play-by-play for %d games", len(game_pks))

    success_count = 0
    failure_count = 0

    for i, game_pk in enumerate(game_pks):
        if progress_callback:
            progress_callback(i + 1, len(game_pks))

        if sync_play_by_play(client, conn, game_pk):
            success_count += 1
        else:
            failure_count += 1

    logger.info(
        "Play-by-play sync complete: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    return (success_count, failure_count)
