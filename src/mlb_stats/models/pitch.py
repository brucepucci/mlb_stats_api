"""Pitch data transformation functions."""

from typing import Any


def transform_at_bat(
    play: dict,
    game_pk: int,
    fetched_at: str,
) -> dict:
    """Transform a play to an at_bats table row.

    Parameters
    ----------
    play : dict
        Single play from allPlays array
    game_pk : int
        Game primary key
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row dict for at_bats table
    """
    about = play.get("about", {})
    result = play.get("result", {})
    matchup = play.get("matchup", {})
    count = play.get("count", {})

    # Count pitches in this at-bat
    play_events = play.get("playEvents", [])
    pitch_count = sum(1 for e in play_events if e.get("isPitch"))

    return {
        "gamePk": game_pk,
        "atBatIndex": about.get("atBatIndex"),
        # Inning context
        "inning": about.get("inning"),
        "halfInning": about.get("halfInning"),
        # Matchup
        "batter_id": matchup.get("batter", {}).get("id"),
        "pitcher_id": matchup.get("pitcher", {}).get("id"),
        "batSide_code": matchup.get("batSide", {}).get("code"),
        "pitchHand_code": matchup.get("pitchHand", {}).get("code"),
        # Result
        "event": result.get("event"),
        "eventType": result.get("eventType"),
        "description": result.get("description"),
        # Scoring
        "rbi": result.get("rbi"),
        "awayScore": result.get("awayScore"),
        "homeScore": result.get("homeScore"),
        # At-bat details
        "isComplete": _bool_to_int(about.get("isComplete")),
        "hasReview": _bool_to_int(about.get("hasReview")),
        "hasOut": _bool_to_int(about.get("hasOut")),
        "isScoringPlay": _bool_to_int(about.get("isScoringPlay")),
        # Count at end
        "balls": count.get("balls"),
        "strikes": count.get("strikes"),
        "outs": count.get("outs"),
        # Timing
        "startTime": about.get("startTime"),
        "endTime": about.get("endTime"),
        # Pitch count
        "pitchCount": pitch_count,
        # Metadata
        "_fetched_at": fetched_at,
    }


def transform_pitch(
    play: dict,
    event: dict,
    game_pk: int,
    fetched_at: str,
) -> dict:
    """Transform a pitch event to a pitches table row.

    Parameters
    ----------
    play : dict
        Parent play from allPlays array (for context)
    event : dict
        Single pitch event from playEvents array
    game_pk : int
        Game primary key
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row dict for pitches table
    """
    about = play.get("about", {})
    matchup = play.get("matchup", {})
    details = event.get("details", {})
    pitch_data = event.get("pitchData", {})
    count = event.get("count", {})

    # Extract coordinates
    coordinates = pitch_data.get("coordinates", {})

    # Extract break metrics
    breaks = pitch_data.get("breaks", {})

    # Pitch type from details
    pitch_type = details.get("type", {})

    # Call info
    call = details.get("call", {})

    return {
        "gamePk": game_pk,
        # At-bat context
        "atBatIndex": about.get("atBatIndex"),
        "pitchNumber": event.get("pitchNumber"),
        # Inning context
        "inning": about.get("inning"),
        "halfInning": about.get("halfInning"),
        # Matchup
        "batter_id": matchup.get("batter", {}).get("id"),
        "pitcher_id": matchup.get("pitcher", {}).get("id"),
        # Batter/pitcher info at time of pitch
        "batSide_code": matchup.get("batSide", {}).get("code"),
        "pitchHand_code": matchup.get("pitchHand", {}).get("code"),
        # Count before pitch
        "balls": count.get("balls"),
        "strikes": count.get("strikes"),
        "outs": count.get("outs"),
        # Pitch result
        "call_code": call.get("code"),
        "call_description": call.get("description"),
        "isInPlay": _bool_to_int(details.get("isInPlay")),
        "isStrike": _bool_to_int(details.get("isStrike")),
        "isBall": _bool_to_int(details.get("isBall")),
        # Pitch type
        "type_code": pitch_type.get("code"),
        "type_description": pitch_type.get("description"),
        "typeConfidence": pitch_data.get("typeConfidence"),
        # Pitch velocity
        "startSpeed": pitch_data.get("startSpeed"),
        "endSpeed": pitch_data.get("endSpeed"),
        # Strike zone
        "zone": pitch_data.get("zone"),
        "strikeZoneTop": pitch_data.get("strikeZoneTop"),
        "strikeZoneBottom": pitch_data.get("strikeZoneBottom"),
        # Pitch location at plate (pX -> plateX, pZ -> plateZ)
        "plateX": coordinates.get("pX"),
        "plateZ": coordinates.get("pZ"),
        # Pitch coordinates (legacy/display)
        "coordinates_x": coordinates.get("x"),
        "coordinates_y": coordinates.get("y"),
        # Release point
        "x0": coordinates.get("x0"),
        "y0": coordinates.get("y0"),
        "z0": coordinates.get("z0"),
        # Initial velocity components
        "vX0": coordinates.get("vX0"),
        "vY0": coordinates.get("vY0"),
        "vZ0": coordinates.get("vZ0"),
        # Acceleration components
        "aX": coordinates.get("aX"),
        "aY": coordinates.get("aY"),
        "aZ": coordinates.get("aZ"),
        # Movement (PITCHf/x style)
        "pfxX": coordinates.get("pfxX"),
        "pfxZ": coordinates.get("pfxZ"),
        # Statcast break metrics
        "breakAngle": breaks.get("breakAngle"),
        "breakLength": breaks.get("breakLength"),
        "breakY": breaks.get("breakY"),
        # Statcast spin metrics
        "spinRate": breaks.get("spinRate"),
        "spinDirection": breaks.get("spinDirection"),
        # Statcast timing/extension
        "plateTime": pitch_data.get("plateTime"),
        "extension": pitch_data.get("extension"),
        # Timestamps
        "startTime": event.get("startTime"),
        "endTime": event.get("endTime"),
        # Metadata
        "playId": event.get("playId"),
        "_fetched_at": fetched_at,
    }


