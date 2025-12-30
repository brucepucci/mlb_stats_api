"""Game data transformation functions."""

from typing import Any


def transform_game(game_feed: dict, fetched_at: str) -> dict:
    """Transform game feed to database row.

    Parameters
    ----------
    game_feed : dict
        Raw API response from /v1.1/game/{gamePk}/feed/live
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching games table schema

    Notes
    -----
    Extracts data from gameData and liveData.boxscore.
    Weather data may be missing for indoor stadiums or older games.
    """
    game_data = game_feed.get("gameData", {})
    live_data = game_feed.get("liveData", {})

    game = game_data.get("game", {})
    datetime_info = game_data.get("datetime", {})
    status = game_data.get("status", {})
    teams = game_data.get("teams", {})
    venue = game_data.get("venue", {})
    weather = game_data.get("weather", {})

    # Get boxscore for attendance and game info
    boxscore = live_data.get("boxscore", {})
    boxscore_info = boxscore.get("info", [])

    # Get final score from linescore
    linescore = live_data.get("linescore", {})

    # Extract attendance from boxscore info
    attendance = _extract_attendance(boxscore_info)

    # Get gameDate from officialDate or parse from dateTime
    game_date = datetime_info.get("officialDate")
    if not game_date and datetime_info.get("dateTime"):
        # Extract date portion from ISO8601 timestamp
        game_date = datetime_info.get("dateTime", "")[:10]

    # Parse season as integer
    # If season can't be determined, also clear venue_id to avoid FK violations
    # (games.venue_id + games.season) references venues(id, year)
    season_str = game.get("season")
    season_valid = False
    try:
        season = int(season_str) if season_str else 0
        season_valid = season > 0
    except (ValueError, TypeError):
        season = 0

    return {
        "gamePk": game_feed.get("gamePk"),
        "season": season,
        "gameType": game.get("type"),
        "gameDate": game_date,
        "gameDateTime": datetime_info.get("dateTime"),
        "officialDate": datetime_info.get("officialDate"),
        "away_team_id": teams.get("away", {}).get("id"),
        "home_team_id": teams.get("home", {}).get("id"),
        "away_score": linescore.get("teams", {}).get("away", {}).get("runs"),
        "home_score": linescore.get("teams", {}).get("home", {}).get("runs"),
        "abstractGameState": status.get("abstractGameState"),
        "detailedState": status.get("detailedState"),
        "statusCode": status.get("statusCode"),
        "venue_id": venue.get("id") if season_valid else None,
        "dayNight": datetime_info.get("dayNight"),
        "scheduledInnings": game.get("scheduledInnings"),
        "inningCount": linescore.get("currentInning"),
        "weather_condition": weather.get("condition"),
        "weather_temp": weather.get("temp"),
        "weather_wind": weather.get("wind"),
        "attendance": attendance,
        "firstPitch": datetime_info.get("firstPitch"),
        "gameEndDateTime": datetime_info.get("gameEndDateTime"),
        "doubleHeader": game.get("doubleHeader"),
        "gameNumber": game.get("gameNumber"),
        "seriesDescription": game.get("seriesDescription"),
        "seriesGameNumber": game.get("seriesGameNumber"),
        "gamesInSeries": game.get("gamesInSeries"),
        "_fetched_at": fetched_at,
    }


def transform_officials(game_feed: dict, gamePk: int) -> list[dict]:
    """Transform officials from boxscore to game_officials rows.

    Parameters
    ----------
    game_feed : dict
        Raw API response from /v1.1/game/{gamePk}/feed/live
    gamePk : int
        Game primary key

    Returns
    -------
    list[dict]
        List of row dicts for game_officials table
    """
    officials = game_feed.get("liveData", {}).get("boxscore", {}).get("officials", [])

    rows = []
    for official in officials:
        official_info = official.get("official", {})
        rows.append(
            {
                "gamePk": gamePk,
                "official_id": official_info.get("id"),
                "official_fullName": official_info.get("fullName"),
                "officialType": official.get("officialType"),
            }
        )

    return rows


def _extract_home_plate_umpire(officials: list[dict]) -> dict[str, Any]:
    """Extract home plate umpire from officials list.

    Parameters
    ----------
    officials : list
        List of official dicts from boxscore

    Returns
    -------
    dict
        Dict with 'id' and 'fullName' keys, empty if not found
    """
    for official in officials:
        if official.get("officialType") == "Home Plate":
            return official.get("official", {})
    return {}


def _extract_attendance(boxscore_info: list[dict]) -> int | None:
    """Extract attendance from boxscore info array.

    Parameters
    ----------
    boxscore_info : list
        List of info dicts from boxscore

    Returns
    -------
    int or None
        Attendance count, or None if not found
    """
    for info in boxscore_info:
        if info.get("label") == "Att":
            value = info.get("value", "").replace(",", "").rstrip(".")
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
    return None
