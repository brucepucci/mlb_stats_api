"""Boxscore data transformation functions."""

from typing import Any


def transform_batting(
    boxscore: dict,
    game_pk: int,
    fetched_at: str,
) -> list[dict]:
    """Transform boxscore to game_batting rows.

    Parameters
    ----------
    boxscore : dict
        Raw API response from /v1/game/{gamePk}/boxscore
    game_pk : int
        Game primary key
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    list[dict]
        List of row dicts for game_batting table

    Notes
    -----
    Players with no batting stats (empty stats.batting dict) are skipped.
    Batting order is parsed from string (e.g., "100") to int.
    """
    rows = []
    teams = boxscore.get("teams", {})

    for side in ("away", "home"):
        team_data = teams.get(side, {})
        team_id = team_data.get("team", {}).get("id")
        players = team_data.get("players", {})

        for player_key, player_data in players.items():
            # Skip if no batting stats
            batting = player_data.get("stats", {}).get("batting", {})
            if not batting:
                continue

            # Extract person info
            person = player_data.get("person", {})
            player_id = person.get("id")

            # Extract position
            position = player_data.get("position", {})

            # Parse batting order (string like "100" -> int)
            batting_order_str = player_data.get("battingOrder", "")
            batting_order = _parse_int(batting_order_str)

            row = {
                "gamePk": game_pk,
                "player_id": player_id,
                "team_id": team_id,
                # Batting order and position
                "battingOrder": batting_order,
                "position_code": position.get("code"),
                "position_name": position.get("name"),
                "position_abbreviation": position.get("abbreviation"),
                # Standard batting stats (preserve MLB field names)
                "gamesPlayed": batting.get("gamesPlayed"),
                "flyOuts": batting.get("flyOuts"),
                "groundOuts": batting.get("groundOuts"),
                "runs": batting.get("runs"),
                "doubles": batting.get("doubles"),
                "triples": batting.get("triples"),
                "homeRuns": batting.get("homeRuns"),
                "strikeOuts": batting.get("strikeOuts"),
                "baseOnBalls": batting.get("baseOnBalls"),
                "intentionalWalks": batting.get("intentionalWalks"),
                "hits": batting.get("hits"),
                "hitByPitch": batting.get("hitByPitch"),
                "atBats": batting.get("atBats"),
                "caughtStealing": batting.get("caughtStealing"),
                "stolenBases": batting.get("stolenBases"),
                "groundIntoDoublePlay": batting.get("groundIntoDoublePlay"),
                "groundIntoTriplePlay": batting.get("groundIntoTriplePlay"),
                "plateAppearances": batting.get("plateAppearances"),
                "totalBases": batting.get("totalBases"),
                "rbi": batting.get("rbi"),
                "leftOnBase": batting.get("leftOnBase"),
                "sacBunts": batting.get("sacBunts"),
                "sacFlies": batting.get("sacFlies"),
                "catchersInterference": batting.get("catchersInterference"),
                "pickoffs": batting.get("pickoffs"),
                # Calculated stats (as strings to preserve formatting)
                "avg": batting.get("avg"),
                "obp": batting.get("obp"),
                "slg": batting.get("slg"),
                "ops": batting.get("ops"),
                "atBatsPerHomeRun": batting.get("atBatsPerHomeRun"),
                # API fetch metadata
                "_fetched_at": fetched_at,
            }
            rows.append(row)

    return rows


