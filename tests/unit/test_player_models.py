"""Tests for player transformation functions."""

from pathlib import Path

from mlb_stats.models.player import transform_player


class TestTransformPlayer:
    """Tests for transform_player function."""

    def test_basic_fields(self, sample_player: dict) -> None:
        """Test transformation extracts basic player fields."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["id"] == 660271
        assert result["fullName"] == "Shohei Ohtani"
        assert result["firstName"] == "Shohei"
        assert result["lastName"] == "Ohtani"
        assert result["primaryNumber"] == "17"
        assert result["birthDate"] == "1994-07-05"
        assert result["active"] == 1
        assert result["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_flattens_primary_position(self, sample_player: dict) -> None:
        """Test that primaryPosition nested object is flattened."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["primaryPosition_code"] == "Y"
        assert result["primaryPosition_name"] == "Two-Way Player"

    def test_flattens_bat_side(self, sample_player: dict) -> None:
        """Test that batSide nested object is flattened."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["batSide_code"] == "L"
        assert result["batSide_description"] == "Left"

    def test_flattens_pitch_hand(self, sample_player: dict) -> None:
        """Test that pitchHand nested object is flattened."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["pitchHand_code"] == "R"
        assert result["pitchHand_description"] == "Right"

    def test_flattens_current_team(self, sample_player: dict) -> None:
        """Test that currentTeam nested object is flattened."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["currentTeam_id"] == 119

    def test_active_boolean_to_int_true(self, sample_player: dict) -> None:
        """Test that active=True is converted to 1."""
        result = transform_player(sample_player, "2024-07-01T00:00:00Z")

        assert result["active"] == 1

    def test_active_boolean_to_int_false(self) -> None:
        """Test that active=False is converted to 0."""
        player_response = {
            "people": [
                {
                    "id": 123456,
                    "fullName": "Retired Player",
                    "active": False,
                }
            ]
        }

        result = transform_player(player_response, "2024-07-01T00:00:00Z")

        assert result["active"] == 0

    def test_missing_optional_fields(self) -> None:
        """Test handling of missing optional fields."""
        player_response = {
            "people": [
                {
                    "id": 123456,
                    "fullName": "Test Player",
                    "active": True,
                }
            ]
        }

        result = transform_player(player_response, "2024-07-01T00:00:00Z")

        assert result["id"] == 123456
        assert result["fullName"] == "Test Player"
        assert result["active"] == 1
        # Optional fields should be None
        assert result["firstName"] is None
        assert result["lastName"] is None
        assert result["primaryNumber"] is None
        assert result["birthDate"] is None
        assert result["height"] is None
        assert result["weight"] is None
        assert result["primaryPosition_code"] is None
        assert result["primaryPosition_name"] is None
        assert result["batSide_code"] is None
        assert result["pitchHand_code"] is None
        assert result["currentTeam_id"] is None

    def test_empty_response(self) -> None:
        """Test handling of empty response."""
        result = transform_player({"people": []}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["fullName"] is None
        assert result["active"] == 0

    def test_missing_people_key(self) -> None:
        """Test handling of response without people key."""
        result = transform_player({}, "2024-07-01T00:00:00Z")

        assert result["id"] is None
        assert result["fullName"] is None

    def test_fetched_at_preserved(self, sample_player: dict) -> None:
        """Test that _fetched_at timestamp is preserved."""
        fetched_at = "2024-12-01T15:30:00Z"
        result = transform_player(sample_player, fetched_at)

        assert result["_fetched_at"] == fetched_at

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test transformation with real API response fixture."""
        import json

        fixture_path = fixtures_dir / "player_660271.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            result = transform_player(data, "2024-07-01T00:00:00Z")
            # Verify real fixture has expected structure
            assert result["id"] is not None
            assert result["fullName"] is not None
