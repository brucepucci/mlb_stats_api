"""Schedule data collector - fetches game schedules."""

import logging

from mlb_stats.api.client import MLBStatsClient

logger = logging.getLogger(__name__)


def fetch_schedule(
    client: MLBStatsClient,
    start_date: str,
    end_date: str,
) -> list[int]:
    """Fetch schedule and return list of gamePks.

    Parameters
    ----------
    client : MLBStatsClient
        API client instance
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)

    Returns
    -------
    list[int]
        List of gamePk values for all games in date range

    Notes
    -----
    Schedule data is never cached since games can be postponed
    or rescheduled.
    """
    logger.info("Fetching schedule from %s to %s", start_date, end_date)

    response = client.get_schedule(start_date=start_date, end_date=end_date)

    game_pks = []
    for date_entry in response.get("dates", []):
        for game in date_entry.get("games", []):
            game_pk = game.get("gamePk")
            if game_pk:
                game_pks.append(game_pk)

    logger.info("Found %d games in schedule", len(game_pks))
    return game_pks
