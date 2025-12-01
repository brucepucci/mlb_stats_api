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

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone the repository
git clone https://github.com/yourusername/mlb-stats.git
cd mlb-stats

# Install dependencies
make install

# Initialize the database
mlb-stats init-db
```

## Quick Start

```bash
# Initialize the database (creates all tables)
mlb-stats init-db

# Check version
mlb-stats --version

# Get help
mlb-stats --help
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
│   └── schema.py        # Database schema (all tables)
└── utils/
    ├── logging.py       # Logging configuration
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
