"""Roster data transformation functions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def transform_roster(
    roster_data: dict[str, Any],
    game_pk: int,
    team_id: int,
    fetched_at: str,
) -> list[dict]:
    """Transform roster API response to game_rosters rows.

    Parameters
    ----------
    roster_data : dict
        Raw API response from /v1/teams/{teamId}/roster/active
    game_pk : int
        Game primary key to associate roster with
    team_id : int
        Team ID
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    list[dict]
        List of row dicts for game_rosters table

    Notes
    -----
    Each player in the roster becomes one row in game_rosters.
    """
    rows = []
    roster = roster_data.get("roster", [])

    for player_entry in roster:
        person = player_entry.get("person", {})
        position = player_entry.get("position", {})
        status = player_entry.get("status", {})

        player_id = person.get("id")
        if not player_id:
            logger.debug("Skipping roster entry without player_id: %s", player_entry)
            continue

        row = {
            "gamePk": game_pk,
            "team_id": team_id,
            "player_id": player_id,
            "jerseyNumber": player_entry.get("jerseyNumber"),
            "position_code": position.get("code"),
            "position_name": position.get("name"),
            "position_type": position.get("type"),
            "position_abbreviation": position.get("abbreviation"),
            "status_code": status.get("code"),
            "status_description": status.get("description"),
            "_fetched_at": fetched_at,
        }
        rows.append(row)

    return rows


def extract_roster_player_ids(roster_data: dict[str, Any]) -> set[int]:
    """Extract player IDs from roster response.

    Parameters
    ----------
    roster_data : dict
        Raw API response from roster endpoint

    Returns
    -------
    set[int]
        Set of player IDs on the roster
    """
    player_ids: set[int] = set()
    roster = roster_data.get("roster", [])

    for player_entry in roster:
        person = player_entry.get("person", {})
        player_id = person.get("id")
        if player_id:
            player_ids.add(player_id)

    return player_ids
