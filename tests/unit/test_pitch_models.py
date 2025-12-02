"""Tests for pitch transformation functions."""

from mlb_stats.models.pitch import (
    extract_batted_ball_event,
    extract_pitches_from_play,
    transform_at_bat,
    transform_batted_ball,
    transform_pitch,
)


class TestTransformAtBat:
    """Tests for transform_at_bat function."""

    def test_extracts_at_bat_data(self, sample_play: dict) -> None:
        """Test extraction of at-bat data from play."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 0
        assert row["inning"] == 1
        assert row["halfInning"] == "top"
        assert row["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_extracts_matchup(self, sample_play: dict) -> None:
        """Test extraction of matchup data."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["batter_id"] == 660271
        assert row["pitcher_id"] == 543243
        assert row["batSide_code"] == "L"
        assert row["pitchHand_code"] == "R"

    def test_extracts_result(self, sample_play: dict) -> None:
        """Test extraction of result data."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["event"] == "Strikeout"
        assert row["eventType"] == "strikeout"
        assert row["rbi"] == 0
        assert row["awayScore"] == 0
        assert row["homeScore"] == 0

    def test_extracts_count(self, sample_play: dict) -> None:
        """Test extraction of count at end of at-bat."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["balls"] == 1
        assert row["strikes"] == 3
        assert row["outs"] == 1

    def test_counts_pitches(self, sample_play: dict) -> None:
        """Test that pitch count is calculated correctly."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["pitchCount"] == 4  # 4 pitches in sample_play

    def test_converts_booleans_to_int(self, sample_play: dict) -> None:
        """Test that boolean fields are converted to int."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["isComplete"] == 1
        assert row["isScoringPlay"] == 0
        assert row["hasReview"] == 0
        assert row["hasOut"] == 1

    def test_extracts_timing(self, sample_play: dict) -> None:
        """Test extraction of timing data."""
        row = transform_at_bat(sample_play, 745927, "2024-07-01T00:00:00Z")

        assert row["startTime"] == "2024-07-02T02:15:00Z"
        assert row["endTime"] == "2024-07-02T02:18:00Z"

    def test_handles_empty_play(self) -> None:
        """Test handling of empty play data."""
        play = {}
        row = transform_at_bat(play, 745927, "2024-07-01T00:00:00Z")

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] is None
        assert row["pitchCount"] == 0


class TestTransformPitch:
    """Tests for transform_pitch function."""

    def test_extracts_pitch_data(self, sample_play: dict) -> None:
        """Test extraction of pitch data from event."""
        event = sample_play["playEvents"][0]  # First pitch
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 0
        assert row["pitchNumber"] == 1
        assert row["inning"] == 1
        assert row["halfInning"] == "top"

    def test_extracts_matchup(self, sample_play: dict) -> None:
        """Test extraction of matchup data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["batter_id"] == 660271
        assert row["pitcher_id"] == 543243
        assert row["batSide_code"] == "L"
        assert row["pitchHand_code"] == "R"

    def test_extracts_count(self, sample_play: dict) -> None:
        """Test extraction of count before pitch."""
        event = sample_play["playEvents"][1]  # Second pitch
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["balls"] == 1
        assert row["strikes"] == 1
        assert row["outs"] == 0

    def test_extracts_call(self, sample_play: dict) -> None:
        """Test extraction of pitch call."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["call_code"] == "B"
        assert row["call_description"] == "Ball"
        assert row["isInPlay"] == 0
        assert row["isStrike"] == 0
        assert row["isBall"] == 1

    def test_extracts_pitch_type(self, sample_play: dict) -> None:
        """Test extraction of pitch type."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["type_code"] == "FF"
        assert row["type_description"] == "Four-Seam Fastball"
        assert row["typeConfidence"] == 0.9

    def test_extracts_velocity(self, sample_play: dict) -> None:
        """Test extraction of velocity data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["startSpeed"] == 95.2
        assert row["endSpeed"] == 87.1

    def test_extracts_strike_zone(self, sample_play: dict) -> None:
        """Test extraction of strike zone data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["zone"] == 14
        assert row["strikeZoneTop"] == 3.49
        assert row["strikeZoneBottom"] == 1.6

    def test_extracts_plate_location(self, sample_play: dict) -> None:
        """Test extraction of plate location (pX/pZ mapped to plateX/plateZ)."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["plateX"] == -1.45
        assert row["plateZ"] == 3.31

    def test_extracts_coordinates(self, sample_play: dict) -> None:
        """Test extraction of legacy coordinates."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["coordinates_x"] == 120.5
        assert row["coordinates_y"] == 180.3

    def test_extracts_release_point(self, sample_play: dict) -> None:
        """Test extraction of release point data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["x0"] == -1.72
        assert row["y0"] == 50.0
        assert row["z0"] == 5.64

    def test_extracts_velocity_components(self, sample_play: dict) -> None:
        """Test extraction of velocity component data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["vX0"] == 8.21
        assert row["vY0"] == -128.65
        assert row["vZ0"] == -6.34

    def test_extracts_acceleration(self, sample_play: dict) -> None:
        """Test extraction of acceleration data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["aX"] == 0.24
        assert row["aY"] == 27.1
        assert row["aZ"] == -31.21

    def test_extracts_movement(self, sample_play: dict) -> None:
        """Test extraction of movement data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["pfxX"] == -6.15
        assert row["pfxZ"] == 7.57

    def test_extracts_break_metrics(self, sample_play: dict) -> None:
        """Test extraction of break metrics."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["breakAngle"] == 3.6
        assert row["breakLength"] == 8.4
        assert row["breakY"] == 24.0

    def test_extracts_spin_metrics(self, sample_play: dict) -> None:
        """Test extraction of spin metrics."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["spinRate"] == 2423
        assert row["spinDirection"] == 184

    def test_extracts_timing_extension(self, sample_play: dict) -> None:
        """Test extraction of timing and extension data."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["plateTime"] == 0.43
        assert row["extension"] == 6.22

    def test_extracts_timestamps(self, sample_play: dict) -> None:
        """Test extraction of timestamps."""
        event = sample_play["playEvents"][0]
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["startTime"] == "2024-07-02T02:15:00Z"
        assert row["endTime"] == "2024-07-02T02:15:05Z"
        assert row["playId"] == "pitch-1"

    def test_handles_missing_statcast_data(self, sample_play: dict) -> None:
        """Test handling of pitch with missing Statcast data (pre-2015)."""
        event = sample_play["playEvents"][3]  # Fourth pitch - minimal data
        row = transform_pitch(sample_play, event, 745927, "2024-07-01T00:00:00Z")

        # Core data should be present
        assert row["pitchNumber"] == 4
        assert row["startSpeed"] == 85.0

        # Statcast fields should be None
        assert row["spinRate"] is None
        assert row["spinDirection"] is None
        assert row["breakAngle"] is None
        assert row["extension"] is None
        assert row["plateX"] is None


