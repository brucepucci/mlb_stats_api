"""Team data transformation functions."""


def transform_team(api_response: dict, fetched_at: str) -> dict:
    """Transform API team response to database row.

    Parameters
    ----------
    api_response : dict
        Raw API response from /v1/teams/{teamId}
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching teams table schema

    Notes
    -----
    Expects response with 'teams' array containing single team.
    Flattens nested objects (league, division, venue) with underscore separator.
    """
    # Extract team from response array
    teams = api_response.get("teams", [])
    team = teams[0] if teams else {}

    return {
        "id": team.get("id"),
        "name": team.get("name"),
        "teamCode": team.get("teamCode"),
        "fileCode": team.get("fileCode"),
        "abbreviation": team.get("abbreviation"),
        "teamName": team.get("teamName"),
        "locationName": team.get("locationName"),
        "firstYearOfPlay": team.get("firstYearOfPlay"),
        "league_id": team.get("league", {}).get("id"),
        "league_name": team.get("league", {}).get("name"),
        "division_id": team.get("division", {}).get("id"),
        "division_name": team.get("division", {}).get("name"),
        "venue_id": team.get("venue", {}).get("id"),
        "active": 1 if team.get("active") else 0,
        "_fetched_at": fetched_at,
    }
