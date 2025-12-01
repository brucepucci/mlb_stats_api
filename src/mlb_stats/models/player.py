"""Player data transformation functions."""


def transform_player(api_response: dict, fetched_at: str) -> dict:
    """Transform API player response to database row.

    Parameters
    ----------
    api_response : dict
        Raw API response from /v1/people/{personId}
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching players table schema

    Notes
    -----
    Expects response with 'people' array containing single player.
    Flattens nested objects (primaryPosition, batSide, pitchHand, currentTeam)
    with underscore separator.
    """
    people = api_response.get("people", [])
    player = people[0] if people else {}

    return {
        # Basic info
        "id": player.get("id"),
        "fullName": player.get("fullName"),
        "firstName": player.get("firstName"),
        "lastName": player.get("lastName"),
        "useName": player.get("useName"),
        "middleName": player.get("middleName"),
        "boxscoreName": player.get("boxscoreName"),
        "nickName": player.get("nickName"),
        # Bio info
        "primaryNumber": player.get("primaryNumber"),
        "birthDate": player.get("birthDate"),
        "birthCity": player.get("birthCity"),
        "birthStateProvince": player.get("birthStateProvince"),
        "birthCountry": player.get("birthCountry"),
        "deathDate": player.get("deathDate"),
        "deathCity": player.get("deathCity"),
        "deathStateProvince": player.get("deathStateProvince"),
        "deathCountry": player.get("deathCountry"),
        # Physical
        "height": player.get("height"),
        "weight": player.get("weight"),
        # Primary position (flattened)
        "primaryPosition_code": player.get("primaryPosition", {}).get("code"),
        "primaryPosition_name": player.get("primaryPosition", {}).get("name"),
        "primaryPosition_type": player.get("primaryPosition", {}).get("type"),
        "primaryPosition_abbreviation": player.get("primaryPosition", {}).get(
            "abbreviation"
        ),
        # Handedness (flattened)
        "batSide_code": player.get("batSide", {}).get("code"),
        "batSide_description": player.get("batSide", {}).get("description"),
        "pitchHand_code": player.get("pitchHand", {}).get("code"),
        "pitchHand_description": player.get("pitchHand", {}).get("description"),
        # Career info
        "draftYear": player.get("draftYear"),
        "mlbDebutDate": player.get("mlbDebutDate"),
        "lastPlayedDate": player.get("lastPlayedDate"),
        "active": 1 if player.get("active") else 0,
        # Current team (flattened)
        "currentTeam_id": player.get("currentTeam", {}).get("id"),
        # API fetch metadata
        "_fetched_at": fetched_at,
    }
