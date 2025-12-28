"""Tests for venue transformation functions."""

import json
from pathlib import Path

from mlb_stats.models.venue import transform_venue

# Test year for venue composite PK
TEST_YEAR = 2024


class TestTransformVenue:
    """Tests for transform_venue function."""

    def test_complete_data(self, sample_venue: dict) -> None:
        """Test transformation with complete venue data."""
        result = transform_venue(sample_venue, "2024-07-01T00:00:00Z", TEST_YEAR)

        assert result["id"] == 22
        assert result["year"] == TEST_YEAR
        assert result["name"] == "Dodger Stadium"
        assert result["active"] == 1
        # Location
        assert result["address1"] == "1000 Vin Scully Avenue"
        assert result["city"] == "Los Angeles"
        assert result["state"] == "California"
        assert result["stateAbbrev"] == "CA"
        assert result["postalCode"] == "90012-1199"
        assert result["country"] == "USA"
        assert result["phone"] == "(323) 224-1500"
        assert result["latitude"] == 34.07368
        assert result["longitude"] == -118.24053
        assert result["azimuthAngle"] == 26.0
        assert result["elevation"] == 515
        # Time zone
        assert result["timeZone_id"] == "America/Los_Angeles"
        assert result["timeZone_offset"] == -8
        assert result["timeZone_tz"] == "PST"
        # Field info
        assert result["capacity"] == 56000
        assert result["turfType"] == "Grass"
        assert result["roofType"] == "Open"
        # Dimensions
        assert result["leftLine"] == 330
        assert result["leftCenter"] == 385
        assert result["center"] == 395
        assert result["rightCenter"] == 385
        assert result["rightLine"] == 330
        # Metadata
        assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test transformation with real API response fixture."""
        fixture_path = fixtures_dir / "venue_22.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            result = transform_venue(data, "2024-07-01T00:00:00Z", TEST_YEAR)

            assert result["id"] == 22
            assert result["year"] == TEST_YEAR
            assert result["name"] == "Dodger Stadium"
            assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_missing_optional_fields(self) -> None:
        """Test transformation with missing optional fields."""
        minimal_response = {
            "venues": [
                {
                    "id": 999,
                    "name": "Test Stadium",
                    "active": False,
                }
            ]
        }

        result = transform_venue(minimal_response, "2024-07-01T00:00:00Z", TEST_YEAR)

        assert result["id"] == 999
        assert result["year"] == TEST_YEAR
        assert result["name"] == "Test Stadium"
        assert result["active"] == 0
        assert result["city"] is None
        assert result["capacity"] is None
        assert result["latitude"] is None

    def test_empty_response(self) -> None:
        """Test transformation with empty venues array."""
        result = transform_venue({"venues": []}, "2024-07-01T00:00:00Z", TEST_YEAR)

        assert result["id"] is None
        assert result["year"] == TEST_YEAR
        assert result["name"] is None

    def test_no_venues_key(self) -> None:
        """Test transformation with missing venues key."""
        result = transform_venue({}, "2024-07-01T00:00:00Z", TEST_YEAR)

        assert result["id"] is None
        assert result["year"] == TEST_YEAR
        assert result["name"] is None
