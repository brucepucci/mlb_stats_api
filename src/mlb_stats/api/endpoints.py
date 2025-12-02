"""MLB Stats API endpoint constants."""

# Base URL for the MLB Stats API
BASE_URL = "https://statsapi.mlb.com/api/"

# Endpoint paths
SCHEDULE = "v1/schedule"
GAME_FEED = "v1.1/game/{game_pk}/feed/live"
BOXSCORE = "v1/game/{game_pk}/boxscore"
PLAY_BY_PLAY = "v1/game/{game_pk}/playByPlay"
PLAYER = "v1/people/{person_id}"
PLAYERS_BATCH = "v1/people"
TEAM = "v1/teams/{team_id}"
TEAMS = "v1/teams"

# Cacheable endpoint types - only game data, never reference data
CACHEABLE_TYPES = frozenset({"game_feed", "boxscore", "play_by_play"})
