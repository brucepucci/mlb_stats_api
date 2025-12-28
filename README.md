# MLB Stats Collector

A Python CLI application that collects MLB game data from the MLB Stats API and stores it in SQLite. The tool fetches game schedules, box scores, pitch-by-pitch data with Statcast metrics, and reference data (teams, players).

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
git clone https://github.com/brucepucci/mlb_stats_api.git
cd mlb_stats_api

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

### Syncing Data

Fetch all game data from the MLB Stats API and store in the database. This includes games, teams, players, and batting/pitching stats.

```bash
# Sync a specific game by gamePk
uv run mlb-stats sync 745927

# Sync games for a date range
uv run mlb-stats sync --start-date 2024-07-01 --end-date 2024-07-07

# Sync all games for a season
uv run mlb-stats sync --season 2024

# Sync all data from 2008 to today (PITCHf/x era)
uv run mlb-stats sync --all

# Sync specific season range
uv run mlb-stats sync --start-season 2010 --end-season 2015

# Sync from 2018 to present
uv run mlb-stats sync --start-season 2018

# Sync from 2008 through 2020
uv run mlb-stats sync --end-season 2020

# Force refresh from API (ignore games already in database)
uv run mlb-stats sync --season 2024 --force-refresh

# Full historical sync with force refresh
uv run mlb-stats sync --all --force-refresh
```

**Note:** The `--force-refresh` flag is useful when you have partial data in the database and want to fetch the complete schedule from the API. Without it, the sync will only process games already in the database for that date range.

### Data Availability by Era

| Year Range | Pitch Data | Batted Ball Statcast |
|------------|------------|---------------------|
| 2008-2014 | PITCHf/x (velocity, location, spin, break) | ❌ No exit velo/launch angle |
| 2015+ | Statcast (PITCHf/x + extension, plateTime) | ✅ Yes (72-94% coverage) |

Pre-2015 games will have NULL values for:
- `extension` (pitcher release extension)
- `plateTime` (time to reach plate)
- `launchSpeed` (exit velocity)
- `launchAngle` (launch angle)
- `totalDistance` (hit distance)

### Global Options

These options can be used with any command:

```bash
# Increase verbosity (-v for INFO, -vv for DEBUG)
uv run mlb-stats -v sync --start-date 2024-07-01 --end-date 2024-07-01
uv run mlb-stats -vv sync --start-date 2024-07-01 --end-date 2024-07-01

# Suppress output (ERROR level only)
uv run mlb-stats --quiet sync --season 2024

# Use a custom database path (default: data/mlb_stats.db)
uv run mlb-stats --db-path /path/to/custom.db sync --season 2024

# Use a custom cache directory (default: cache/)
uv run mlb-stats --cache-dir /path/to/cache sync --season 2024
```

### Examples

```bash
# Sync a single day of games with verbose output
uv run mlb-stats -v sync --start-date 2024-06-15 --end-date 2024-06-15

# Sync Opening Day 2024
uv run mlb-stats sync --start-date 2024-03-28 --end-date 2024-03-28

# Sync the entire 2023 season (this will take a while)
uv run mlb-stats sync --season 2023 --force-refresh

# Sync all PITCHf/x era data (2008-present, ~40,000+ games)
uv run mlb-stats sync --all --force-refresh

# Sync just the PITCHf/x-only era (before Statcast)
uv run mlb-stats sync --start-season 2008 --end-season 2014

# Sync a specific decade
uv run mlb-stats sync --start-season 2010 --end-season 2019
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
│   ├── game.py          # Game transformer
│   ├── player.py        # Player transformer
│   └── boxscore.py      # Batting/pitching transformers
├── collectors/
│   ├── schedule.py      # Schedule fetcher
│   ├── game.py          # Game sync orchestrator
│   ├── team.py          # Team sync (on-demand)
│   ├── player.py        # Player sync (always fresh)
│   └── boxscore.py      # Boxscore sync orchestrator
└── utils/
    ├── logging.py       # Logging configuration
    ├── dates.py         # Date parsing/formatting
    └── metadata.py      # Write metadata helpers
```

## Database Schema

The database contains 13 tables:

**Reference tables:** `teams`, `players`, `venues`

**Game tables:** `games`, `game_officials`, `game_batting`, `game_pitching`, `game_rosters`

**Pitch-level tables:** `pitches`, `at_bats`, `batted_balls`

**Operational:** `sync_log`, `_meta`

## License

MIT License - see [LICENSE](LICENSE) for details.
