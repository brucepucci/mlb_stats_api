"""Tests for venue transformation functions."""

import json
from pathlib import Path

from mlb_stats.models.venue import transform_venue


class TestTransformVenue:
    """Tests for transform_venue function."""

    def test_complete_data(self) -> None:
        """Test transformation with complete venue data."""
        response = {
            "venues": [
                {
                    "id": 22,
                    "name": "Dodger Stadium",
                    "location": {
                        "city": "Los Angeles",
                        "state": "California",
                        "stateAbbrev": "CA",
                        "country": "USA",
                        "defaultCoordinates": {
                            "latitude": 34.073611,
                            "longitude": -118.24,
                        },
                        "elevation": 515,
                    },
                    "timeZone": {"id": "America/Los_Angeles"},
                }
            ]
        }

        result = transform_venue(response, "2024-07-01T00:00:00Z")

        assert result["id"] == 22
        assert result["name"] == "Dodger Stadium"
        assert result["city"] == "Los Angeles"
        assert result["state"] == "California"
        assert result["stateAbbrev"] == "CA"
        assert result["country"] == "USA"
        assert result["latitude"] == 34.073611
        assert result["longitude"] == -118.24
        assert result["elevation"] == 515
        assert result["timezone"] == "America/Los_Angeles"
        assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test transformation with real API response fixture."""
        fixture_path = fixtures_dir / "venue_22.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            result = transform_venue(data, "2024-07-01T00:00:00Z")

            assert result["id"] == 22
            assert result["name"] == "Dodger Stadium"
            assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_missing_location_data(self) -> None:
        """Test transformation with missing location data."""
        response = {
            "venues": [
                {
                    "id": 999,
                    "name": "Unknown Venue",
                }
            ]
        }

        result = transform_venue(response, "2024-07-01T00:00:00Z")

        assert result["id"] == 999
        assert result["name"] == "Unknown Venue"
        assert result["city"] is None
        assert result["latitude"] is None

    def test_empty_venues_array(self) -> None:
        """Test transformation with empty venues array."""
        result = transform_venue({"venues": []}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["name"] is None

    def test_no_venues_key(self) -> None:
        """Test transformation with missing venues key."""
        result = transform_venue({}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["name"] is None

    def test_missing_coordinates(self) -> None:
        """Test transformation with location but no coordinates."""
        response = {
            "venues": [
                {
                    "id": 999,
                    "name": "Venue Without Coords",
                    "location": {
                        "city": "Some City",
                        "state": "Some State",
                    },
                }
            ]
        }

        result = transform_venue(response, "2024-07-01T00:00:00Z")

        assert result["id"] == 999
        assert result["city"] == "Some City"
        assert result["latitude"] is None
        assert result["longitude"] is None