def transform_batted_ball(
    play: dict,
    event: dict,
    game_pk: int,
    fetched_at: str,
) -> dict:
    """Transform a batted ball event to a batted_balls table row.

    Parameters
    ----------
    play : dict
        Parent play from allPlays array (for result context)
    event : dict
        The pitch event that was put in play (must have hitData)
    game_pk : int
        Game primary key
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row dict for batted_balls table
    """
    about = play.get("about", {})
    result = play.get("result", {})
    matchup = play.get("matchup", {})
    hit_data = event.get("hitData", {})
    hit_coords = hit_data.get("coordinates", {})

    return {
        "gamePk": game_pk,
        # Link to pitch that was hit
        "atBatIndex": about.get("atBatIndex"),
        "pitchNumber": event.get("pitchNumber"),
        # Matchup
        "batter_id": matchup.get("batter", {}).get("id"),
        "pitcher_id": matchup.get("pitcher", {}).get("id"),
        # Inning context
        "inning": about.get("inning"),
        "halfInning": about.get("halfInning"),
        # Statcast batted ball metrics
        "launchSpeed": hit_data.get("launchSpeed"),
        "launchAngle": hit_data.get("launchAngle"),
        "totalDistance": hit_data.get("totalDistance"),
        # Batted ball classification
        "trajectory": hit_data.get("trajectory"),
        "hardness": hit_data.get("hardness"),
        # Field location
        "location": hit_data.get("location"),
        "coordinates_x": hit_coords.get("coordX"),
        "coordinates_y": hit_coords.get("coordY"),
        # Play result (from parent play)
        "event": result.get("event"),
        "eventType": result.get("eventType"),
        "description": result.get("description"),
        # Scoring impact
        "rbi": result.get("rbi"),
        "awayScore": result.get("awayScore"),
        "homeScore": result.get("homeScore"),
        # Calculated metrics (if available from API)
        "hitProbability": hit_data.get("hitProbability"),
        # Enhanced Statcast fields (2024+ for bat tracking)
        "isBarrel": _bool_to_int(hit_data.get("isBarrel")),
        "batSpeed": hit_data.get("batSpeed"),
        "isSwordSwing": _bool_to_int(hit_data.get("isSwordSwing")),
        # Metadata
        "playId": event.get("playId"),
        "_fetched_at": fetched_at,
    }


def extract_pitches_from_play(play: dict) -> list[dict]:
    """Extract pitch events from a play.

    Parameters
    ----------
    play : dict
        Single play from allPlays array

    Returns
    -------
    list[dict]
        List of pitch events (filtered by isPitch=True)

    Notes
    -----
    Filters out non-pitch events like pickoffs, balks, etc.
    """
    events = play.get("playEvents", [])
    return [e for e in events if e.get("isPitch")]


def extract_batted_ball_event(play: dict) -> dict | None:
    """Find the batted ball event in a play, if any.

    Parameters
    ----------
    play : dict
        Single play from allPlays array

    Returns
    -------
    dict or None
        The pitch event that was put in play with hitData, or None

    Notes
    -----
    Looks for events where isInPlay=True and hitData exists.
    Returns the last such event (the final pitch of the at-bat).
    """
    events = play.get("playEvents", [])
    for event in reversed(events):
        details = event.get("details", {})
        if details.get("isInPlay") and event.get("hitData"):
            return event
    return None


def _bool_to_int(value: Any) -> int | None:
    """Convert boolean to integer (0/1) for SQLite.

    Parameters
    ----------
    value : Any
        Value to convert

    Returns
    -------
    int or None
        1 for True, 0 for False, None for None/missing
    """
    if value is None:
        return None
    return 1 if value else 0
