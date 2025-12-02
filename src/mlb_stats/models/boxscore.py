"""Boxscore data transformation functions."""

from typing import Any


def _calculate_batting_avg(hits: int | None, at_bats: int | None) -> str | None:
    """Calculate batting average for a game.

    Parameters
    ----------
    hits : int or None
        Number of hits
    at_bats : int or None
        Number of at bats

    Returns
    -------
    str or None
        Batting average formatted as ".XXX" or None if cannot calculate
    """
    if hits is None or at_bats is None or at_bats == 0:
        return None
    avg = hits / at_bats
    # Format: always show 3 decimal places, include leading 0 if >= 1.0
    if avg >= 1.0:
        return f"{avg:.3f}"
    return f"{avg:.3f}"


def _calculate_obp(
    hits: int | None,
    base_on_balls: int | None,
    hit_by_pitch: int | None,
    at_bats: int | None,
    sac_flies: int | None,
) -> str | None:
    """Calculate on-base percentage for a game.

    OBP = (H + BB + HBP) / (AB + BB + HBP + SF)

    Parameters
    ----------
    hits : int or None
        Number of hits
    base_on_balls : int or None
        Number of walks
    hit_by_pitch : int or None
        Number of hit by pitches
    at_bats : int or None
        Number of at bats
    sac_flies : int or None
        Number of sacrifice flies

    Returns
    -------
    str or None
        OBP formatted as ".XXX" or None if cannot calculate
    """
    h = hits or 0
    bb = base_on_balls or 0
    hbp = hit_by_pitch or 0
    ab = at_bats or 0
    sf = sac_flies or 0

    denominator = ab + bb + hbp + sf
    if denominator == 0:
        return None

    obp = (h + bb + hbp) / denominator
    if obp >= 1.0:
        return f"{obp:.3f}"
    return f"{obp:.3f}"


def _calculate_slg(total_bases: int | None, at_bats: int | None) -> str | None:
    """Calculate slugging percentage for a game.

    SLG = TB / AB

    Parameters
    ----------
    total_bases : int or None
        Total bases
    at_bats : int or None
        Number of at bats

    Returns
    -------
    str or None
        SLG formatted as ".XXX" or "X.XXX" or None if cannot calculate
    """
    if total_bases is None or at_bats is None or at_bats == 0:
        return None
    slg = total_bases / at_bats
    return f"{slg:.3f}"


def _calculate_ops(obp_str: str | None, slg_str: str | None) -> str | None:
    """Calculate OPS (OBP + SLG) for a game.

    Parameters
    ----------
    obp_str : str or None
        OBP as formatted string
    slg_str : str or None
        SLG as formatted string

    Returns
    -------
    str or None
        OPS formatted as ".XXX" or "X.XXX" or None if cannot calculate
    """
    if obp_str is None or slg_str is None:
        return None

    # Parse the string values to floats
    obp = float(obp_str)
    slg = float(slg_str)

    ops = obp + slg
    return f"{ops:.3f}"


def _parse_innings_pitched(ip_str: str | None) -> float | None:
    """Parse innings pitched string to float.

    Innings pitched uses baseball notation where .1 = 1/3 inning and .2 = 2/3 inning.
    E.g., "6.2" means 6 and 2/3 innings = 6.667 innings.

    Parameters
    ----------
    ip_str : str or None
        Innings pitched as string (e.g., "6.2")

    Returns
    -------
    float or None
        Innings pitched as decimal, or None if cannot parse
    """
    if ip_str is None:
        return None
    try:
        # Split into whole innings and partial
        if "." in ip_str:
            whole, partial = ip_str.split(".")
            whole_innings = int(whole)
            # Convert baseball notation (0, 1, 2) to thirds
            thirds = int(partial)
            return whole_innings + (thirds / 3)
        else:
            return float(ip_str)
    except (ValueError, TypeError):
        return None


def _calculate_era(earned_runs: int | None, innings_pitched_str: str | None) -> str | None:
    """Calculate ERA for a game.

    ERA = (Earned Runs / Innings Pitched) * 9

    Parameters
    ----------
    earned_runs : int or None
        Number of earned runs allowed
    innings_pitched_str : str or None
        Innings pitched as string (e.g., "6.2")

    Returns
    -------
    str or None
        ERA formatted as "X.XX" or None if cannot calculate
    """
    if earned_runs is None:
        return None

    innings = _parse_innings_pitched(innings_pitched_str)
    if innings is None or innings == 0:
        return None

    era = (earned_runs / innings) * 9
    return f"{era:.2f}"


