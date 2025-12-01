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
        Minimal game feed structure
    """
    return {
        "gamePk": 745927,
        "gameData": {
            "game": {"pk": 745927, "type": "R", "season": "2024"},
            "datetime": {"dateTime": "2024-07-02T02:10:00Z"},
            "status": {"abstractGameState": "Final", "detailedState": "Final"},
            "teams": {
                "away": {"id": 137, "name": "San Francisco Giants"},
                "home": {"id": 119, "name": "Los Angeles Dodgers"},
            },
            "venue": {"id": 22, "name": "Dodger Stadium"},
        },
        "liveData": {
            "boxscore": {
                "teams": {
                    "away": {"teamStats": {}, "players": {}},
                    "home": {"teamStats": {}, "players": {}},
                }
            }
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
                                "atBats": 4,
                                "rbi": 2,
                                "avg": ".500",
                                "obp": ".500",
                                "slg": "1.250",
                                "ops": "1.750",
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
                                "era": "3.00",
                                "whip": "1.17",
                            }
                        },
                        "seasonStats": {"pitching": {"note": "W"}},
                        "gameStatus": {"isStartingPitcher": True},
                    }
                },
                "pitchers": [543243],
                "battingOrder": [],
            },
        }
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
