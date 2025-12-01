"""Tests for date utility functions."""

from datetime import date

import pytest

from mlb_stats.utils.dates import date_range, format_date, parse_date, season_dates


class TestParseDate:
    """Tests for parse_date function."""

    def test_valid_date(self) -> None:
        """Test parsing valid date string."""
        result = parse_date("2024-07-01")
        assert result == date(2024, 7, 1)

    def test_leap_year(self) -> None:
        """Test parsing leap year date."""
        result = parse_date("2024-02-29")
        assert result == date(2024, 2, 29)

    def test_invalid_format(self) -> None:
        """Test parsing invalid date format raises ValueError."""
        with pytest.raises(ValueError):
            parse_date("07/01/2024")

    def test_invalid_date(self) -> None:
        """Test parsing invalid date raises ValueError."""
        with pytest.raises(ValueError):
            parse_date("2024-13-01")

    def test_non_leap_year_feb_29(self) -> None:
        """Test parsing Feb 29 on non-leap year raises ValueError."""
        with pytest.raises(ValueError):
            parse_date("2023-02-29")


class TestFormatDate:
    """Tests for format_date function."""

    def test_format(self) -> None:
        """Test formatting date to string."""
        result = format_date(date(2024, 7, 1))
        assert result == "2024-07-01"

    def test_format_single_digit_month(self) -> None:
        """Test formatting with single digit month pads with zero."""
        result = format_date(date(2024, 1, 5))
        assert result == "2024-01-05"


class TestDateRange:
    """Tests for date_range function."""

    def test_single_day(self) -> None:
        """Test range with same start and end."""
        result = date_range(date(2024, 7, 1), date(2024, 7, 1))
        assert result == [date(2024, 7, 1)]

    def test_week(self) -> None:
        """Test week-long range."""
        result = date_range(date(2024, 7, 1), date(2024, 7, 7))
        assert len(result) == 7
        assert result[0] == date(2024, 7, 1)
        assert result[-1] == date(2024, 7, 7)

    def test_cross_month(self) -> None:
        """Test range crossing month boundary."""
        result = date_range(date(2024, 6, 29), date(2024, 7, 2))
        assert len(result) == 4
        assert result[0] == date(2024, 6, 29)
        assert result[-1] == date(2024, 7, 2)

    def test_empty_when_end_before_start(self) -> None:
        """Test empty range when end date is before start date."""
        result = date_range(date(2024, 7, 7), date(2024, 7, 1))
        assert result == []


class TestSeasonDates:
    """Tests for season_dates function."""

    def test_returns_tuple(self) -> None:
        """Test that season_dates returns a tuple of strings."""
        start, end = season_dates(2024)
        assert start == "2024-02-15"
        assert end == "2024-11-15"

    def test_different_year(self) -> None:
        """Test season dates for a different year."""
        start, end = season_dates(2023)
        assert start == "2023-02-15"
        assert end == "2023-11-15"