def _calculate_whip(
    hits: int | None,
    base_on_balls: int | None,
    innings_pitched_str: str | None,
) -> str | None:
    """Calculate WHIP for a game.

    WHIP = (Walks + Hits) / Innings Pitched

    Parameters
    ----------
    hits : int or None
        Hits allowed
    base_on_balls : int or None
        Walks allowed
    innings_pitched_str : str or None
        Innings pitched as string (e.g., "6.2")

    Returns
    -------
    str or None
        WHIP formatted as "X.XX" or None if cannot calculate
    """
    innings = _parse_innings_pitched(innings_pitched_str)
    if innings is None or innings == 0:
        return None

    h = hits or 0
    bb = base_on_balls or 0

    whip = (h + bb) / innings
    return f"{whip:.2f}"


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

            # Extract counting stats
            hits = batting.get("hits")
            at_bats = batting.get("atBats")
            base_on_balls = batting.get("baseOnBalls")
            hit_by_pitch = batting.get("hitByPitch")
            sac_flies = batting.get("sacFlies")
            total_bases = batting.get("totalBases")
            home_runs = batting.get("homeRuns")

            # Calculate rate stats for this game
            avg = _calculate_batting_avg(hits, at_bats)
            obp = _calculate_obp(hits, base_on_balls, hit_by_pitch, at_bats, sac_flies)
            slg = _calculate_slg(total_bases, at_bats)
            ops = _calculate_ops(obp, slg)

            # Calculate at bats per home run
            at_bats_per_hr = None
            if home_runs and home_runs > 0 and at_bats:
                at_bats_per_hr = f"{at_bats / home_runs:.2f}"

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
                "homeRuns": home_runs,
                "strikeOuts": batting.get("strikeOuts"),
                "baseOnBalls": base_on_balls,
                "intentionalWalks": batting.get("intentionalWalks"),
                "hits": hits,
                "hitByPitch": hit_by_pitch,
                "atBats": at_bats,
                "caughtStealing": batting.get("caughtStealing"),
                "stolenBases": batting.get("stolenBases"),
                "groundIntoDoublePlay": batting.get("groundIntoDoublePlay"),
                "groundIntoTriplePlay": batting.get("groundIntoTriplePlay"),
                "plateAppearances": batting.get("plateAppearances"),
                "totalBases": total_bases,
                "rbi": batting.get("rbi"),
                "leftOnBase": batting.get("leftOnBase"),
                "sacBunts": batting.get("sacBunts"),
                "sacFlies": sac_flies,
                "catchersInterference": batting.get("catchersInterference"),
                "pickoffs": batting.get("pickoffs"),
                # Calculated rate stats for this game
                "avg": avg,
                "obp": obp,
                "slg": slg,
                "ops": ops,
                "atBatsPerHomeRun": at_bats_per_hr,
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
    note field (W/L/S/H/BS) is from stats.pitching.note (game-level decision).
    ERA and WHIP are calculated from game-level stats.
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

            # Get W/L/S/H/BS note from game-level stats (not seasonStats)
            note = pitching.get("note")

            # Extract counting stats for rate calculations
            earned_runs = pitching.get("earnedRuns")
            innings_pitched = pitching.get("inningsPitched")
            hits = pitching.get("hits")
            base_on_balls = pitching.get("baseOnBalls")

            # Calculate rate stats for this game
            era = _calculate_era(earned_runs, innings_pitched)
            whip = _calculate_whip(hits, base_on_balls, innings_pitched)

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
                "baseOnBalls": base_on_balls,
                "intentionalWalks": pitching.get("intentionalWalks"),
                "hits": hits,
                "hitByPitch": pitching.get("hitByPitch"),
                "atBats": pitching.get("atBats"),
                "caughtStealing": pitching.get("caughtStealing"),
                "stolenBases": pitching.get("stolenBases"),
                "numberOfPitches": pitching.get("numberOfPitches"),
                "inningsPitched": innings_pitched,
                "wins": pitching.get("wins"),
                "losses": pitching.get("losses"),
                "saves": pitching.get("saves"),
                "saveOpportunities": pitching.get("saveOpportunities"),
                "holds": pitching.get("holds"),
                "blownSaves": pitching.get("blownSaves"),
                "earnedRuns": earned_runs,
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
                # Calculated rate stats for this game
                "era": era,
                "whip": whip,
                # Game result attribution (W/L/S/H/BS)
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
