"""Tests for CLI option validation."""

import pytest
from click.testing import CliRunner

from mlb_stats.cli import cli


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestSeasonRangeValidation:
    """Test validation for --start-season and --end-season options."""

    def test_start_season_only(self, runner):
        """Test --start-season alone defaults end to current year."""
        result = runner.invoke(cli, ["sync", "--start-season", "2018", "--help"])
        # Help should work without validation errors
        assert result.exit_code == 0

    def test_end_season_only(self, runner):
        """Test --end-season alone defaults start to 2008."""
        result = runner.invoke(cli, ["sync", "--end-season", "2020", "--help"])
        assert result.exit_code == 0

    def test_both_season_bounds(self, runner):
        """Test --start-season and --end-season together."""
        result = runner.invoke(
            cli, ["sync", "--start-season", "2010", "--end-season", "2015", "--help"]
        )
        assert result.exit_code == 0

    def test_start_after_end_error(self, runner):
        """Test error when start season is after end season."""
        result = runner.invoke(
            cli, ["sync", "--start-season", "2020", "--end-season", "2018"]
        )
        assert result.exit_code != 0
        assert "cannot be after" in result.output.lower()

    def test_start_before_2008_error(self, runner):
        """Test error when start season is before 2008."""
        result = runner.invoke(cli, ["sync", "--start-season", "2005"])
        assert result.exit_code != 0
        assert "2008" in result.output
        assert "PITCHf/x" in result.output

    def test_season_range_with_date_range_error(self, runner):
        """Test error when mixing season range with date range."""
        result = runner.invoke(
            cli,
            [
                "sync",
                "--start-season",
                "2010",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ],
        )
        assert result.exit_code != 0
        assert "cannot use" in result.output.lower()

    def test_season_range_with_season_error(self, runner):
        """Test error when mixing season range with --season."""
        result = runner.invoke(
            cli, ["sync", "--start-season", "2010", "--season", "2024"]
        )
        assert result.exit_code != 0
        assert "cannot use" in result.output.lower()


class TestAllFlagValidation:
    """Test validation for --all flag."""

    def test_all_with_start_season_error(self, runner):
        """Test error when --all is used with --start-season."""
        result = runner.invoke(cli, ["sync", "--all", "--start-season", "2010"])
        assert result.exit_code != 0
        assert "cannot use --all" in result.output.lower()

    def test_all_with_end_season_error(self, runner):
        """Test error when --all is used with --end-season."""
        result = runner.invoke(cli, ["sync", "--all", "--end-season", "2020"])
        assert result.exit_code != 0
        assert "cannot use --all" in result.output.lower()

    def test_all_with_season_error(self, runner):
        """Test error when --all is used with --season."""
        result = runner.invoke(cli, ["sync", "--all", "--season", "2024"])
        assert result.exit_code != 0
        assert "cannot use --all" in result.output.lower()

    def test_all_with_date_range_error(self, runner):
        """Test error when --all is used with date range."""
        result = runner.invoke(
            cli,
            [
                "sync",
                "--all",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
            ],
        )
        assert result.exit_code != 0
        assert "cannot use --all" in result.output.lower()


class TestGamePkValidation:
    """Test validation for gamePk argument."""

    def test_game_pk_with_season_range_error(self, runner):
        """Test error when gamePk is used with season range."""
        result = runner.invoke(
            cli, ["sync", "745927", "--start-season", "2010", "--end-season", "2015"]
        )
        assert result.exit_code != 0
        assert "cannot use gamepk" in result.output.lower()

    def test_game_pk_with_all_error(self, runner):
        """Test error when gamePk is used with --all."""
        result = runner.invoke(cli, ["sync", "745927", "--all"])
        assert result.exit_code != 0
        assert "cannot use gamepk" in result.output.lower()
