# MLB Stats Collector

A Python CLI application that collects MLB game data from the MLB Stats API and stores it in SQLite. The tool fetches game schedules, box scores, pitch-by-pitch data with Statcast metrics, and reference data (teams, venues, players).

## Features

- Fetch game schedules by date range or season
- Collect box score data (batting and pitching stats)
- Collect pitch-level data with Statcast metrics
- Store data in SQLite for easy querying
- Intelligent caching of immutable game data
- Rate limiting to be a good API citizen

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone https://github.com/yourusername/mlb-stats.git
cd mlb-stats

# Install dependencies
uv sync

# Initialize the database
uv run mlb-stats init-db
```

## CLI Usage

All commands should be run with `uv run` prefix.

### Basic Commands

```bash
# Show version
uv run mlb-stats --version

# Show help
uv run mlb-stats --help

# Initialize the database (creates all tables)
uv run mlb-stats init-db
```

### Syncing Games

Fetch game data from the MLB Stats API and store in the database.

```bash
# Sync games for a specific date range
uv run mlb-stats sync games --start-date 2024-07-01 --end-date 2024-07-07

# Sync all games for a season
uv run mlb-stats sync games --season 2024
```

### Syncing Box Scores

Fetch box score data (batting and pitching stats) for games. This also syncs player data.

```bash
# Sync boxscore for a specific game
uv run mlb-stats sync boxscores 745927

# Sync boxscores for a date range
uv run mlb-stats sync boxscores --start-date 2024-07-01 --end-date 2024-07-07

# Sync boxscores for a season
uv run mlb-stats sync boxscores --season 2024
```

**Note:** The `sync boxscores` command will automatically sync the game record and all players that appear in the boxscore. Games don't need to be synced separately first.

### Global Options

These options can be used with any command:

```bash
# Increase verbosity (-v for INFO, -vv for DEBUG)
uv run mlb-stats -v sync games --start-date 2024-07-01 --end-date 2024-07-01
uv run mlb-stats -vv sync games --start-date 2024-07-01 --end-date 2024-07-01

# Suppress output (ERROR level only)
uv run mlb-stats --quiet sync games --season 2024

# Use a custom database path (default: data/mlb_stats.db)
uv run mlb-stats --db-path /path/to/custom.db sync games --season 2024

# Use a custom cache directory (default: cache/)
uv run mlb-stats --cache-dir /path/to/cache sync games --season 2024
```

### Examples

```bash
# Sync a single day of games with verbose output
uv run mlb-stats -v sync games --start-date 2024-06-15 --end-date 2024-06-15

# Sync Opening Day 2024
uv run mlb-stats sync games --start-date 2024-03-28 --end-date 2024-03-28

# Sync the entire 2023 season (this will take a while)
uv run mlb-stats sync games --season 2023

# Sync games then boxscores for a week
uv run mlb-stats sync games --start-date 2024-07-01 --end-date 2024-07-07
uv run mlb-stats sync boxscores --start-date 2024-07-01 --end-date 2024-07-07
```

### Querying the Database

After syncing, you can query the SQLite database directly:

```bash
# Open the database with sqlite3
sqlite3 data/mlb_stats.db

# Example queries
sqlite3 data/mlb_stats.db "SELECT COUNT(*) FROM games;"
sqlite3 data/mlb_stats.db "SELECT name, abbreviation FROM teams ORDER BY name;"
sqlite3 data/mlb_stats.db "SELECT gamePk, gameDate, away_score, home_score FROM games LIMIT 10;"

# Player batting stats for a game
sqlite3 data/mlb_stats.db "
  SELECT p.fullName, b.hits, b.homeRuns, b.rbi, b.avg
  FROM game_batting b
  JOIN players p ON b.player_id = p.id
  WHERE b.gamePk = 745927
  ORDER BY b.battingOrder;"

# Top home run hitters across synced games
sqlite3 data/mlb_stats.db "
  SELECT p.fullName, SUM(b.homeRuns) as total_hr
  FROM game_batting b
  JOIN players p ON b.player_id = p.id
  GROUP BY p.id
  HAVING total_hr > 0
  ORDER BY total_hr DESC
  LIMIT 10;"

# Pitching stats for a game
sqlite3 data/mlb_stats.db "
  SELECT p.fullName, pit.inningsPitched, pit.strikeOuts, pit.earnedRuns, pit.note
  FROM game_pitching pit
  JOIN players p ON pit.player_id = p.id
  WHERE pit.gamePk = 745927
  ORDER BY pit.pitchingOrder;"
```

## Development

```bash
# Install dev dependencies
make install

# Run linting
make lint

# Auto-fix formatting issues
make reformat

# Run all tests
make test

# Run tests with coverage
make coverage
```

## Project Structure

```
src/mlb_stats/
├── __init__.py          # Package version
├── cli.py               # CLI entry points
├── api/
│   ├── client.py        # HTTP client with retry/rate limiting
│   ├── cache.py         # File-based JSON caching
│   └── endpoints.py     # API endpoint constants
├── db/
│   ├── connection.py    # SQLite connection management
│   ├── schema.py        # Database schema (all tables)
│   └── queries.py       # Database upsert/query helpers
├── models/
│   ├── team.py          # Team transformer
│   ├── venue.py         # Venue transformer
│   ├── game.py          # Game transformer
│   ├── player.py        # Player transformer
│   └── boxscore.py      # Batting/pitching transformers
├── collectors/
│   ├── schedule.py      # Schedule fetcher
│   ├── game.py          # Game sync orchestrator
│   ├── team.py          # Team sync (on-demand)
│   ├── venue.py         # Venue sync (on-demand)
│   ├── player.py        # Player sync (always fresh)
│   └── boxscore.py      # Boxscore sync orchestrator
└── utils/
    ├── logging.py       # Logging configuration
    ├── dates.py         # Date parsing/formatting
    └── metadata.py      # Write metadata helpers
```

## Database Schema

The database contains 11 tables:

**Reference tables:** `teams`, `venues`, `players`

**Game tables:** `games`, `game_officials`, `game_batting`, `game_pitching`

**Pitch-level tables:** `pitches`, `at_bats`, `batted_balls`

**Operational:** `sync_log`, `_meta`

## License

MIT License - see [LICENSE](LICENSE) for details.