class TestTransformBattedBall:
    """Tests for transform_batted_ball function."""

    def test_extracts_batted_ball_data(self, sample_play_with_hit: dict) -> None:
        """Test extraction of batted ball data."""
        event = sample_play_with_hit["playEvents"][-1]  # Last pitch (in play)
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["gamePk"] == 745927
        assert row["atBatIndex"] == 5
        assert row["pitchNumber"] == 4
        assert row["_fetched_at"] == "2024-07-01T00:00:00Z"

    def test_extracts_matchup(self, sample_play_with_hit: dict) -> None:
        """Test extraction of matchup data."""
        event = sample_play_with_hit["playEvents"][-1]
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["batter_id"] == 660271
        assert row["pitcher_id"] == 543243
        assert row["inning"] == 2
        assert row["halfInning"] == "top"

    def test_extracts_statcast_metrics(self, sample_play_with_hit: dict) -> None:
        """Test extraction of Statcast batted ball metrics."""
        event = sample_play_with_hit["playEvents"][-1]
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["launchSpeed"] == 101.9
        assert row["launchAngle"] == 12
        assert row["totalDistance"] == 285

    def test_extracts_classification(self, sample_play_with_hit: dict) -> None:
        """Test extraction of batted ball classification."""
        event = sample_play_with_hit["playEvents"][-1]
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["trajectory"] == "line_drive"
        assert row["hardness"] == "hard"

    def test_extracts_location(self, sample_play_with_hit: dict) -> None:
        """Test extraction of field location data."""
        event = sample_play_with_hit["playEvents"][-1]
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["location"] == "7"  # Left field
        assert row["coordinates_x"] == 85.4
        assert row["coordinates_y"] == 125.2

    def test_extracts_play_result(self, sample_play_with_hit: dict) -> None:
        """Test extraction of play result from parent play."""
        event = sample_play_with_hit["playEvents"][-1]
        row = transform_batted_ball(
            sample_play_with_hit, event, 745927, "2024-07-01T00:00:00Z"
        )

        assert row["event"] == "Single"
        assert row["eventType"] == "single"
        assert row["rbi"] == 1
        assert row["awayScore"] == 1
        assert row["homeScore"] == 0

    def test_extracts_enhanced_statcast_fields(self) -> None:
        """Test extraction of enhanced Statcast fields (2024+)."""
        play = {
            "about": {"atBatIndex": 5, "inning": 3, "halfInning": "bottom"},
            "result": {
                "event": "Home Run",
                "eventType": "home_run",
                "description": "Shohei Ohtani homers (25)",
                "rbi": 2,
                "awayScore": 0,
                "homeScore": 3,
            },
            "matchup": {
                "batter": {"id": 660271},
                "pitcher": {"id": 543243},
            },
            "playEvents": [
                {
                    "pitchNumber": 4,
                    "playId": "test-play-id",
                    "hitData": {
                        "launchSpeed": 112.5,
                        "launchAngle": 28,
                        "totalDistance": 420,
                        "trajectory": "fly_ball",
                        "hardness": "hard",
                        "location": "8",
                        "coordinates": {"coordX": 125.0, "coordY": 50.0},
                        "hitProbability": 0.95,
                        "isBarrel": True,
                        "batSpeed": 78.3,
                        "isSwordSwing": False,
                    },
                }
            ],
        }
        event = play["playEvents"][0]
        row = transform_batted_ball(play, event, 745927, "2024-07-01T00:00:00Z")

        # Enhanced Statcast fields
        assert row["hitProbability"] == 0.95
        assert row["isBarrel"] == 1
        assert row["batSpeed"] == 78.3
        assert row["isSwordSwing"] == 0

    def test_handles_missing_enhanced_statcast_fields(self) -> None:
        """Test that missing enhanced Statcast fields return None."""
        play = {
            "about": {"atBatIndex": 5, "inning": 3, "halfInning": "bottom"},
            "result": {"event": "Single", "eventType": "single"},
            "matchup": {
                "batter": {"id": 660271},
                "pitcher": {"id": 543243},
            },
            "playEvents": [
                {
                    "pitchNumber": 2,
                    "hitData": {
                        "launchSpeed": 95.0,
                        "launchAngle": 10,
                        # No enhanced Statcast fields (pre-2024 game)
                    },
                }
            ],
        }
        event = play["playEvents"][0]
        row = transform_batted_ball(play, event, 745927, "2024-07-01T00:00:00Z")

        assert row["hitProbability"] is None
        assert row["isBarrel"] is None
        assert row["batSpeed"] is None
        assert row["isSwordSwing"] is None


