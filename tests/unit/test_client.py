"""Tests for the MLBStatsClient class."""

from pathlib import Path

import pytest
import responses
from requests.exceptions import HTTPError

from mlb_stats.api.client import MLBStatsClient
from mlb_stats.api.endpoints import BASE_URL


class TestClientRetry:
    """Tests for client retry logic."""

    @responses.activate
    def test_retry_on_500(self, temp_cache_dir: Path) -> None:
        """Test that client retries on HTTP 500 errors."""
        # First two calls fail, third succeeds
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.0,
            max_retries=3,
            cache_dir=temp_cache_dir,
        )

        result = client.get_schedule(date="2024-07-01")
        assert result == {"dates": []}
        assert len(responses.calls) == 3

    @responses.activate
    def test_raises_after_max_retries(self, temp_cache_dir: Path) -> None:
        """Test that client raises after exhausting retries."""
        # All calls fail
        for _ in range(5):  # More than max_retries
            responses.add(
                responses.GET,
                f"{BASE_URL}v1/schedule",
                status=500,
            )

        client = MLBStatsClient(
            request_delay=0.0,
            max_retries=2,
            cache_dir=temp_cache_dir,
        )

        with pytest.raises(HTTPError):
            client.get_schedule(date="2024-07-01")


class TestClientRateLimit:
    """Tests for client rate limiting."""

    @responses.activate
    def test_rate_limit_delay(self, temp_cache_dir: Path) -> None:
        """Test that client respects rate limit delay."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.1,  # 100ms delay
            max_retries=1,
            cache_dir=temp_cache_dir,
        )

        import time

        start = time.time()
        client.get_schedule(date="2024-07-01")
        client.get_schedule(date="2024-07-02")
        elapsed = time.time() - start

        # Second request should have waited at least 100ms
        assert elapsed >= 0.1


class TestClientHeaders:
    """Tests for client headers."""

    @responses.activate
    def test_user_agent_header(self, temp_cache_dir: Path) -> None:
        """Test that User-Agent header is set."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.0,
            cache_dir=temp_cache_dir,
        )
        client.get_schedule(date="2024-07-01")

        assert len(responses.calls) == 1
        assert "mlb-stats-collector" in responses.calls[0].request.headers["User-Agent"]


class TestClientCaching:
    """Tests for client caching behavior."""

    @responses.activate
    def test_cache_checked_for_game_data(
        self, temp_cache_dir: Path, sample_game_feed: dict
    ) -> None:
        """Test that cache is checked before API call for game data."""
        # Prime the cache
        responses.add(
            responses.GET,
            f"{BASE_URL}v1.1/game/745927/feed/live",
            json=sample_game_feed,
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.0,
            cache_dir=temp_cache_dir,
        )

        # First call should hit API and cache
        result1 = client.get_game_feed(745927)
        assert len(responses.calls) == 1

        # Second call should use cache
        result2 = client.get_game_feed(745927)
        assert len(responses.calls) == 1  # No additional API call
        assert result1 == result2

    @responses.activate
    def test_cache_not_checked_for_reference_data(
        self, temp_cache_dir: Path, sample_player: dict
    ) -> None:
        """Test that reference data is NOT cached."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=sample_player,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/people/660271",
            json=sample_player,
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.0,
            cache_dir=temp_cache_dir,
        )

        # Both calls should hit API (no caching for players)
        client.get_player(660271)
        client.get_player(660271)
        assert len(responses.calls) == 2

    @responses.activate
    def test_schedule_not_cached(
        self, temp_cache_dir: Path, sample_schedule: dict
    ) -> None:
        """Test that schedule data is NOT cached."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json=sample_schedule,
            status=200,
        )

        client = MLBStatsClient(
            request_delay=0.0,
            cache_dir=temp_cache_dir,
        )

        # Both calls should hit API
        client.get_schedule(date="2024-07-01")
        client.get_schedule(date="2024-07-01")
        assert len(responses.calls) == 2


class TestClientMethods:
    """Tests for individual client methods."""

    @responses.activate
    def test_get_schedule_with_date(self, temp_cache_dir: Path) -> None:
        """Test get_schedule with single date."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        client = MLBStatsClient(request_delay=0.0, cache_dir=temp_cache_dir)
        client.get_schedule(date="2024-07-01")

        assert "date=2024-07-01" in responses.calls[0].request.url

    @responses.activate
    def test_get_schedule_with_date_range(self, temp_cache_dir: Path) -> None:
        """Test get_schedule with date range."""
        responses.add(
            responses.GET,
            f"{BASE_URL}v1/schedule",
            json={"dates": []},
            status=200,
        )

        client = MLBStatsClient(request_delay=0.0, cache_dir=temp_cache_dir)
        client.get_schedule(start_date="2024-07-01", end_date="2024-07-07")

        url = responses.calls[0].request.url
        assert "startDate=2024-07-01" in url
        assert "endDate=2024-07-07" in url