def transform_pitching(
    boxscore: dict,
    game_pk: int,
    fetched_at: str,
) -> list[dict]:
    """Transform boxscore to game_pitching rows.

    Parameters
    ----------
    boxscore : dict
        Raw API response from /v1/game/{gamePk}/boxscore
    game_pk : int
        Game primary key
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    list[dict]
        List of row dicts for game_pitching table

    Notes
    -----
    Players with no pitching stats (empty stats.pitching dict) are skipped.
    isStartingPitcher is extracted from gameStatus.
    pitchingOrder is derived from the team's pitchers list order.
    note field (W/L/S/H/BS) is from seasonStats.pitching.note.
    """
    rows = []
    teams = boxscore.get("teams", {})

    for side in ("away", "home"):
        team_data = teams.get(side, {})
        team_id = team_data.get("team", {}).get("id")
        players = team_data.get("players", {})

        # Get pitcher order from team's pitchers list
        pitchers_list = team_data.get("pitchers", [])
        pitcher_order_map = {pid: idx + 1 for idx, pid in enumerate(pitchers_list)}

        for player_key, player_data in players.items():
            # Skip if no pitching stats
            pitching = player_data.get("stats", {}).get("pitching", {})
            if not pitching:
                continue

            # Extract person info
            person = player_data.get("person", {})
            player_id = person.get("id")

            # Determine if starting pitcher
            game_status = player_data.get("gameStatus", {})
            is_starting = 1 if game_status.get("isStartingPitcher") else 0

            # Get pitching order from the pitchers list
            pitching_order = pitcher_order_map.get(player_id)

            # Get W/L/S/H/BS note from seasonStats
            season_stats = player_data.get("seasonStats", {}).get("pitching", {})
            note = season_stats.get("note")

            row = {
                "gamePk": game_pk,
                "player_id": player_id,
                "team_id": team_id,
                # Role info
                "isStartingPitcher": is_starting,
                "pitchingOrder": pitching_order,
                # Standard pitching stats (preserve MLB field names)
                "gamesPlayed": pitching.get("gamesPlayed"),
                "gamesStarted": pitching.get("gamesStarted"),
                "flyOuts": pitching.get("flyOuts"),
                "groundOuts": pitching.get("groundOuts"),
                "airOuts": pitching.get("airOuts"),
                "runs": pitching.get("runs"),
                "doubles": pitching.get("doubles"),
                "triples": pitching.get("triples"),
                "homeRuns": pitching.get("homeRuns"),
                "strikeOuts": pitching.get("strikeOuts"),
                "baseOnBalls": pitching.get("baseOnBalls"),
                "intentionalWalks": pitching.get("intentionalWalks"),
                "hits": pitching.get("hits"),
                "hitByPitch": pitching.get("hitByPitch"),
                "atBats": pitching.get("atBats"),
                "caughtStealing": pitching.get("caughtStealing"),
                "stolenBases": pitching.get("stolenBases"),
                "numberOfPitches": pitching.get("numberOfPitches"),
                "inningsPitched": pitching.get("inningsPitched"),
                "wins": pitching.get("wins"),
                "losses": pitching.get("losses"),
                "saves": pitching.get("saves"),
                "saveOpportunities": pitching.get("saveOpportunities"),
                "holds": pitching.get("holds"),
                "blownSaves": pitching.get("blownSaves"),
                "earnedRuns": pitching.get("earnedRuns"),
                "battersFaced": pitching.get("battersFaced"),
                "outs": pitching.get("outs"),
                "gamesPitched": pitching.get("gamesPitched"),
                "completeGames": pitching.get("completeGames"),
                "shutouts": pitching.get("shutouts"),
                "pitchesThrown": pitching.get("pitchesThrown"),
                "balls": pitching.get("balls"),
                "strikes": pitching.get("strikes"),
                "strikePercentage": pitching.get("strikePercentage"),
                "hitBatsmen": pitching.get("hitBatsmen"),
                "balks": pitching.get("balks"),
                "wildPitches": pitching.get("wildPitches"),
                "pickoffs": pitching.get("pickoffs"),
                "rbi": pitching.get("rbi"),
                "gamesFinished": pitching.get("gamesFinished"),
                "runsScoredPer9": pitching.get("runsScoredPer9"),
                "homeRunsPer9": pitching.get("homeRunsPer9"),
                "inheritedRunners": pitching.get("inheritedRunners"),
                "inheritedRunnersScored": pitching.get("inheritedRunnersScored"),
                "catchersInterference": pitching.get("catchersInterference"),
                "sacBunts": pitching.get("sacBunts"),
                "sacFlies": pitching.get("sacFlies"),
                "passedBall": pitching.get("passedBall"),
                # Calculated stats from API
                "era": pitching.get("era"),
                "whip": pitching.get("whip"),
                # Game result attribution
                "note": note,
                # API fetch metadata
                "_fetched_at": fetched_at,
            }
            rows.append(row)

    return rows


def extract_player_ids(boxscore: dict) -> set[int]:
    """Extract all player IDs from boxscore.

    Parameters
    ----------
    boxscore : dict
        Raw API response from /v1/game/{gamePk}/boxscore

    Returns
    -------
    set[int]
        Set of unique player IDs

    Notes
    -----
    Extracts player IDs from both away and home team rosters.
    """
    player_ids: set[int] = set()
    teams = boxscore.get("teams", {})

    for side in ("away", "home"):
        players = teams.get(side, {}).get("players", {})
        for player_key, player_data in players.items():
            person = player_data.get("person", {})
            player_id = person.get("id")
            if player_id:
                player_ids.add(player_id)

    return player_ids


def _parse_int(value: Any) -> int | None:
    """Safely parse value as int.

    Parameters
    ----------
    value : Any
        Value to parse

    Returns
    -------
    int or None
        Parsed integer, or None if parsing fails
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