class TestExtractPitchesFromPlay:
    """Tests for extract_pitches_from_play function."""

    def test_extracts_all_pitches(self, sample_play: dict) -> None:
        """Test extraction of all pitches from play."""
        pitches = extract_pitches_from_play(sample_play)

        assert len(pitches) == 4
        assert all(p.get("isPitch") for p in pitches)

    def test_excludes_non_pitch_events(self) -> None:
        """Test that non-pitch events are excluded."""
        play = {
            "playEvents": [
                {"isPitch": True, "pitchNumber": 1},
                {"isPitch": False, "type": "action"},  # Pickoff
                {"isPitch": True, "pitchNumber": 2},
            ]
        }
        pitches = extract_pitches_from_play(play)

        assert len(pitches) == 2
        assert pitches[0]["pitchNumber"] == 1
        assert pitches[1]["pitchNumber"] == 2

    def test_handles_empty_play_events(self) -> None:
        """Test handling of play with no events."""
        play = {"playEvents": []}
        pitches = extract_pitches_from_play(play)

        assert pitches == []

    def test_handles_missing_play_events(self) -> None:
        """Test handling of play without playEvents key."""
        play = {}
        pitches = extract_pitches_from_play(play)

        assert pitches == []


class TestExtractBattedBallEvent:
    """Tests for extract_batted_ball_event function."""

    def test_finds_batted_ball_event(self, sample_play_with_hit: dict) -> None:
        """Test finding batted ball event in play."""
        event = extract_batted_ball_event(sample_play_with_hit)

        assert event is not None
        assert event["pitchNumber"] == 4
        assert event["hitData"]["launchSpeed"] == 101.9

    def test_returns_none_for_strikeout(self, sample_play: dict) -> None:
        """Test that strikeout play has no batted ball event."""
        event = extract_batted_ball_event(sample_play)

        assert event is None

    def test_handles_empty_play(self) -> None:
        """Test handling of empty play."""
        play = {}
        event = extract_batted_ball_event(play)

        assert event is None

    def test_returns_last_in_play_event(self) -> None:
        """Test that the last in-play event is returned."""
        play = {
            "playEvents": [
                {
                    "details": {"isInPlay": True},
                    "hitData": {"launchSpeed": 90.0},
                    "pitchNumber": 1,
                },
                {
                    "details": {"isInPlay": True},
                    "hitData": {"launchSpeed": 100.0},
                    "pitchNumber": 2,
                },
            ]
        }
        event = extract_batted_ball_event(play)

        assert event is not None
        assert event["pitchNumber"] == 2
        assert event["hitData"]["launchSpeed"] == 100.0

    def test_requires_hit_data(self) -> None:
        """Test that isInPlay without hitData returns None."""
        play = {
            "playEvents": [
                {
                    "details": {"isInPlay": True},
                    # No hitData key
                    "pitchNumber": 1,
                },
            ]
        }
        event = extract_batted_ball_event(play)

        assert event is None
