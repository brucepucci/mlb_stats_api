# CLAUDE.md

Project context for AI assistants working on the MLB Stats API data collection project.

## Project Overview

A Python CLI application that collects MLB game data from the MLB Stats API and stores it in SQLite. The tool fetches game schedules, box scores, pitch-by-pitch data with Statcast metrics, and reference data (teams, players).

**Full planning document:** `docs/PROJECT_PLAN.md`

## Key Design Principles

1. **Preserve MLB field names exactly** - Database columns use MLB's naming (e.g., `gamePk`, `strikeOuts`, not `game_pk`, `strike_outs`)
2. **Game-driven data collection** - Games are the source of truth; reference data (teams, venues, players) is fetched on-demand when encountered in game data
3. **Always upsert** - Use `INSERT OR REPLACE` for all writes; never check if record exists first
4. **Never cache reference data** - Players, teams, venues always fetched fresh to keep mutable fields current (`lastPlayedDate`, `currentTeam_id`, etc.)
5. **Cache immutable game data** - Game feed, boxscore, play-by-play cached indefinitely once game is Final
6. **Fail loudly** - Data quality issues should raise errors, not silently corrupt data

## Naming Conventions

| Context | Convention | Example |
|---------|------------|---------|
| Database columns | Exact MLB JSON field names | `gamePk`, `fullName`, `strikeOuts` |
| Python variables | snake_case | `game_pk`, `full_name`, `strike_outs` |
| Metadata columns | Underscore prefix | `_written_at`, `_git_hash`, `_version`, `_fetched_at` |
| Flattened nested objects | Underscore separator | `primaryPosition.code` → `primaryPosition_code` |

## Database Schema (12 Tables)

**Reference tables:** `teams`, `players`
**Game tables:** `games`, `game_officials`, `game_batting`, `game_pitching`, `game_rosters`
**Pitch-level tables:** `pitches`, `at_bats`, `batted_balls`
**Operational:** `sync_log`, `_meta`

Every table includes write metadata columns:
- `_written_at` - ISO8601 UTC timestamp of database write
- `_git_hash` - Git commit hash of code that wrote the row
- `_version` - Semantic version of the application

## Historical Data Eras

- **2008-2014:** PITCHf/x era - pitch tracking without Statcast enhancements
- **2015+:** Statcast era - full pitch and batted ball tracking
- **Pre-2008:** Limited data - no pitch-level tracking available

Pre-2015 games will have NULL values for Statcast-specific fields (`extension`, `plateTime`, `launchSpeed`, `launchAngle`, `totalDistance`).

## Write Metadata Pattern

```python
def get_write_metadata() -> dict:
    return {
        "_written_at": datetime.utcnow().isoformat() + "Z",
        "_git_hash": get_git_hash(),
        "_version": __version__,
    }

# Usage: Add to every row before insert
row_data.update(get_write_metadata())
cursor.execute("INSERT OR REPLACE INTO games (...) VALUES (...)", row_data)
```

## Reference Data Pattern

Reference data is fetched on-demand, never cached, always upserted:

```python
def sync_player(player_id: int) -> None:
    """Fetch player from API and upsert. Always fresh, never cached."""
    player_data = client.get_player(player_id)  # No cache
    row = transform_player(player_data)
    row.update(get_write_metadata())
    upsert_player(row)

# Called when processing boxscore:
for player_id in boxscore_player_ids:
    sync_player(player_id)  # Always fetch, always upsert
```

## Caching Rules

| Data Type | Cache? | Reason |
|-----------|--------|--------|
| Game feed (Final) | Yes | Immutable |
| Boxscore (Final) | Yes | Immutable |
| Play-by-play (Final) | Yes | Immutable |
| Schedule | No | Can change |
| Players | **No** | Mutable fields |
| Teams | **No** | Mutable fields |

## Implementation Phases

| Phase | Focus | Key Outputs |
|-------|-------|-------------|
| 1 | Foundation | HTTP client, caching, CLI skeleton, **full DB schema** |
| 2 | Games | Schedule sync, games table, team/venue on-demand fetch |
| 3 | Box Scores | Batting/pitching stats, player on-demand fetch |
| 4 | Pitch Data | Pitches, at-bats, batted balls, Statcast metrics |
| 5 | CLI Polish | Composite commands, export, documentation |

## Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Detailed diagnostic info | SQL queries, row-by-row details |
| `INFO` | Progress updates | "Syncing game 745927..." |
| `WARNING` | Unexpected but not error | "Player ID 999999 not found, skipping" |
| `ERROR` | Operation failed, continuing | "Failed to sync game, will retry" |
| `CRITICAL` | Cannot continue | "Database corrupted" |

## CLI Verbosity

| Flag | Level | Shows |
|------|-------|-------|
| (none) | WARNING | Progress bar + summary |
| `-v` | INFO | Which games/players processing |
| `-vv` | DEBUG | API calls, SQL statements |
| `--quiet` | ERROR | Summary only |

## API Endpoints

Base URL: `https://statsapi.mlb.com/api/`

| Endpoint | Purpose |
|----------|---------|
| `/v1/schedule` | Game schedule by date range |
| `/v1.1/game/{gamePk}/feed/live` | Full game data including plays |
| `/v1/game/{gamePk}/boxscore` | Box score stats |
| `/v1/game/{gamePk}/playByPlay` | Pitch-by-pitch data |
| `/v1/people/{personId}` | Player info |
| `/v1/teams/{teamId}` | Team info |

## Technical Stack

- Python 3.11+
- SQLite (WAL mode, foreign keys enabled)
- `uv` for package management
- `requests` for HTTP
- `click` for CLI
- `pytest` for testing

**Explicitly NOT using:** pandas, SQLAlchemy, asyncio/aiohttp

## Things to Avoid

1. **Don't rename MLB fields** - Keep `gamePk`, not `game_pk`
2. **Don't check before insert** - Just upsert, let the database handle it
3. **Don't cache reference data** - Always fetch fresh
4. **Don't use pandas** - Keep dependencies minimal
5. **Don't swallow errors** - Log them, handle them, but don't hide them
6. **Don't assume Statcast data exists** - Pre-2015 games won't have it

## Testing Requirements

- Unit tests for all transformers
- Integration tests with mocked HTTP responses
- Live API tests marked `@pytest.mark.slow`
- Verify foreign key constraints
- Verify stat totals match (e.g., player runs = game score)

## File Structure

```
src/mlb_stats/
├── __init__.py
├── cli.py
├── api/
│   ├── client.py          # MLBStatsClient with retry/rate limiting
│   ├── cache.py           # File-based caching (game data only)
│   └── endpoints.py       # URL constants
├── db/
│   ├── connection.py      # get_connection(), init_db()
│   ├── schema.py          # create_tables()
│   └── queries.py         # Upsert helpers
├── models/
│   ├── team.py            # transform_team()
│   ├── player.py          # transform_player()
│   ├── game.py            # transform_game()
│   └── boxscore.py        # transform_batting(), transform_pitching()
├── collectors/
│   ├── schedule.py
│   ├── game.py
│   ├── boxscore.py
│   ├── team.py            # On-demand
│   └── player.py          # On-demand
└── utils/
    ├── logging.py
    ├── metadata.py        # get_write_metadata()
    └── dates.py
```
