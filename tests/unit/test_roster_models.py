"""Tests for roster transformation functions."""

from mlb_stats.models.roster import extract_roster_player_ids, transform_roster


class TestTransformRoster:
    """Tests for transform_roster function."""

    def test_transforms_roster_entries(self, sample_roster: dict) -> None:
        """Test transformation of roster entries to database rows."""
        rows = transform_roster(sample_roster, 745927, 119, "2024-07-01T00:00:00Z")

        assert len(rows) == 3

        # Check first player (Shohei Ohtani)
        ohtani = next(r for r in rows if r["player_id"] == 660271)
        assert ohtani["gamePk"] == 745927
        assert ohtani["team_id"] == 119
        assert ohtani["jerseyNumber"] == "17"
        assert ohtani["position_code"] == "Y"
        assert ohtani["position_name"] == "Two-Way Player"
        assert ohtani["position_type"] == "Two-Way Player"
        assert ohtani["position_abbreviation"] == "TWP"
        assert ohtani["status_code"] == "A"
        assert ohtani["status_description"] == "Active"
        assert ohtani["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_transforms_pitcher(self, sample_roster: dict) -> None:
        """Test transformation of pitcher roster entry."""
        rows = transform_roster(sample_roster, 745927, 119, "2024-07-01T00:00:00Z")

        pitcher = next(r for r in rows if r["player_id"] == 543243)
        assert pitcher["position_code"] == "1"
        assert pitcher["position_name"] == "Pitcher"
        assert pitcher["position_abbreviation"] == "P"

    def test_transforms_infielder(self, sample_roster: dict) -> None:
        """Test transformation of infielder roster entry."""
        rows = transform_roster(sample_roster, 745927, 119, "2024-07-01T00:00:00Z")

        betts = next(r for r in rows if r["player_id"] == 592450)
        assert betts["position_code"] == "6"
        assert betts["position_name"] == "Shortstop"
        assert betts["position_type"] == "Infielder"
        assert betts["position_abbreviation"] == "SS"

    def test_empty_roster(self) -> None:
        """Test transformation with empty roster."""
        rows = transform_roster({"roster": []}, 745927, 119, "2024-07-01T00:00:00Z")
        assert rows == []

    def test_missing_roster_key(self) -> None:
        """Test transformation with missing roster key."""
        rows = transform_roster({}, 745927, 119, "2024-07-01T00:00:00Z")
        assert rows == []

    def test_skips_entries_without_player_id(self) -> None:
        """Test that entries without player ID are skipped."""
        roster_data = {
            "roster": [
                {
                    "person": {},  # No id
                    "jerseyNumber": "99",
                    "position": {"code": "1"},
                },
                {
                    "person": {"id": 123456},
                    "jerseyNumber": "42",
                    "position": {"code": "2"},
                },
            ]
        }
        rows = transform_roster(roster_data, 745927, 119, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["player_id"] == 123456

    def test_handles_missing_optional_fields(self) -> None:
        """Test transformation with minimal data."""
        roster_data = {
            "roster": [
                {
                    "person": {"id": 123456},
                }
            ]
        }
        rows = transform_roster(roster_data, 745927, 119, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["player_id"] == 123456
        assert rows[0]["gamePk"] == 745927
        assert rows[0]["team_id"] == 119
        assert rows[0]["jerseyNumber"] is None
        assert rows[0]["position_code"] is None
        assert rows[0]["status_code"] is None

    def test_preserves_game_and_team_ids(self) -> None:
        """Test that game_pk and team_id are correctly assigned."""
        roster_data = {"roster": [{"person": {"id": 111}}, {"person": {"id": 222}}]}
        rows = transform_roster(roster_data, 999999, 888, "2024-07-01T00:00:00Z")

        for row in rows:
            assert row["gamePk"] == 999999
            assert row["team_id"] == 888


class TestExtractRosterPlayerIds:
    """Tests for extract_roster_player_ids function."""

    def test_extracts_all_player_ids(self, sample_roster: dict) -> None:
        """Test extraction of player IDs from roster."""
        ids = extract_roster_player_ids(sample_roster)

        assert ids == {660271, 543243, 592450}

    def test_returns_set(self, sample_roster: dict) -> None:
        """Test that result is a set."""
        ids = extract_roster_player_ids(sample_roster)
        assert isinstance(ids, set)

    def test_empty_roster(self) -> None:
        """Test extraction from empty roster."""
        ids = extract_roster_player_ids({"roster": []})
        assert ids == set()

    def test_missing_roster_key(self) -> None:
        """Test extraction with missing roster key."""
        ids = extract_roster_player_ids({})
        assert ids == set()

    def test_skips_entries_without_id(self) -> None:
        """Test that entries without player ID are skipped."""
        roster_data = {
            "roster": [
                {"person": {}},  # No id
                {"person": {"id": 123}},
                {"person": {"id": 456}},
            ]
        }
        ids = extract_roster_player_ids(roster_data)
        assert ids == {123, 456}

    def test_handles_duplicate_ids(self) -> None:
        """Test that duplicate IDs are deduplicated."""
        roster_data = {
            "roster": [
                {"person": {"id": 123}},
                {"person": {"id": 123}},  # Duplicate
                {"person": {"id": 456}},
            ]
        }
        ids = extract_roster_player_ids(roster_data)
        assert ids == {123, 456}
