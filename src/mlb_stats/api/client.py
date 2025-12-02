"""HTTP client for MLB Stats API with retry and rate limiting."""

import logging
import time
from pathlib import Path
from typing import Any

import requests

from mlb_stats import __version__
from mlb_stats.api.cache import ResponseCache
from mlb_stats.api.endpoints import (
    BASE_URL,
    BOXSCORE,
    GAME_FEED,
    PLAY_BY_PLAY,
    PLAYER,
    PLAYERS_BATCH,
    SCHEDULE,
    TEAM,
    TEAMS,
)

logger = logging.getLogger(__name__)


class MLBStatsClient:
    """HTTP client for MLB Stats API with retry and rate limiting.

    Parameters
    ----------
    request_delay : float
        Minimum seconds to wait between requests. Default 0.5.
    max_retries : int
        Maximum retry attempts for failed requests. Default 3.
    timeout : float
        Request timeout in seconds. Default 30.
    cache_dir : str or Path, optional
        Directory for caching responses. If None, caching is disabled.
    use_cache : bool
        Whether to use caching. Default True.
    """

    def __init__(
        self,
        request_delay: float = 0.5,
        max_retries: int = 3,
        timeout: float = 30.0,
        cache_dir: str | Path | None = None,
        use_cache: bool = True,
    ) -> None:
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.use_cache = use_cache

        # Initialize cache if directory provided
        self.cache: ResponseCache | None = None
        if cache_dir and use_cache:
            self.cache = ResponseCache(cache_dir)

        # Set up session with headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": f"mlb-stats-collector/{__version__} (research project)",
                "Accept": "application/json",
            }
        )

        self._last_request_time: float = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug("Rate limiting: sleeping %.2fs", sleep_time)
            time.sleep(sleep_time)

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make GET request with retry logic.

        Parameters
        ----------
        endpoint : str
            API endpoint path (e.g., 'v1/schedule')
        params : dict, optional
            Query parameters

        Returns
        -------
        dict
            JSON response data

        Raises
        ------
        requests.HTTPError
            If request fails after all retries
        """
        url = f"{BASE_URL}{endpoint}"

        for attempt in range(self.max_retries):
            self._wait_for_rate_limit()

            try:
                logger.debug("GET %s params=%s (attempt %d)", url, params, attempt + 1)
                response = self.session.get(url, params=params, timeout=self.timeout)
                self._last_request_time = time.time()

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                wait_time = 2**attempt
                logger.warning(
                    "Request failed (attempt %d/%d): %s. Waiting %ds before retry.",
                    attempt + 1,
                    self.max_retries,
                    e,
                    wait_time,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)

        # Final attempt (after exhausting retries, try once more)
        self._wait_for_rate_limit()
        logger.debug("GET %s params=%s (final attempt)", url, params)
        response = self.session.get(url, params=params, timeout=self.timeout)
        self._last_request_time = time.time()
        response.raise_for_status()
        return response.json()

    def _is_game_final(self, data: dict[str, Any]) -> bool:
        """Check if game data indicates game is Final."""
        # Game feed structure
        if "gameData" in data:
            status = data.get("gameData", {}).get("status", {})
            return status.get("abstractGameState") == "Final"
        # Direct status object
        if "status" in data:
            return data.get("status", {}).get("abstractGameState") == "Final"
        return False

    def get_schedule(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        date: str | None = None,
        sport_id: int = 1,
    ) -> dict[str, Any]:
        """Fetch game schedule.

        Schedule data is never cached as it can change.

        Parameters
        ----------
        start_date : str, optional
            Start date (YYYY-MM-DD)
        end_date : str, optional
            End date (YYYY-MM-DD)
        date : str, optional
            Single date (YYYY-MM-DD), alternative to start/end
        sport_id : int
            Sport ID (1 = MLB)

        Returns
        -------
        dict
            Schedule data
        """
        params: dict[str, Any] = {"sportId": sport_id}
        if date:
            params["date"] = date
        else:
            if start_date:
                params["startDate"] = start_date
            if end_date:
                params["endDate"] = end_date

        return self.get(SCHEDULE, params=params)

    def get_game_feed(
        self,
        game_pk: int,
        use_cache: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch complete game feed including boxscore and plays.

        Parameters
        ----------
        game_pk : int
            Game primary key
        use_cache : bool, optional
            Override default cache behavior

        Returns
        -------
        dict
            Game feed data
        """
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        cache_key = str(game_pk)

        # Check cache first
        if should_use_cache and self.cache:
            cached = self.cache.get("game_feed", cache_key)
            if cached:
                logger.debug("Using cached game feed for %d", game_pk)
                return cached

        # Fetch from API
        endpoint = GAME_FEED.format(game_pk=game_pk)
        data = self.get(endpoint)

        # Cache only if game is Final
        if self.cache and self._is_game_final(data):
            self.cache.set("game_feed", cache_key, data)

        return data

    def get_boxscore(
        self,
        game_pk: int,
        use_cache: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch boxscore for a game.

        Parameters
        ----------
        game_pk : int
            Game primary key
        use_cache : bool, optional
            Override default cache behavior

        Returns
        -------
        dict
            Boxscore data
        """
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        cache_key = str(game_pk)

        # Check cache first
        if should_use_cache and self.cache:
            cached = self.cache.get("boxscore", cache_key)
            if cached:
                logger.debug("Using cached boxscore for %d", game_pk)
                return cached

        # Fetch from API
        endpoint = BOXSCORE.format(game_pk=game_pk)
        data = self.get(endpoint)

        # Cache only if game is Final
        if self.cache and self._is_game_final(data):
            self.cache.set("boxscore", cache_key, data)

        return data

    def get_play_by_play(
        self,
        game_pk: int,
        use_cache: bool | None = None,
    ) -> dict[str, Any]:
        """Fetch play-by-play data for a game.

        Parameters
        ----------
        game_pk : int
            Game primary key
        use_cache : bool, optional
            Override default cache behavior

        Returns
        -------
        dict
            Play-by-play data
        """
        should_use_cache = use_cache if use_cache is not None else self.use_cache
        cache_key = str(game_pk)

        # Check cache first
        if should_use_cache and self.cache:
            cached = self.cache.get("play_by_play", cache_key)
            if cached:
                logger.debug("Using cached play-by-play for %d", game_pk)
                return cached

        # Fetch from API
        endpoint = PLAY_BY_PLAY.format(game_pk=game_pk)
        data = self.get(endpoint)

        # We need to check game status separately since play-by-play
        # response may not include status. For now, always cache if present.
        # A more robust solution would check the game feed or boxscore.
        if self.cache and "allPlays" in data:
            # Assume if we have plays, the game might be complete
            # Better: check via separate call or pass status in
            self.cache.set("play_by_play", cache_key, data)

        return data

    def get_player(self, person_id: int) -> dict[str, Any]:
        """Fetch player data.

        Player data is NEVER cached to ensure freshness of mutable fields
        like currentTeam, lastPlayedDate, etc.

        Parameters
        ----------
        person_id : int
            Player ID

        Returns
        -------
        dict
            Player data
        """
        endpoint = PLAYER.format(person_id=person_id)
        return self.get(endpoint)

    def get_players(self, person_ids: list[int]) -> dict[str, Any]:
        """Fetch multiple players in a single request.

        Player data is NEVER cached.

        Parameters
        ----------
        person_ids : list of int
            List of player IDs

        Returns
        -------
        dict
            Players data
        """
        ids_str = ",".join(str(pid) for pid in person_ids)
        return self.get(PLAYERS_BATCH, params={"personIds": ids_str})

    def get_team(self, team_id: int) -> dict[str, Any]:
        """Fetch team data.

        Team data is NEVER cached to ensure freshness.

        Parameters
        ----------
        team_id : int
            Team ID

        Returns
        -------
        dict
            Team data
        """
        endpoint = TEAM.format(team_id=team_id)
        return self.get(endpoint)

    def get_teams(self, sport_id: int = 1) -> dict[str, Any]:
        """Fetch all teams for a sport.

        Team data is NEVER cached.

        Parameters
        ----------
        sport_id : int
            Sport ID (1 = MLB)

        Returns
        -------
        dict
            Teams data
        """
        return self.get(TEAMS, params={"sportId": sport_id})
