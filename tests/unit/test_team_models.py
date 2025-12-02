"""Tests for team transformation functions."""

import json
from pathlib import Path

from mlb_stats.models.team import transform_team


class TestTransformTeam:
    """Tests for transform_team function."""

    def test_complete_data(self, sample_team: dict) -> None:
        """Test transformation with complete team data."""
        result = transform_team(sample_team, "2024-07-01T00:00:00Z")

        assert result["id"] == 119
        assert result["name"] == "Los Angeles Dodgers"
        assert result["abbreviation"] == "LAD"
        assert result["teamName"] == "Dodgers"
        assert result["locationName"] == "Los Angeles"
        assert result["league_id"] == 104
        assert result["league_name"] == "National League"
        assert result["division_id"] == 203
        assert result["division_name"] == "National League West"
        assert result["active"] == 1
        assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test transformation with real API response fixture."""
        fixture_path = fixtures_dir / "team_119.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            result = transform_team(data, "2024-07-01T00:00:00Z")

            assert result["id"] == 119
            assert result["name"] == "Los Angeles Dodgers"
            assert result["abbreviation"] == "LAD"
            assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_missing_optional_fields(self) -> None:
        """Test transformation with missing optional fields."""
        minimal_response = {
            "teams": [
                {
                    "id": 999,
                    "name": "Test Team",
                    "active": False,
                }
            ]
        }

        result = transform_team(minimal_response, "2024-07-01T00:00:00Z")

        assert result["id"] == 999
        assert result["name"] == "Test Team"
        assert result["active"] == 0
        assert result["league_id"] is None

    def test_empty_response(self) -> None:
        """Test transformation with empty teams array."""
        result = transform_team({"teams": []}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["name"] is None

    def test_no_teams_key(self) -> None:
        """Test transformation with missing teams key."""
        result = transform_team({}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["name"] is None
