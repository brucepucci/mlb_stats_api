"""Venue data transformation functions."""


def _transform_venue_data(venue: dict, fetched_at: str) -> dict:
    """Transform raw venue data to database row.

    Parameters
    ----------
    venue : dict
        Raw venue data (from API response or game feed)
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching venues table schema
    """
    location = venue.get("location", {})

    return {
        "id": venue.get("id"),
        "name": venue.get("name"),
        "city": location.get("city"),
        "state": location.get("state"),
        "stateAbbrev": location.get("stateAbbrev"),
        "country": location.get("country"),
        "latitude": location.get("defaultCoordinates", {}).get("latitude"),
        "longitude": location.get("defaultCoordinates", {}).get("longitude"),
        "elevation": location.get("elevation"),
        "timezone": venue.get("timeZone", {}).get("id"),
        "_fetched_at": fetched_at,
    }


def transform_venue(api_response: dict, fetched_at: str) -> dict:
    """Transform API venue response to database row.

    Parameters
    ----------
    api_response : dict
        Raw API response from /v1/venues/{venueId}
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching venues table schema

    Notes
    -----
    Expects response with 'venues' array containing single venue.
    Location data (lat/long/elevation) may be missing for some venues.
    """
    venues = api_response.get("venues", [])
    venue = venues[0] if venues else {}
    return _transform_venue_data(venue, fetched_at)


def transform_venue_from_game_feed(venue_data: dict, fetched_at: str) -> dict:
    """Transform venue data from game feed to database row.

    Parameters
    ----------
    venue_data : dict
        Venue data from gameData.venue
    fetched_at : str
        ISO8601 timestamp when data was fetched

    Returns
    -------
    dict
        Row data matching venues table schema
    """
    return _transform_venue_data(venue_data, fetched_at)
