"""Shared pytest fixtures for MLB Stats Collector tests."""

import sqlite3
from pathlib import Path

import pytest

from mlb_stats.api.cache import ResponseCache
from mlb_stats.api.client import MLBStatsClient
from mlb_stats.db.connection import init_db


@pytest.fixture
def temp_db(tmp_path: Path) -> sqlite3.Connection:
    """Create a temporary test database with all tables.

    Yields
    ------
    sqlite3.Connection
        Connection to temporary database
    """
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Get path for a temporary database (not yet created).

    Returns
    -------
    Path
        Path to temporary database file
    """
    return tmp_path / "test.db"


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory.

    Returns
    -------
    Path
        Path to temporary cache directory
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def response_cache(temp_cache_dir: Path) -> ResponseCache:
    """Create a ResponseCache instance with temporary directory.

    Returns
    -------
    ResponseCache
        Cache instance for testing
    """
    return ResponseCache(temp_cache_dir)


@pytest.fixture
def mock_client(temp_cache_dir: Path) -> MLBStatsClient:
    """Create an MLBStatsClient with mocked responses enabled.

    Returns
    -------
    MLBStatsClient
        Client configured for testing with cache
    """
    return MLBStatsClient(
        request_delay=0.0,  # No delay for tests
        max_retries=1,
        cache_dir=temp_cache_dir,
        use_cache=True,
    )


@pytest.fixture
def sample_game_feed() -> dict:
    """Sample game feed response for testing.

    Returns
    -------
    dict
        Game feed structure with teams and players
    """
    return {
        "gamePk": 745927,
        "gameData": {
            "game": {"pk": 745927, "type": "R", "season": "2024"},
            "datetime": {"dateTime": "2024-07-02T02:10:00Z", "officialDate": "2024-07-01"},
            "status": {"abstractGameState": "Final", "detailedState": "Final"},
            "teams": {
                "away": {
                    "id": 137,
                    "name": "San Francisco Giants",
                    "teamCode": "sfn",
                    "abbreviation": "SF",
                    "teamName": "Giants",
                    "locationName": "San Francisco",
                    "venue": {"id": 2395, "name": "Oracle Park"},
                    "league": {"id": 104, "name": "National League"},
                    "division": {"id": 203, "name": "NL West"},
                    "active": True,
                },
                "home": {
                    "id": 119,
                    "name": "Los Angeles Dodgers",
                    "teamCode": "lan",
                    "abbreviation": "LAD",
                    "teamName": "Dodgers",
                    "locationName": "Los Angeles",
                    "venue": {"id": 22, "name": "Dodger Stadium"},
                    "league": {"id": 104, "name": "National League"},
                    "division": {"id": 203, "name": "NL West"},
                    "active": True,
                },
            },
            "venue": {
                "id": 22,
                "name": "Dodger Stadium",
                "location": {
                    "city": "Los Angeles",
                    "state": "California",
                    "stateAbbrev": "CA",
                    "country": "USA",
                    "defaultCoordinates": {"latitude": 34.0739, "longitude": -118.24},
                },
                "timeZone": {"id": "America/Los_Angeles"},
            },
            "players": {
                "ID660271": {
                    "id": 660271,
                    "fullName": "Shohei Ohtani",
                    "firstName": "Shohei",
                    "lastName": "Ohtani",
                    "primaryNumber": "17",
                    "birthDate": "1994-07-05",
                    "birthCity": "Oshu",
                    "birthCountry": "Japan",
                    "height": "6' 4\"",
                    "weight": 210,
                    "active": True,
                    "primaryPosition": {
                        "code": "Y",
                        "name": "Two-Way Player",
                        "type": "Two-Way Player",
                        "abbreviation": "TWP",
                    },
                    "batSide": {"code": "L", "description": "Left"},
                    "pitchHand": {"code": "R", "description": "Right"},
                    "mlbDebutDate": "2018-03-29",
                },
                "ID543243": {
                    "id": 543243,
                    "fullName": "Test Pitcher",
                    "firstName": "Test",
                    "lastName": "Pitcher",
                    "primaryNumber": "22",
                    "birthDate": "1990-01-01",
                    "birthCity": "Test City",
                    "birthCountry": "USA",
                    "height": "6' 2\"",
                    "weight": 200,
                    "active": True,
                    "primaryPosition": {
                        "code": "1",
                        "name": "Pitcher",
                        "type": "Pitcher",
                        "abbreviation": "P",
                    },
                    "batSide": {"code": "R", "description": "Right"},
                    "pitchHand": {"code": "R", "description": "Right"},
                    "mlbDebutDate": "2015-04-01",
                },
            },
        },
        "liveData": {
            "boxscore": {
                "teams": {
                    "away": {"teamStats": {}, "players": {}},
                    "home": {"teamStats": {}, "players": {}},
                }
            },
            "plays": {
                "allPlays": [
                    {
                        "result": {
                            "type": "atBat",
                            "event": "Strikeout",
                            "eventType": "strikeout",
                            "description": "Test Batter strikes out.",
                            "rbi": 0,
                            "awayScore": 0,
                            "homeScore": 0,
                        },
                        "about": {
                            "atBatIndex": 0,
                            "halfInning": "top",
                            "inning": 1,
                            "startTime": "2024-07-02T02:15:00Z",
                            "endTime": "2024-07-02T02:18:00Z",
                            "isComplete": True,
                            "isScoringPlay": False,
                            "hasReview": False,
                            "hasOut": True,
                        },
                        "count": {"balls": 1, "strikes": 3, "outs": 1},
                        "matchup": {
                            "batter": {"id": 660271, "fullName": "Shohei Ohtani"},
                            "pitcher": {"id": 543243, "fullName": "Test Pitcher"},
                            "batSide": {"code": "L"},
                            "pitchHand": {"code": "R"},
                        },
                        "playEvents": [
                            {
                                "details": {
                                    "call": {"code": "B", "description": "Ball"},
                                    "isInPlay": False,
                                    "isStrike": False,
                                    "isBall": True,
                                    "type": {"code": "FF", "description": "Fastball"},
                                },
                                "count": {"balls": 1, "strikes": 0, "outs": 0},
                                "pitchData": {
                                    "startSpeed": 95.0,
                                    "endSpeed": 87.0,
                                    "zone": 14,
                                    "coordinates": {"pX": -1.5, "pZ": 3.3},
                                    "breaks": {"spinRate": 2400, "spinDirection": 180},
                                },
                                "pitchNumber": 1,
                                "playId": "test-pitch-1",
                                "isPitch": True,
                                "type": "pitch",
                            },
                            {
                                "details": {
                                    "call": {"code": "S", "description": "Strike"},
                                    "isInPlay": False,
                                    "isStrike": True,
                                    "isBall": False,
                                    "type": {"code": "SL", "description": "Slider"},
                                },
                                "count": {"balls": 1, "strikes": 1, "outs": 0},
                                "pitchData": {"startSpeed": 87.0},
                                "pitchNumber": 2,
                                "playId": "test-pitch-2",
                                "isPitch": True,
                                "type": "pitch",
                            },
                            {
                                "details": {
                                    "call": {"code": "S", "description": "Strike"},
                                    "isInPlay": False,
                                    "isStrike": True,
                                    "isBall": False,
                                    "type": {"code": "FF", "description": "Fastball"},
                                },
                                "count": {"balls": 1, "strikes": 2, "outs": 0},
                                "pitchData": {"startSpeed": 96.0},
                                "pitchNumber": 3,
                                "playId": "test-pitch-3",
                                "isPitch": True,
                                "type": "pitch",
                            },
                            {
                                "details": {
                                    "call": {"code": "S", "description": "Strike"},
                                    "isInPlay": False,
                                    "isStrike": True,
                                    "isBall": False,
                                    "type": {"code": "CH", "description": "Changeup"},
                                },
                                "count": {"balls": 1, "strikes": 3, "outs": 1},
                                "pitchData": {"startSpeed": 85.0},
                                "pitchNumber": 4,
                                "playId": "test-pitch-4",
                                "isPitch": True,
                                "type": "pitch",
                            },
                        ],
                    },
                    {
                        "result": {
                            "type": "atBat",
                            "event": "Single",
                            "eventType": "single",
                            "description": "Test Pitcher singles to left.",
                            "rbi": 0,
                            "awayScore": 0,
                            "homeScore": 0,
                        },
                        "about": {
                            "atBatIndex": 1,
                            "halfInning": "bottom",
                            "inning": 1,
                            "startTime": "2024-07-02T02:25:00Z",
                            "endTime": "2024-07-02T02:27:00Z",
                            "isComplete": True,
                            "isScoringPlay": False,
                            "hasReview": False,
                            "hasOut": False,
                        },
                        "count": {"balls": 1, "strikes": 0, "outs": 1},
                        "matchup": {
                            "batter": {"id": 543243, "fullName": "Test Pitcher"},
                            "pitcher": {"id": 660271, "fullName": "Shohei Ohtani"},
                            "batSide": {"code": "R"},
                            "pitchHand": {"code": "R"},
                        },
                        "playEvents": [
                            {
                                "details": {
                                    "call": {"code": "B", "description": "Ball"},
                                    "isInPlay": False,
                                    "isStrike": False,
                                    "isBall": True,
                                    "type": {"code": "FF", "description": "Fastball"},
                                },
                                "count": {"balls": 1, "strikes": 0, "outs": 1},
                                "pitchData": {"startSpeed": 98.0},
                                "pitchNumber": 1,
                                "playId": "test-pitch-5",
                                "isPitch": True,
                                "type": "pitch",
                            },
                            {
                                "details": {
                                    "call": {"code": "X", "description": "In play"},
                                    "isInPlay": True,
                                    "isStrike": False,
                                    "isBall": False,
                                    "type": {"code": "FF", "description": "Fastball"},
                                },
                                "count": {"balls": 1, "strikes": 0, "outs": 1},
                                "pitchData": {
                                    "startSpeed": 97.5,
                                    "coordinates": {"pX": 0.1, "pZ": 2.5},
                                },
                                "hitData": {
                                    "launchSpeed": 95.0,
                                    "launchAngle": 15,
                                    "totalDistance": 250,
                                    "trajectory": "line_drive",
                                    "hardness": "hard",
                                    "location": "7",
                                    "coordinates": {"coordX": 80.0, "coordY": 120.0},
                                },
                                "pitchNumber": 2,
                                "playId": "test-pitch-6",
                                "isPitch": True,
                                "type": "pitch",
                            },
                        ],
                    },
                ]
            },
        },
    }


@pytest.fixture
def sample_schedule() -> dict:
    """Sample schedule response for testing.

    Returns
    -------
    dict
        Minimal schedule structure
    """
    return {
        "dates": [
            {
                "date": "2024-07-01",
                "games": [
                    {
                        "gamePk": 745927,
                        "gameDate": "2024-07-02T02:10:00Z",
                        "status": {
                            "abstractGameState": "Final",
                            "detailedState": "Final",
                        },
                        "teams": {
                            "away": {
                                "team": {"id": 137, "name": "San Francisco Giants"}
                            },
                            "home": {
                                "team": {"id": 119, "name": "Los Angeles Dodgers"}
                            },
                        },
                        "venue": {"id": 22, "name": "Dodger Stadium"},
                    }
                ],
            }
        ]
    }


@pytest.fixture
def sample_player() -> dict:
    """Sample player response for testing.

    Returns
    -------
    dict
        Minimal player structure
    """
    return {
        "people": [
            {
                "id": 660271,
                "fullName": "Shohei Ohtani",
                "firstName": "Shohei",
                "lastName": "Ohtani",
                "primaryNumber": "17",
                "birthDate": "1994-07-05",
                "active": True,
                "primaryPosition": {"code": "Y", "name": "Two-Way Player"},
                "batSide": {"code": "L", "description": "Left"},
                "pitchHand": {"code": "R", "description": "Right"},
                "currentTeam": {"id": 119, "name": "Los Angeles Dodgers"},
            }
        ]
    }


@pytest.fixture
def sample_team() -> dict:
    """Sample team response for testing.

    Returns
    -------
    dict
        Minimal team structure
    """
    return {
        "teams": [
            {
                "id": 119,
                "name": "Los Angeles Dodgers",
                "teamCode": "lan",
                "abbreviation": "LAD",
                "teamName": "Dodgers",
                "locationName": "Los Angeles",
                "active": True,
                "league": {"id": 104, "name": "National League"},
                "division": {"id": 203, "name": "National League West"},
                "venue": {"id": 22, "name": "Dodger Stadium"},
            }
        ]
    }


@pytest.fixture
def sample_venue() -> dict:
    """Sample venue response for testing.

    Returns
    -------
    dict
        Venue structure from /v1/venues/{venueId}?hydrate=location,fieldInfo,timezone
    """
    return {
        "venues": [
            {
                "id": 22,
                "name": "Dodger Stadium",
                "link": "/api/v1/venues/22",
                "active": True,
                "season": "2024",
                "location": {
                    "address1": "1000 Vin Scully Avenue",
                    "city": "Los Angeles",
                    "state": "California",
                    "stateAbbrev": "CA",
                    "postalCode": "90012-1199",
                    "country": "USA",
                    "phone": "(323) 224-1500",
                    "defaultCoordinates": {
                        "latitude": 34.07368,
                        "longitude": -118.24053,
                    },
                    "azimuthAngle": 26.0,
                    "elevation": 515,
                },
                "timeZone": {
                    "tz": "PST",
                    "id": "America/Los_Angeles",
                    "offset": -8,
                },
                "fieldInfo": {
                    "capacity": 56000,
                    "turfType": "Grass",
                    "roofType": "Open",
                    "leftLine": 330,
                    "leftCenter": 385,
                    "center": 395,
                    "rightCenter": 385,
                    "rightLine": 330,
                },
            }
        ]
    }


@pytest.fixture
def sample_boxscore() -> dict:
    """Sample boxscore response for testing.

    Returns
    -------
    dict
        Minimal boxscore structure with batting and pitching stats
    """
    return {
        "teams": {
            "away": {
                "team": {"id": 137, "name": "San Francisco Giants"},
                "players": {
                    "ID660271": {
                        "person": {"id": 660271, "fullName": "Shohei Ohtani"},
                        "jerseyNumber": "17",
                        "position": {
                            "code": "10",
                            "name": "Designated Hitter",
                            "abbreviation": "DH",
                        },
                        "battingOrder": "100",
                        "stats": {
                            "batting": {
                                "gamesPlayed": 1,
                                "runs": 1,
                                "hits": 2,
                                "homeRuns": 1,
                                "strikeOuts": 1,
                                "baseOnBalls": 0,
                                "hitByPitch": 0,
                                "atBats": 4,
                                "rbi": 2,
                                "totalBases": 5,
                                "sacFlies": 0,
                            }
                        },
                        "gameStatus": {"isCurrentBatter": False},
                    }
                },
                "pitchers": [543243],
                "battingOrder": [660271],
            },
            "home": {
                "team": {"id": 119, "name": "Los Angeles Dodgers"},
                "players": {
                    "ID543243": {
                        "person": {"id": 543243, "fullName": "Test Pitcher"},
                        "jerseyNumber": "22",
                        "position": {
                            "code": "1",
                            "name": "Pitcher",
                            "abbreviation": "P",
                        },
                        "stats": {
                            "pitching": {
                                "gamesPlayed": 1,
                                "gamesStarted": 1,
                                "inningsPitched": "6.0",
                                "strikeOuts": 8,
                                "baseOnBalls": 2,
                                "hits": 5,
                                "earnedRuns": 2,
                                "runs": 3,
                                "homeRuns": 1,
                                "note": "(W, 5-2)",
                            }
                        },
                        "gameStatus": {"isStartingPitcher": True},
                    }
                },
                "pitchers": [543243],
                "battingOrder": [],
            },
        }
    }


@pytest.fixture
def sample_play() -> dict:
    """Sample play (at-bat) from allPlays for testing.

    Returns
    -------
    dict
        Complete play structure with pitch events
    """
    return {
        "result": {
            "type": "atBat",
            "event": "Strikeout",
            "eventType": "strikeout",
            "description": "Test Batter strikes out swinging.",
            "rbi": 0,
            "awayScore": 0,
            "homeScore": 0,
            "isOut": True,
        },
        "about": {
            "atBatIndex": 0,
            "halfInning": "top",
            "isTopInning": True,
            "inning": 1,
            "startTime": "2024-07-02T02:15:00Z",
            "endTime": "2024-07-02T02:18:00Z",
            "isComplete": True,
            "isScoringPlay": False,
            "hasReview": False,
            "hasOut": True,
        },
        "count": {
            "balls": 1,
            "strikes": 3,
            "outs": 1,
        },
        "matchup": {
            "batter": {"id": 660271, "fullName": "Shohei Ohtani"},
            "pitcher": {"id": 543243, "fullName": "Test Pitcher"},
            "batSide": {"code": "L", "description": "Left"},
            "pitchHand": {"code": "R", "description": "Right"},
        },
        "playEvents": [
            {
                "details": {
                    "call": {"code": "B", "description": "Ball"},
                    "description": "Ball",
                    "isInPlay": False,
                    "isStrike": False,
                    "isBall": True,
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
                "count": {"balls": 1, "strikes": 0, "outs": 0},
                "pitchData": {
                    "startSpeed": 95.2,
                    "endSpeed": 87.1,
                    "zone": 14,
                    "strikeZoneTop": 3.49,
                    "strikeZoneBottom": 1.6,
                    "coordinates": {
                        "x": 120.5,
                        "y": 180.3,
                        "pX": -1.45,
                        "pZ": 3.31,
                        "x0": -1.72,
                        "y0": 50.0,
                        "z0": 5.64,
                        "vX0": 8.21,
                        "vY0": -128.65,
                        "vZ0": -6.34,
                        "aX": 0.24,
                        "aY": 27.1,
                        "aZ": -31.21,
                        "pfxX": -6.15,
                        "pfxZ": 7.57,
                    },
                    "breaks": {
                        "breakAngle": 3.6,
                        "breakLength": 8.4,
                        "breakY": 24.0,
                        "spinRate": 2423,
                        "spinDirection": 184,
                    },
                    "typeConfidence": 0.9,
                    "plateTime": 0.43,
                    "extension": 6.22,
                },
                "index": 0,
                "playId": "pitch-1",
                "pitchNumber": 1,
                "startTime": "2024-07-02T02:15:00Z",
                "endTime": "2024-07-02T02:15:05Z",
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "S", "description": "Swinging Strike"},
                    "description": "Swinging Strike",
                    "isInPlay": False,
                    "isStrike": True,
                    "isBall": False,
                    "type": {"code": "SL", "description": "Slider"},
                },
                "count": {"balls": 1, "strikes": 1, "outs": 0},
                "pitchData": {
                    "startSpeed": 87.5,
                    "endSpeed": 80.2,
                    "zone": 6,
                    "strikeZoneTop": 3.49,
                    "strikeZoneBottom": 1.6,
                    "coordinates": {
                        "x": 115.0,
                        "y": 175.0,
                        "pX": 0.35,
                        "pZ": 2.1,
                    },
                    "breaks": {
                        "spinRate": 2650,
                        "spinDirection": 45,
                    },
                    "typeConfidence": 0.85,
                },
                "index": 1,
                "playId": "pitch-2",
                "pitchNumber": 2,
                "startTime": "2024-07-02T02:15:30Z",
                "endTime": "2024-07-02T02:15:35Z",
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "S", "description": "Swinging Strike"},
                    "description": "Swinging Strike",
                    "isInPlay": False,
                    "isStrike": True,
                    "isBall": False,
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
                "count": {"balls": 1, "strikes": 2, "outs": 0},
                "pitchData": {
                    "startSpeed": 96.0,
                    "endSpeed": 88.0,
                    "zone": 5,
                    "strikeZoneTop": 3.49,
                    "strikeZoneBottom": 1.6,
                    "coordinates": {
                        "pX": 0.1,
                        "pZ": 2.5,
                    },
                },
                "index": 2,
                "playId": "pitch-3",
                "pitchNumber": 3,
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "S", "description": "Swinging Strike"},
                    "description": "Swinging Strike",
                    "isInPlay": False,
                    "isStrike": True,
                    "isBall": False,
                    "type": {"code": "CH", "description": "Changeup"},
                },
                "count": {"balls": 1, "strikes": 3, "outs": 1},
                "pitchData": {
                    "startSpeed": 85.0,
                    "endSpeed": 78.0,
                    "zone": 6,
                },
                "index": 3,
                "playId": "pitch-4",
                "pitchNumber": 4,
                "isPitch": True,
                "type": "pitch",
            },
        ],
    }


@pytest.fixture
def sample_play_with_hit() -> dict:
    """Sample play with a ball put in play for testing batted ball data.

    Returns
    -------
    dict
        Play structure with hitData on the final pitch
    """
    return {
        "result": {
            "type": "atBat",
            "event": "Single",
            "eventType": "single",
            "description": "Test Batter singles to left field.",
            "rbi": 1,
            "awayScore": 1,
            "homeScore": 0,
            "isOut": False,
        },
        "about": {
            "atBatIndex": 5,
            "halfInning": "top",
            "isTopInning": True,
            "inning": 2,
            "startTime": "2024-07-02T02:30:00Z",
            "endTime": "2024-07-02T02:32:00Z",
            "isComplete": True,
            "isScoringPlay": True,
            "hasReview": False,
            "hasOut": False,
        },
        "count": {
            "balls": 2,
            "strikes": 1,
            "outs": 0,
        },
        "matchup": {
            "batter": {"id": 660271, "fullName": "Shohei Ohtani"},
            "pitcher": {"id": 543243, "fullName": "Test Pitcher"},
            "batSide": {"code": "L", "description": "Left"},
            "pitchHand": {"code": "R", "description": "Right"},
        },
        "playEvents": [
            {
                "details": {
                    "call": {"code": "B", "description": "Ball"},
                    "isInPlay": False,
                    "isStrike": False,
                    "isBall": True,
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
                "count": {"balls": 1, "strikes": 0, "outs": 0},
                "pitchData": {"startSpeed": 94.5},
                "pitchNumber": 1,
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "C", "description": "Called Strike"},
                    "isInPlay": False,
                    "isStrike": True,
                    "isBall": False,
                    "type": {"code": "SL", "description": "Slider"},
                },
                "count": {"balls": 1, "strikes": 1, "outs": 0},
                "pitchData": {"startSpeed": 86.0},
                "pitchNumber": 2,
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "B", "description": "Ball"},
                    "isInPlay": False,
                    "isStrike": False,
                    "isBall": True,
                    "type": {"code": "CH", "description": "Changeup"},
                },
                "count": {"balls": 2, "strikes": 1, "outs": 0},
                "pitchData": {"startSpeed": 84.0},
                "pitchNumber": 3,
                "isPitch": True,
                "type": "pitch",
            },
            {
                "details": {
                    "call": {"code": "X", "description": "In play, no out"},
                    "description": "In play, no out",
                    "isInPlay": True,
                    "isStrike": False,
                    "isBall": False,
                    "type": {"code": "FF", "description": "Four-Seam Fastball"},
                },
                "count": {"balls": 2, "strikes": 1, "outs": 0},
                "pitchData": {
                    "startSpeed": 95.0,
                    "endSpeed": 87.0,
                    "zone": 5,
                    "coordinates": {
                        "pX": 0.2,
                        "pZ": 2.8,
                    },
                },
                "hitData": {
                    "launchSpeed": 101.9,
                    "launchAngle": 12,
                    "totalDistance": 285,
                    "trajectory": "line_drive",
                    "hardness": "hard",
                    "location": "7",
                    "coordinates": {
                        "coordX": 85.4,
                        "coordY": 125.2,
                    },
                },
                "index": 3,
                "playId": "hit-pitch-1",
                "pitchNumber": 4,
                "isPitch": True,
                "type": "pitch",
            },
        ],
    }


@pytest.fixture
def sample_roster() -> dict:
    """Sample roster response for testing.

    Returns
    -------
    dict
        Roster structure from /v1/teams/{teamId}/roster/active
    """
    return {
        "roster": [
            {
                "person": {"id": 660271, "fullName": "Shohei Ohtani"},
                "jerseyNumber": "17",
                "position": {
                    "code": "Y",
                    "name": "Two-Way Player",
                    "type": "Two-Way Player",
                    "abbreviation": "TWP",
                },
                "status": {"code": "A", "description": "Active"},
                "parentTeamId": 119,
            },
            {
                "person": {"id": 543243, "fullName": "Test Pitcher"},
                "jerseyNumber": "22",
                "position": {
                    "code": "1",
                    "name": "Pitcher",
                    "type": "Pitcher",
                    "abbreviation": "P",
                },
                "status": {"code": "A", "description": "Active"},
                "parentTeamId": 119,
            },
            {
                "person": {"id": 592450, "fullName": "Mookie Betts"},
                "jerseyNumber": "50",
                "position": {
                    "code": "6",
                    "name": "Shortstop",
                    "type": "Infielder",
                    "abbreviation": "SS",
                },
                "status": {"code": "A", "description": "Active"},
                "parentTeamId": 119,
            },
        ],
        "teamId": 119,
        "rosterType": "active",
    }


# Fixtures directory path helper
@pytest.fixture
def fixtures_dir() -> Path:
    """Get path to test fixtures directory.

    Returns
    -------
    Path
        Path to fixtures directory
    """
    return Path(__file__).parent / "fixtures"
