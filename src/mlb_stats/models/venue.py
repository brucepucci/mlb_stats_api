"""Venue data transformation functions."""


def _transform_venue_data(venue: dict, fetched_at: str, year: int) -> dict:
    """Transform raw venue data to database row.

    Parameters
    ----------
    venue : dict
        Raw venue data (from API response or game feed)
    fetched_at : str
        ISO8601 timestamp when data was fetched
    year : int
        Year this venue data applies to (for composite PK)

    Returns
    -------
    dict
        Row data matching venues table schema
    """
    location = venue.get("location", {})
    coords = location.get("defaultCoordinates", {})
    time_zone = venue.get("timeZone", {})
    field_info = venue.get("fieldInfo", {})

    return {
        "id": venue.get("id"),
        "year": year,
        "name": venue.get("name"),
        "active": 1 if venue.get("active") else 0,
        # Location
        "address1": location.get("address1"),
        "city": location.get("city"),
        "state": location.get("state"),
        "stateAbbrev": location.get("stateAbbrev"),
        "postalCode": location.get("postalCode"),
        "country": location.get("country"),
        "phone": location.get("phone"),
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
        "azimuthAngle": location.get("azimuthAngle"),
        "elevation": location.get("elevation"),
        # Time zone
        "timeZone_id": time_zone.get("id"),
        "timeZone_offset": time_zone.get("offset"),
        "timeZone_tz": time_zone.get("tz"),
        # Field info
        "capacity": field_info.get("capacity"),
        "turfType": field_info.get("turfType"),
        "roofType": field_info.get("roofType"),
        # Dimensions
        "leftLine": field_info.get("leftLine"),
        "leftCenter": field_info.get("leftCenter"),
        "center": field_info.get("center"),
        "rightCenter": field_info.get("rightCenter"),
        "rightLine": field_info.get("rightLine"),
        # Metadata
        "_fetched_at": fetched_at,
    }


def transform_venue(api_response: dict, fetched_at: str, year: int) -> dict:
    """Transform API venue response to database row.

    Parameters
    ----------
    api_response : dict
        Raw API response from /v1/venues/{venueId}
    fetched_at : str
        ISO8601 timestamp when data was fetched
    year : int
        Year this venue data applies to (for composite PK)

    Returns
    -------
    dict
        Row data matching venues table schema

    Notes
    -----
    Expects response with 'venues' array containing single venue.
    Flattens nested objects (location, timeZone, fieldInfo) with underscore separator.
    """
    venues = api_response.get("venues", [])
    venue = venues[0] if venues else {}
    return _transform_venue_data(venue, fetched_at, year)


def transform_venue_from_game_feed(venue_data: dict, fetched_at: str, year: int) -> dict:
    """Transform venue data from game feed to database row.

    Parameters
    ----------
    venue_data : dict
        Venue data from gameData.venue
    fetched_at : str
        ISO8601 timestamp when data was fetched
    year : int
        Year this venue data applies to (for composite PK)

    Returns
    -------
    dict
        Row data matching venues table schema

    Notes
    -----
    Game feed venue data may not include all fields (especially fieldInfo).
    Missing fields will be None.
    """
    return _transform_venue_data(venue_data, fetched_at, year)
