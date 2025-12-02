"""Tests for boxscore transformation functions."""

from pathlib import Path

from mlb_stats.models.boxscore import (
    extract_player_ids,
    transform_batting,
    transform_pitching,
)


class TestTransformBatting:
    """Tests for transform_batting function."""

    def test_extracts_batting_stats(self, sample_boxscore: dict) -> None:
        """Test extraction of batting stats from boxscore."""
        rows = transform_batting(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1  # Only one batter in sample
        row = rows[0]
        assert row["gamePk"] == 745927
        assert row["player_id"] == 660271
        assert row["team_id"] == 137  # Away team
        assert row["hits"] == 2
        assert row["homeRuns"] == 1
        assert row["rbi"] == 2
        assert row["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_parses_batting_order(self, sample_boxscore: dict) -> None:
        """Test that batting order string is parsed to int."""
        rows = transform_batting(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["battingOrder"] == 100  # Leadoff hitter

    def test_extracts_position(self, sample_boxscore: dict) -> None:
        """Test extraction of position data."""
        rows = transform_batting(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        row = rows[0]
        assert row["position_code"] == "10"
        assert row["position_name"] == "Designated Hitter"
        assert row["position_abbreviation"] == "DH"

    def test_extracts_calculated_stats(self, sample_boxscore: dict) -> None:
        """Test calculation of rate stats from counting stats."""
        rows = transform_batting(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        row = rows[0]
        # Calculated from fixture: 2 hits / 4 AB = 0.500, 5 TB / 4 AB = 1.250
        assert row["avg"] == "0.500"
        assert row["obp"] == "0.500"
        assert row["slg"] == "1.250"
        assert row["ops"] == "1.750"

    def test_empty_boxscore(self) -> None:
        """Test handling of empty boxscore."""
        boxscore = {"teams": {"away": {"players": {}}, "home": {"players": {}}}}
        rows = transform_batting(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert rows == []

    def test_skips_players_without_batting_stats(self) -> None:
        """Test that players without batting stats are skipped."""
        boxscore = {
            "teams": {
                "away": {
                    "team": {"id": 137},
                    "players": {
                        "ID123": {
                            "person": {"id": 123, "fullName": "No Stats Player"},
                            "stats": {},  # No batting key
                        }
                    },
                },
                "home": {"team": {"id": 119}, "players": {}},
            }
        }
        rows = transform_batting(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert rows == []

    def test_handles_missing_batting_order(self) -> None:
        """Test handling of missing batting order."""
        boxscore = {
            "teams": {
                "away": {
                    "team": {"id": 137},
                    "players": {
                        "ID123": {
                            "person": {"id": 123, "fullName": "Pinch Hitter"},
                            "stats": {"batting": {"hits": 1, "atBats": 2}},
                            # No battingOrder key
                        }
                    },
                },
                "home": {"team": {"id": 119}, "players": {}},
            }
        }
        rows = transform_batting(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["battingOrder"] is None


class TestTransformPitching:
    """Tests for transform_pitching function."""

    def test_extracts_pitching_stats(self, sample_boxscore: dict) -> None:
        """Test extraction of pitching stats from boxscore."""
        rows = transform_pitching(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1  # Only one pitcher in sample
        row = rows[0]
        assert row["gamePk"] == 745927
        assert row["player_id"] == 543243
        assert row["team_id"] == 119  # Home team
        assert row["strikeOuts"] == 8
        assert row["inningsPitched"] == "6.0"
        assert row["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_identifies_starting_pitcher(self, sample_boxscore: dict) -> None:
        """Test that starting pitcher is identified."""
        rows = transform_pitching(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["isStartingPitcher"] == 1

    def test_extracts_pitching_order(self, sample_boxscore: dict) -> None:
        """Test extraction of pitching order from team's pitchers list."""
        rows = transform_pitching(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        row = rows[0]
        assert row["pitchingOrder"] == 1  # First pitcher

    def test_extracts_note_field(self, sample_boxscore: dict) -> None:
        """Test extraction of W/L/S/H/BS note from game-level stats."""
        rows = transform_pitching(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        row = rows[0]
        assert row["note"] == "(W, 5-2)"

    def test_extracts_calculated_stats(self, sample_boxscore: dict) -> None:
        """Test extraction of calculated pitching stats."""
        rows = transform_pitching(sample_boxscore, 745927, "2024-07-01T00:00:00Z")

        row = rows[0]
        assert row["era"] == "3.00"
        assert row["whip"] == "1.17"

    def test_empty_boxscore(self) -> None:
        """Test handling of empty boxscore."""
        boxscore = {"teams": {"away": {"players": {}}, "home": {"players": {}}}}
        rows = transform_pitching(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert rows == []

    def test_skips_players_without_pitching_stats(self) -> None:
        """Test that players without pitching stats are skipped."""
        boxscore = {
            "teams": {
                "away": {"team": {"id": 137}, "players": {}},
                "home": {
                    "team": {"id": 119},
                    "players": {
                        "ID123": {
                            "person": {"id": 123, "fullName": "Position Player"},
                            "stats": {"batting": {"hits": 1}},  # Only batting
                        }
                    },
                },
            }
        }
        rows = transform_pitching(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert rows == []

    def test_handles_reliever_not_starter(self) -> None:
        """Test that relievers have isStartingPitcher=0."""
        boxscore = {
            "teams": {
                "away": {"team": {"id": 137}, "players": {}, "pitchers": []},
                "home": {
                    "team": {"id": 119},
                    "players": {
                        "ID456": {
                            "person": {"id": 456, "fullName": "Reliever"},
                            "stats": {"pitching": {"inningsPitched": "2.0"}},
                            "gameStatus": {"isStartingPitcher": False},
                        }
                    },
                    "pitchers": [456],
                },
            }
        }
        rows = transform_pitching(boxscore, 745927, "2024-07-01T00:00:00Z")

        assert len(rows) == 1
        assert rows[0]["isStartingPitcher"] == 0


class TestExtractPlayerIds:
    """Tests for extract_player_ids function."""

    def test_extracts_all_player_ids(self, sample_boxscore: dict) -> None:
        """Test extraction of all player IDs from boxscore."""
        player_ids = extract_player_ids(sample_boxscore)

        assert isinstance(player_ids, set)
        assert len(player_ids) == 2
        assert 660271 in player_ids
        assert 543243 in player_ids

    def test_returns_unique_ids(self) -> None:
        """Test that duplicate player IDs are deduplicated."""
        boxscore = {
            "teams": {
                "away": {
                    "players": {
                        "ID123": {"person": {"id": 123}},
                        "ID456": {"person": {"id": 456}},
                    }
                },
                "home": {
                    "players": {
                        "ID789": {"person": {"id": 789}},
                    }
                },
            }
        }
        player_ids = extract_player_ids(boxscore)

        assert len(player_ids) == 3

    def test_empty_boxscore(self) -> None:
        """Test with empty boxscore."""
        boxscore = {"teams": {"away": {"players": {}}, "home": {"players": {}}}}
        player_ids = extract_player_ids(boxscore)

        assert player_ids == set()

    def test_handles_missing_person_id(self) -> None:
        """Test handling of player data without person id."""
        boxscore = {
            "teams": {
                "away": {
                    "players": {
                        "ID123": {"person": {}},  # No id
                    }
                },
                "home": {"players": {}},
            }
        }
        player_ids = extract_player_ids(boxscore)

        assert player_ids == set()

    def test_with_live_fixture(self, fixtures_dir: Path) -> None:
        """Test extraction with real API response fixture."""
        import json

        fixture_path = fixtures_dir / "boxscore_745927.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            player_ids = extract_player_ids(data)
            # Real game should have multiple players
            assert len(player_ids) > 0
            for pid in player_ids:
                assert isinstance(pid, int)
