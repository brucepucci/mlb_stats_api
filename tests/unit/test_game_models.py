"""Tests for game transformation functions."""

import json
from pathlib import Path

from mlb_stats.models.game import (
    _extract_attendance,
    _extract_home_plate_umpire,
    transform_game,
    transform_officials,
)


class TestTransformGame:
    """Tests for transform_game function."""

    def test_basic_fields(self, sample_game_feed: dict) -> None:
        """Test transformation extracts basic game fields."""
        result = transform_game(sample_game_feed, "2024-07-01T00:00:00Z")

        assert result["gamePk"] == 745927
        assert result["season"] == 2024
        assert result["gameType"] == "R"
        assert result["away_team_id"] == 137
        assert result["home_team_id"] == 119
        assert result["venue_id"] == 22
        assert result["venue_name"] == "Dodger Stadium"
        assert result["abstractGameState"] == "Final"
        assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test transformation with real API response fixture."""
        fixture_path = fixtures_dir / "game_feed_745927.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            result = transform_game(data, "2024-07-01T00:00:00Z")

            assert result["gamePk"] == 745927
            assert result["season"] == 2024
            assert result["gameType"] == "R"
            # Real fixture should have scores
            assert result["away_score"] is not None or result["home_score"] is not None

    def test_missing_weather(self) -> None:
        """Test transformation with missing weather data."""
        game_feed = {
            "gamePk": 123456,
            "gameData": {
                "game": {"type": "R", "season": "2024"},
                "datetime": {"dateTime": "2024-07-01T00:00:00Z"},
                "status": {"abstractGameState": "Final"},
                "teams": {"away": {"id": 1}, "home": {"id": 2}},
                "venue": {"id": 1},
            },
            "liveData": {"boxscore": {}, "linescore": {}},
        }

        result = transform_game(game_feed, "2024-07-01T00:00:00Z")

        assert result["weather_condition"] is None
        assert result["weather_temp"] is None
        assert result["weather_wind"] is None

    def test_season_as_string(self) -> None:
        """Test that string season is converted to int."""
        game_feed = {
            "gamePk": 123456,
            "gameData": {
                "game": {"type": "R", "season": "2024"},
                "datetime": {"dateTime": "2024-07-01T00:00:00Z"},
                "status": {},
                "teams": {"away": {}, "home": {}},
                "venue": {},
            },
            "liveData": {"boxscore": {}, "linescore": {}},
        }

        result = transform_game(game_feed, "2024-07-01T00:00:00Z")

        assert result["season"] == 2024
        assert isinstance(result["season"], int)

    def test_game_date_from_datetime(self) -> None:
        """Test gameDate extracted from dateTime when officialDate missing."""
        game_feed = {
            "gamePk": 123456,
            "gameData": {
                "game": {"type": "R", "season": "2024"},
                "datetime": {"dateTime": "2024-07-15T02:10:00Z"},
                "status": {},
                "teams": {"away": {}, "home": {}},
                "venue": {},
            },
            "liveData": {"boxscore": {}, "linescore": {}},
        }

        result = transform_game(game_feed, "2024-07-01T00:00:00Z")

        assert result["gameDate"] == "2024-07-15"


class TestTransformOfficials:
    """Tests for transform_officials function."""

    def test_extracts_officials(self) -> None:
        """Test extraction of officials from boxscore."""
        game_feed = {
            "liveData": {
                "boxscore": {
                    "officials": [
                        {
                            "official": {"id": 100, "fullName": "John Umpire"},
                            "officialType": "Home Plate",
                        },
                        {
                            "official": {"id": 101, "fullName": "Jane Umpire"},
                            "officialType": "First Base",
                        },
                        {
                            "official": {"id": 102, "fullName": "Bob Umpire"},
                            "officialType": "Second Base",
                        },
                        {
                            "official": {"id": 103, "fullName": "Sue Umpire"},
                            "officialType": "Third Base",
                        },
                    ]
                }
            }
        }

        result = transform_officials(game_feed, 745927)

        assert len(result) == 4
        assert result[0]["gamePk"] == 745927
        assert result[0]["official_id"] == 100
        assert result[0]["official_fullName"] == "John Umpire"
        assert result[0]["officialType"] == "Home Plate"

    def test_empty_officials(self) -> None:
        """Test empty list when no officials present."""
        game_feed = {"liveData": {"boxscore": {}}}

        result = transform_officials(game_feed, 745927)

        assert result == []

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test officials extraction with real API response."""
        fixture_path = fixtures_dir / "game_feed_745927.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            result = transform_officials(data, 745927)

            # Real games typically have 4 umpires
            assert len(result) >= 4
            for official in result:
                assert official["gamePk"] == 745927
                assert "official_id" in official
                assert "officialType" in official


class TestExtractHomePlateUmpire:
    """Tests for _extract_home_plate_umpire helper."""

    def test_finds_hp_umpire(self) -> None:
        """Test finding home plate umpire."""
        officials = [
            {"official": {"id": 100, "fullName": "HP"}, "officialType": "Home Plate"},
            {"official": {"id": 101, "fullName": "1B"}, "officialType": "First Base"},
        ]

        result = _extract_home_plate_umpire(officials)

        assert result["id"] == 100
        assert result["fullName"] == "HP"

    def test_no_hp_umpire(self) -> None:
        """Test when no home plate umpire present."""
        officials = [
            {"official": {"id": 101, "fullName": "1B"}, "officialType": "First Base"},
        ]

        result = _extract_home_plate_umpire(officials)

        assert result == {}

    def test_empty_list(self) -> None:
        """Test with empty officials list."""
        result = _extract_home_plate_umpire([])

        assert result == {}


class TestExtractAttendance:
    """Tests for _extract_attendance helper."""

    def test_finds_attendance(self) -> None:
        """Test extracting attendance from boxscore info."""
        boxscore_info = [
            {"label": "Weather", "value": "Sunny"},
            {"label": "Att", "value": "52,523"},
            {"label": "First pitch", "value": "7:10 PM"},
        ]

        result = _extract_attendance(boxscore_info)

        assert result == 52523

    def test_no_attendance(self) -> None:
        """Test when attendance not present."""
        boxscore_info = [
            {"label": "Weather", "value": "Sunny"},
        ]

        result = _extract_attendance(boxscore_info)

        assert result is None

    def test_empty_info(self) -> None:
        """Test with empty info list."""
        result = _extract_attendance([])

        assert result is None

    def test_invalid_attendance_value(self) -> None:
        """Test with non-numeric attendance value."""
        boxscore_info = [
            {"label": "Att", "value": "N/A"},
        ]

        result = _extract_attendance(boxscore_info)

        assert result is None
