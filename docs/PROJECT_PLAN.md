# MLB Stats API Data Collection Project

## Project Planning Document

**Version:** 1.0.0  
**Purpose:** Instructions for building a Python application to collect MLB game data from the MLB Stats API and store it in SQLite for use by researchers and data scientists in fantasy baseball analysis.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [MLB Stats API Reference](#2-mlb-stats-api-reference)
3. [Database Schema Design](#3-database-schema-design)
4. [Project Structure](#4-project-structure)
5. [Implementation Phases](#5-implementation-phases)
6. [Technical Requirements](#6-technical-requirements)
7. [Testing Strategy](#7-testing-strategy)
8. [Documentation Requirements](#8-documentation-requirements)
9. [CI/CD and Version Control](#9-cicd-and-version-control)

---

## 1. Project Overview

### 1.1 Objectives

Build a CLI-based Python application that:

- Fetches game schedules, box scores, and pitch-level data from the MLB Stats API
- Stores data in a SQLite database optimized for analytical queries
- Supports incremental data collection (e.g., backfill historical data, update with new games)
- Operates as a good API citizen with caching and rate limiting
- Runs on Mac, Linux, and resource-constrained devices (e.g., Raspberry Pi)

### 1.2 Scope

**In Scope:**
- Game box score data (separate hitter and pitcher tables)
- Game metadata (score, venue, attendance, start time, weather, umpires, game type)
- Pitch-level data from play-by-play including Statcast metrics
- Batted ball data (exit velocity, launch angle, distance, trajectory)
- Statcast pitch data (spin rate, extension, break metrics)
- Player biographical information
- Team information
- Data from 2008 onwards (when MLB Stats API coverage begins)
  - Note: Statcast data available from 2015+, with improved tracking from 2017+

**Out of Scope:**
- Real-time/live game tracking
- Data prior to 2008
- Integration with other data sources (Baseball Reference, FanGraphs, etc.)
- Fielding tracking data (catch probability, route efficiency, etc.)

### 1.3 Design Principles

1. **Preserve MLB field names exactly** - Do not rename fields; use MLB's naming conventions as-is
2. **Use MLB identifiers** - gamePk, personId, teamId, venueId are the canonical identifiers
3. **Queryability first** - Design tables for intuitive SQL queries without excessive JOINs
4. **Accept reasonable redundancy** - Denormalize where it improves query simplicity
5. **Fail loudly** - Data quality issues should raise errors, not silently corrupt data
6. **Consistency over cleverness** - Use the same patterns everywhere

### 1.4 Naming Conventions

How "preserve MLB field names" works in practice:

- **Database columns**: Use exact MLB JSON field names (e.g., `gamePk`, `fullName`, `strikeOuts`)
- **Python variables**: Use snake_case internally (e.g., `game_pk`, `full_name`, `strike_outs`)
- **Transformation functions**: Convert between conventions at the data boundary
- **Nested objects**: Flatten with underscores (e.g., `primaryPosition.code` → `primaryPosition_code`)
- **Metadata columns**: Prefix with underscore to distinguish from MLB fields (e.g., `_written_at`)

---

## 2. MLB Stats API Reference

### 2.1 Base URL and Authentication

```
Base URL: https://statsapi.mlb.com/api/
```

The MLB Stats API is **publicly accessible** with no authentication required for the endpoints we need.

### 2.2 Key Identifiers

| Identifier | Description | Example |
|------------|-------------|---------|
| `gamePk` | Unique game identifier | `745927` |
| `personId` | Unique player identifier | `660271` (Shohei Ohtani) |
| `teamId` | Unique team identifier | `119` (Los Angeles Dodgers) |
| `venueId` | Unique venue identifier | `22` (Dodger Stadium) |
| `sportId` | Sport identifier (MLB = 1) | `1` |

### 2.3 Key Endpoints

#### Schedule Endpoint
Retrieves games for a date range.

```
GET /v1/schedule?sportId=1&startDate={YYYY-MM-DD}&endDate={YYYY-MM-DD}
GET /v1/schedule?sportId=1&date={YYYY-MM-DD}
```

**Response Structure:**
```json
{
  "dates": [
    {
      "date": "2024-07-01",
      "games": [
        {
          "gamePk": 745927,
          "gameDate": "2024-07-02T02:10:00Z",
          "status": {"abstractGameState": "Final", "detailedState": "Final"},
          "teams": {
            "away": {"team": {"id": 137, "name": "San Francisco Giants"}},
            "home": {"team": {"id": 119, "name": "Los Angeles Dodgers"}}
          },
          "venue": {"id": 22, "name": "Dodger Stadium"}
        }
      ]
    }
  ]
}
```

#### Game Feed (Live Data) Endpoint
Retrieves complete game data including boxscore and play-by-play.

```
GET /v1.1/game/{gamePk}/feed/live
```

**Response Structure (simplified):**
```json
{
  "gamePk": 745927,
  "gameData": {
    "game": {"pk": 745927, "type": "R", "season": "2024"},
    "datetime": {"dateTime": "2024-07-02T02:10:00Z"},
    "status": {"abstractGameState": "Final"},
    "teams": {"away": {...}, "home": {...}},
    "players": {"ID545361": {...}},
    "venue": {"id": 22, "name": "Dodger Stadium"},
    "weather": {"condition": "Clear", "temp": "72", "wind": "5 mph"},
    "officialScorer": {...},
    "primaryDatacaster": {...}
  },
  "liveData": {
    "plays": {
      "allPlays": [...],
      "currentPlay": {...}
    },
    "linescore": {...},
    "boxscore": {
      "teams": {
        "away": {"players": {...}, "teamStats": {...}},
        "home": {"players": {...}, "teamStats": {...}}
      },
      "officials": [...]
    }
  }
}
```

#### Boxscore Endpoint
Retrieves boxscore only (lighter weight than full feed).

```
GET /v1/game/{gamePk}/boxscore
```

#### Play-by-Play Endpoint
Retrieves play-by-play only.

```
GET /v1/game/{gamePk}/playByPlay
```

**Play Structure (includes pitch and Statcast data):**
```json
{
  "result": {
    "type": "atBat",
    "event": "Strikeout",
    "eventType": "strikeout",
    "description": "...",
    "rbi": 0,
    "awayScore": 0,
    "homeScore": 0
  },
  "about": {
    "atBatIndex": 0,
    "halfInning": "top",
    "inning": 1,
    "startTime": "2024-07-02T02:15:00Z",
    "endTime": "2024-07-02T02:18:00Z",
    "isComplete": true,
    "isScoringPlay": false
  },
  "count": {"balls": 1, "strikes": 3, "outs": 1},
  "matchup": {
    "batter": {"id": 660271, "fullName": "..."},
    "pitcher": {"id": 543243, "fullName": "..."},
    "batSide": {"code": "L"},
    "pitchHand": {"code": "R"}
  },
  "playEvents": [
    {
      "details": {
        "call": {"code": "B", "description": "Ball"},
        "description": "Ball",
        "ballColor": "rgba(39, 161, 39, 1.0)",
        "type": {"code": "FF", "description": "Four-Seam Fastball"},
        "isInPlay": false,
        "isStrike": false,
        "isBall": true
      },
      "count": {"balls": 1, "strikes": 0, "outs": 0},
      "pitchData": {
        "startSpeed": 95.2,
        "endSpeed": 87.1,
        "zone": 14,
        "strikeZoneTop": 3.49,
        "strikeZoneBottom": 1.6,
        "coordinates": {
          "x": 120.5,
          "y": 180.3,
          "pX": 0.45,
          "pZ": 2.31,
          "x0": -1.72,
          "y0": 50.0,
          "z0": 5.64,
          "vX0": 8.21,
          "vY0": -128.65,
          "vZ0": -6.34,
          "aX": 0.24,
          "aY": 27.1,
          "aZ": -31.21,
          "pfxX": 0.15,
          "pfxZ": 0.57
        },
        "breaks": {
          "breakAngle": 3.6,
          "breakLength": 8.4,
          "breakY": 24.0,
          "spinRate": 2423,
          "spinDirection": 184
        },
        "typeConfidence": 0.9,
        "plateTime": 0.43,
        "extension": 6.22
      },
      "index": 0,
      "playId": "ca063f74-f034-455f-9016-d35ce2d895db",
      "pitchNumber": 1,
      "isPitch": true,
      "type": "pitch",
      "startTime": "2024-07-02T02:15:00.000Z",
      "endTime": "2024-07-02T02:15:05.000Z"
    },
    {
      "details": {
        "call": {"code": "X", "description": "In play, out(s)"},
        "description": "In play, out(s)",
        "type": {"code": "FF", "description": "Four-Seam Fastball"},
        "isInPlay": true
      },
      "pitchData": {...},
      "hitData": {
        "launchSpeed": 101.9,
        "launchAngle": 28,
        "totalDistance": 389,
        "trajectory": "fly_ball",
        "hardness": "hard",
        "location": "8",
        "coordinates": {
          "coordX": 125.4,
          "coordY": 48.2
        }
      },
      "isPitch": true,
      "type": "pitch"
    }
  ]
}
```

#### People (Player) Endpoint

```
GET /v1/people/{personId}
GET /v1/people?personIds={id1},{id2},{id3}
```

**Response Structure:**
```json
{
  "people": [
    {
      "id": 660271,
      "fullName": "Shohei Ohtani",
      "firstName": "Shohei",
      "lastName": "Ohtani",
      "primaryNumber": "17",
      "birthDate": "1994-07-05",
      "birthCity": "Oshu",
      "birthCountry": "Japan",
      "height": "6' 4\"",
      "weight": 210,
      "active": true,
      "primaryPosition": {"code": "Y", "name": "Two-Way Player", "type": "Two-Way Player"},
      "batSide": {"code": "L", "description": "Left"},
      "pitchHand": {"code": "R", "description": "Right"},
      "mlbDebutDate": "2018-03-29",
      "currentTeam": {"id": 119, "name": "Los Angeles Dodgers"}
    }
  ]
}
```

#### Teams Endpoint

```
GET /v1/teams?sportId=1
GET /v1/teams/{teamId}
```

**Response Structure:**
```json
{
  "teams": [
    {
      "id": 119,
      "name": "Los Angeles Dodgers",
      "teamCode": "lan",
      "fileCode": "la",
      "abbreviation": "LAD",
      "teamName": "Dodgers",
      "locationName": "Los Angeles",
      "firstYearOfPlay": "1884",
      "league": {"id": 104, "name": "National League"},
      "division": {"id": 203, "name": "National League West"},
      "venue": {"id": 22, "name": "Dodger Stadium"},
      "active": true
    }
  ]
}
```

#### Venue Endpoint

```
GET /v1/venues/{venueId}
```

#### Meta Endpoint
Retrieves lookup values for various types.

```
GET /v1/meta?type={type}
```

Available types: `gameTypes`, `gameStatus`, `pitchTypes`, `pitchCodes`, `eventTypes`, `positions`, `situationCodes`, `statTypes`, `statGroups`

### 2.4 API Best Practices

1. **Rate Limiting:** While MLB does not publish explicit rate limits, be conservative:
   - Add 0.5-1 second delay between requests
   - Implement exponential backoff on errors
   - Never make concurrent requests to the same endpoint

2. **Caching:** 
   - Cache raw JSON responses to disk
   - Final game data is immutable - cache permanently
   - In-progress games should be re-fetched

3. **User-Agent:** Include a descriptive User-Agent header

4. **Error Handling:**
   - Handle HTTP 429 (rate limit) with exponential backoff
   - Handle HTTP 5xx with retry logic
   - Log all errors with full context

### 2.5 Caching Strategy

Cache raw JSON responses to avoid redundant API calls. **Only cache immutable game data, not reference data.**

**What Gets Cached:**
| Data Type | Cache? | Reason |
|-----------|--------|--------|
| Game feed (Final) | Yes, indefinitely | Immutable once complete |
| Boxscore (Final) | Yes, indefinitely | Immutable once complete |
| Play-by-play (Final) | Yes, indefinitely | Immutable once complete |
| Schedule | No | Games can be postponed/rescheduled |
| Players | **No** | `lastPlayedDate`, `currentTeam_id`, `active` change frequently |
| Teams | **No** | Venue, division can change mid-season |
| Venues | **No** | Capacity, name can change |

Reference data API calls are lightweight. With 0.5s rate limiting, fetching 50 unique players in a day's games adds ~25 seconds. Worth it for accurate data.

**Cache Directory Structure:**
```
cache/
├── game_feed/
│   ├── 745927.json
│   └── 745928.json
├── boxscore/
│   ├── 745927.json
│   └── 745928.json
└── play_by_play/
    ├── 745927.json
    └── 745928.json
```

**Cache File Naming:**
- Game feed: `{cache_dir}/game_feed/{gamePk}.json`
- Boxscore: `{cache_dir}/boxscore/{gamePk}.json`
- Play-by-play: `{cache_dir}/play_by_play/{gamePk}.json`

**Cache Validity:**
- Only cache games where `abstractGameState = "Final"`
- In-progress or preview games are never cached

**Cache Bypass:**
- `--no-cache` flag: Ignore cache, fetch fresh data (still writes to cache)
- `--refresh` flag: Alias for `--no-cache`
- Cache only stores JSON body, not response headers

---

## 3. Database Schema Design

### 3.1 Design Philosophy

- Tables are optimized for common fantasy baseball queries
- Foreign keys reference MLB IDs directly (gamePk, personId, teamId)
- Timestamps stored in UTC
- Nullable fields allowed where MLB data may be missing
- Compound primary keys where appropriate
- Every row includes write metadata for provenance tracking:
  - `_written_at`: ISO8601 UTC timestamp when the row was written to the database
  - `_git_hash`: Git commit hash of the code that wrote the row
  - `_version`: Semantic version of the project at write time
  - Note: These use underscore prefix to distinguish from MLB field names

### 3.2 Core Tables

#### `teams`
Reference table for team information.

```sql
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,              -- MLB teamId
    name TEXT NOT NULL,                  -- "Los Angeles Dodgers"
    teamCode TEXT,                       -- "lan"
    fileCode TEXT,                       -- "la"
    abbreviation TEXT,                   -- "LAD"
    teamName TEXT,                       -- "Dodgers"
    locationName TEXT,                   -- "Los Angeles"
    firstYearOfPlay TEXT,
    league_id INTEGER,
    league_name TEXT,
    division_id INTEGER,
    division_name TEXT,
    venue_id INTEGER,
    active INTEGER,                      -- 1 or 0
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,            -- ISO8601 UTC timestamp of API fetch
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,           -- ISO8601 UTC timestamp when row was written
    _git_hash TEXT NOT NULL,             -- Git commit hash of code that wrote this row
    _version TEXT NOT NULL,              -- Semantic version of project at write time
    
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);
```

#### `venues`
Reference table for venue/stadium information.

```sql
CREATE TABLE venues (
    id INTEGER PRIMARY KEY,              -- MLB venueId
    name TEXT NOT NULL,
    city TEXT,
    state TEXT,
    stateAbbrev TEXT,
    country TEXT,
    
    -- Location data (may be null)
    latitude REAL,
    longitude REAL,
    elevation REAL,
    timezone TEXT,
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL
);
```

#### `players`
Reference table for player biographical data.

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,              -- MLB personId
    fullName TEXT NOT NULL,
    firstName TEXT,
    lastName TEXT,
    useName TEXT,
    middleName TEXT,
    boxscoreName TEXT,
    nickName TEXT,
    
    primaryNumber TEXT,
    birthDate TEXT,                      -- YYYY-MM-DD
    birthCity TEXT,
    birthStateProvince TEXT,
    birthCountry TEXT,
    deathDate TEXT,
    deathCity TEXT,
    deathStateProvince TEXT,
    deathCountry TEXT,
    
    height TEXT,                         -- "6' 4\""
    weight INTEGER,
    
    primaryPosition_code TEXT,
    primaryPosition_name TEXT,
    primaryPosition_type TEXT,
    primaryPosition_abbreviation TEXT,
    
    batSide_code TEXT,                   -- L, R, S
    batSide_description TEXT,
    pitchHand_code TEXT,                 -- L, R, S
    pitchHand_description TEXT,
    
    draftYear INTEGER,
    mlbDebutDate TEXT,
    lastPlayedDate TEXT,
    
    active INTEGER,                      -- 1 or 0
    
    currentTeam_id INTEGER,
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (currentTeam_id) REFERENCES teams(id)
);
```

#### `games`
Core game information table.

```sql
CREATE TABLE games (
    gamePk INTEGER PRIMARY KEY,
    
    -- Identifiers
    season INTEGER NOT NULL,
    gameType TEXT NOT NULL,              -- 'R', 'F', 'D', 'L', 'W', 'S', 'E', 'A'
    gameDate TEXT NOT NULL,              -- Date portion YYYY-MM-DD
    gameDateTime TEXT,                   -- Full ISO8601 UTC timestamp
    officialDate TEXT,                   -- MLB's official game date
    
    -- Teams
    away_team_id INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    
    -- Final score
    away_score INTEGER,
    home_score INTEGER,
    
    -- Status
    abstractGameState TEXT,              -- 'Final', 'Live', 'Preview'
    detailedState TEXT,                  -- 'Final', 'In Progress', etc.
    statusCode TEXT,
    
    -- Venue
    venue_id INTEGER,
    venue_name TEXT,                     -- Denormalized for convenience
    
    -- Game details
    dayNight TEXT,                       -- 'day', 'night'
    scheduledInnings INTEGER,
    inningCount INTEGER,                 -- Actual innings played
    
    -- Weather (when available)
    weather_condition TEXT,
    weather_temp TEXT,
    weather_wind TEXT,
    
    -- Attendance
    attendance INTEGER,
    
    -- Timing
    firstPitch TEXT,                     -- ISO8601 UTC
    gameEndDateTime TEXT,                -- ISO8601 UTC (if available)
    
    -- Doubleheader info
    doubleHeader TEXT,                   -- 'Y', 'N', 'S'
    gameNumber INTEGER,                  -- 1 or 2 for doubleheaders
    
    -- Series info
    seriesDescription TEXT,
    seriesGameNumber INTEGER,
    gamesInSeries INTEGER,
    
    -- Home plate umpire (denormalized for quick access)
    umpire_HP_id INTEGER,
    umpire_HP_name TEXT,
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (away_team_id) REFERENCES teams(id),
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (venue_id) REFERENCES venues(id)
);

CREATE INDEX idx_games_date ON games(gameDate);
CREATE INDEX idx_games_season ON games(season);
CREATE INDEX idx_games_away_team ON games(away_team_id);
CREATE INDEX idx_games_home_team ON games(home_team_id);
```

#### `game_officials`
Umpires and other officials for each game. Note: The home plate umpire is also denormalized onto the `games` table (`umpire_HP_id`, `umpire_HP_name`) for quick access in pitch analysis queries. This table contains the complete crew for advanced umpire analysis.

```sql
CREATE TABLE game_officials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    
    official_id INTEGER,
    official_fullName TEXT,
    officialType TEXT,                   -- 'Home Plate', 'First Base', etc.
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    UNIQUE(gamePk, officialType)
);

CREATE INDEX idx_game_officials_gamepk ON game_officials(gamePk);
```

#### `game_batting`
Per-player batting stats for each game.

```sql
CREATE TABLE game_batting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    
    -- Batting order and position
    battingOrder INTEGER,                -- 100, 200, etc. (100 = leadoff)
    position_code TEXT,
    position_name TEXT,
    position_abbreviation TEXT,
    
    -- Standard batting stats (preserve MLB field names)
    gamesPlayed INTEGER,
    flyOuts INTEGER,
    groundOuts INTEGER,
    runs INTEGER,
    doubles INTEGER,
    triples INTEGER,
    homeRuns INTEGER,
    strikeOuts INTEGER,
    baseOnBalls INTEGER,
    intentionalWalks INTEGER,
    hits INTEGER,
    hitByPitch INTEGER,
    atBats INTEGER,
    caughtStealing INTEGER,
    stolenBases INTEGER,
    groundIntoDoublePlay INTEGER,
    groundIntoTriplePlay INTEGER,
    plateAppearances INTEGER,
    totalBases INTEGER,
    rbi INTEGER,
    leftOnBase INTEGER,
    sacBunts INTEGER,
    sacFlies INTEGER,
    catchersInterference INTEGER,
    pickoffs INTEGER,
    
    -- Calculated stats from API (as strings to preserve formatting)
    avg TEXT,
    obp TEXT,
    slg TEXT,
    ops TEXT,
    
    -- Game context
    atBatsPerHomeRun TEXT,
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    UNIQUE(gamePk, player_id)
);

CREATE INDEX idx_game_batting_gamepk ON game_batting(gamePk);
CREATE INDEX idx_game_batting_player ON game_batting(player_id);
CREATE INDEX idx_game_batting_team ON game_batting(team_id);
```

#### `game_pitching`
Per-player pitching stats for each game.

```sql
CREATE TABLE game_pitching (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    
    -- Role info
    isStartingPitcher INTEGER,           -- 1 or 0
    pitchingOrder INTEGER,               -- Order of appearance
    
    -- Standard pitching stats (preserve MLB field names)
    gamesPlayed INTEGER,
    gamesStarted INTEGER,
    flyOuts INTEGER,
    groundOuts INTEGER,
    airOuts INTEGER,
    runs INTEGER,
    doubles INTEGER,
    triples INTEGER,
    homeRuns INTEGER,
    strikeOuts INTEGER,
    baseOnBalls INTEGER,
    intentionalWalks INTEGER,
    hits INTEGER,
    hitByPitch INTEGER,
    atBats INTEGER,
    caughtStealing INTEGER,
    stolenBases INTEGER,
    numberOfPitches INTEGER,
    inningsPitched TEXT,                 -- Keep as text (e.g., "6.2")
    wins INTEGER,
    losses INTEGER,
    saves INTEGER,
    saveOpportunities INTEGER,
    holds INTEGER,
    blownSaves INTEGER,
    earnedRuns INTEGER,
    battersFaced INTEGER,
    outs INTEGER,
    gamesPitched INTEGER,
    completeGames INTEGER,
    shutouts INTEGER,
    pitchesThrown INTEGER,
    balls INTEGER,
    strikes INTEGER,
    strikePercentage TEXT,
    hitBatsmen INTEGER,
    balks INTEGER,
    wildPitches INTEGER,
    pickoffs INTEGER,
    rbi INTEGER,
    gamesFinished INTEGER,
    runsScoredPer9 TEXT,
    homeRunsPer9 TEXT,
    inheritedRunners INTEGER,
    inheritedRunnersScored INTEGER,
    catchersInterference INTEGER,
    sacBunts INTEGER,
    sacFlies INTEGER,
    passedBall INTEGER,
    
    -- Calculated stats from API
    era TEXT,
    whip TEXT,
    
    -- Game result attribution
    note TEXT,                           -- 'W', 'L', 'S', 'H', 'BS', etc.
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    UNIQUE(gamePk, player_id)
);

CREATE INDEX idx_game_pitching_gamepk ON game_pitching(gamePk);
CREATE INDEX idx_game_pitching_player ON game_pitching(player_id);
CREATE INDEX idx_game_pitching_team ON game_pitching(team_id);
```

#### `pitches`
Pitch-level data from play-by-play including Statcast metrics.

```sql
CREATE TABLE pitches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    
    -- At-bat context
    atBatIndex INTEGER NOT NULL,         -- Index of the at-bat in the game
    pitchNumber INTEGER NOT NULL,        -- Pitch number within the at-bat
    
    -- Inning context
    inning INTEGER NOT NULL,
    halfInning TEXT NOT NULL,            -- 'top', 'bottom'
    
    -- Matchup
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    
    -- Batter/pitcher info at time of pitch
    batSide_code TEXT,                   -- L, R
    pitchHand_code TEXT,                 -- L, R
    
    -- Count before pitch
    balls INTEGER,
    strikes INTEGER,
    outs INTEGER,
    
    -- Pitch result
    call_code TEXT,                      -- 'B', 'S', 'X', 'F', etc.
    call_description TEXT,               -- 'Ball', 'Called Strike', etc.
    isInPlay INTEGER,                    -- 1 or 0
    isStrike INTEGER,                    -- 1 or 0
    isBall INTEGER,                      -- 1 or 0
    
    -- Pitch type
    type_code TEXT,                      -- 'FF', 'SL', 'CH', etc.
    type_description TEXT,               -- 'Four-Seam Fastball', etc.
    typeConfidence REAL,                 -- Pitch classification confidence
    
    -- Pitch velocity
    startSpeed REAL,                     -- Release velocity (mph)
    endSpeed REAL,                       -- Velocity at plate (mph)
    
    -- Strike zone
    zone INTEGER,                        -- Strike zone number (1-14)
    strikeZoneTop REAL,                  -- Top of zone (feet)
    strikeZoneBottom REAL,               -- Bottom of zone (feet)
    
    -- Pitch location at plate
    plateX REAL,                         -- pX: horizontal position (feet from center)
    plateZ REAL,                         -- pZ: vertical position (feet)
    
    -- Pitch coordinates (legacy/display)
    coordinates_x REAL,
    coordinates_y REAL,
    
    -- Release point
    x0 REAL,                             -- Horizontal release position (feet)
    y0 REAL,                             -- Distance from plate at release (feet)
    z0 REAL,                             -- Vertical release position (feet)
    
    -- Initial velocity components
    vX0 REAL,                            -- X velocity at y=50ft (ft/s)
    vY0 REAL,                            -- Y velocity at y=50ft (ft/s)
    vZ0 REAL,                            -- Z velocity at y=50ft (ft/s)
    
    -- Acceleration components
    aX REAL,                             -- X acceleration (ft/s^2)
    aY REAL,                             -- Y acceleration (ft/s^2)
    aZ REAL,                             -- Z acceleration (ft/s^2)
    
    -- Movement (PITCHf/x style)
    pfxX REAL,                           -- Horizontal movement (inches)
    pfxZ REAL,                           -- Vertical movement (inches)
    
    -- Statcast break metrics
    breakAngle REAL,                     -- Break angle (degrees)
    breakLength REAL,                    -- Break length (inches)
    breakY REAL,                         -- Distance from plate where break occurs
    
    -- Statcast spin metrics
    spinRate INTEGER,                    -- Spin rate (RPM)
    spinDirection INTEGER,               -- Spin direction (degrees, 0-360)
    
    -- Statcast timing/extension
    plateTime REAL,                      -- Time to plate (seconds)
    extension REAL,                      -- Release extension (feet)
    
    -- Timestamps
    startTime TEXT,                      -- ISO8601 UTC
    endTime TEXT,
    
    -- Metadata
    playId TEXT,                         -- MLB's unique play identifier
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (batter_id) REFERENCES players(id),
    FOREIGN KEY (pitcher_id) REFERENCES players(id),
    UNIQUE(gamePk, atBatIndex, pitchNumber)
);

CREATE INDEX idx_pitches_gamepk ON pitches(gamePk);
CREATE INDEX idx_pitches_batter ON pitches(batter_id);
CREATE INDEX idx_pitches_pitcher ON pitches(pitcher_id);
CREATE INDEX idx_pitches_atbat ON pitches(gamePk, atBatIndex);
CREATE INDEX idx_pitches_type ON pitches(type_code);
CREATE INDEX idx_pitches_spin ON pitches(spinRate);
CREATE INDEX idx_pitches_velo ON pitches(startSpeed);
```

#### `batted_balls`
Statcast batted ball data for balls put in play.

```sql
CREATE TABLE batted_balls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    
    -- Link to pitch that was hit
    atBatIndex INTEGER NOT NULL,
    pitchNumber INTEGER NOT NULL,        -- The pitch that was put in play
    
    -- Matchup
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    
    -- Inning context
    inning INTEGER NOT NULL,
    halfInning TEXT NOT NULL,
    
    -- Statcast batted ball metrics
    launchSpeed REAL,                    -- Exit velocity (mph)
    launchAngle REAL,                    -- Launch angle (degrees)
    totalDistance REAL,                  -- Projected/actual distance (feet)
    
    -- Batted ball classification
    trajectory TEXT,                     -- 'fly_ball', 'ground_ball', 'line_drive', 'popup'
    hardness TEXT,                       -- 'soft', 'medium', 'hard'
    
    -- Field location
    location TEXT,                       -- Position number where ball was fielded
    coordinates_x REAL,                  -- Hit coordinates X (spray chart)
    coordinates_y REAL,                  -- Hit coordinates Y (spray chart)
    
    -- Play result
    event TEXT,                          -- 'single', 'double', 'home_run', 'field_out', etc.
    eventType TEXT,
    description TEXT,
    
    -- Scoring impact
    rbi INTEGER,
    awayScore INTEGER,                   -- Score after play
    homeScore INTEGER,
    
    -- Calculated metrics (if available from API)
    hitProbability REAL,                 -- xBA - expected batting average
    
    -- Metadata
    playId TEXT,
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (batter_id) REFERENCES players(id),
    FOREIGN KEY (pitcher_id) REFERENCES players(id),
    FOREIGN KEY (gamePk, atBatIndex, pitchNumber) REFERENCES pitches(gamePk, atBatIndex, pitchNumber),
    UNIQUE(gamePk, atBatIndex, pitchNumber)
);

CREATE INDEX idx_batted_balls_gamepk ON batted_balls(gamePk);
CREATE INDEX idx_batted_balls_batter ON batted_balls(batter_id);
CREATE INDEX idx_batted_balls_pitcher ON batted_balls(pitcher_id);
CREATE INDEX idx_batted_balls_exit_velo ON batted_balls(launchSpeed);
CREATE INDEX idx_batted_balls_launch_angle ON batted_balls(launchAngle);
CREATE INDEX idx_batted_balls_trajectory ON batted_balls(trajectory);
CREATE INDEX idx_batted_balls_event ON batted_balls(eventType);
```

#### `at_bats`
Summary table for each plate appearance.

```sql
CREATE TABLE at_bats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    atBatIndex INTEGER NOT NULL,
    
    -- Inning context
    inning INTEGER NOT NULL,
    halfInning TEXT NOT NULL,
    
    -- Matchup
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    batSide_code TEXT,
    pitchHand_code TEXT,
    
    -- Result
    event TEXT,                          -- 'Strikeout', 'Single', 'Walk', etc.
    eventType TEXT,                      -- 'strikeout', 'single', 'walk', etc.
    description TEXT,
    
    -- Scoring
    rbi INTEGER,
    awayScore INTEGER,                   -- Score after this at-bat
    homeScore INTEGER,
    
    -- At-bat details
    isComplete INTEGER,
    hasReview INTEGER,
    hasOut INTEGER,
    isScoringPlay INTEGER,
    
    -- Count at end
    balls INTEGER,
    strikes INTEGER,
    outs INTEGER,                        -- Outs after this at-bat
    
    -- Timing
    startTime TEXT,
    endTime TEXT,
    
    -- Pitch count
    pitchCount INTEGER,
    
    -- API fetch metadata
    _fetched_at TEXT NOT NULL,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,
    
    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (batter_id) REFERENCES players(id),
    FOREIGN KEY (pitcher_id) REFERENCES players(id),
    UNIQUE(gamePk, atBatIndex)
);

CREATE INDEX idx_at_bats_gamepk ON at_bats(gamePk);
CREATE INDEX idx_at_bats_batter ON at_bats(batter_id);
CREATE INDEX idx_at_bats_pitcher ON at_bats(pitcher_id);
CREATE INDEX idx_at_bats_event ON at_bats(eventType);
```

#### `sync_log`
Tracks data collection runs for incremental updates.

```sql
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,             -- 'schedule', 'boxscore', 'play_by_play', etc.
    start_date TEXT,                     -- Date range start
    end_date TEXT,                       -- Date range end
    gamePk INTEGER,                      -- Specific game if applicable
    status TEXT NOT NULL,                -- 'started', 'completed', 'failed'
    records_processed INTEGER,
    error_message TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    
    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL
);

CREATE INDEX idx_sync_log_type ON sync_log(sync_type);
CREATE INDEX idx_sync_log_status ON sync_log(status);
```

### 3.3 Database Configuration

```python
# SQLite pragmas for performance
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA cache_size = -64000;  # 64MB cache
```

### 3.4 Database Write Strategy

**Game-Driven Approach:**
Reference data (teams, venues, players) is fetched on-demand when encountered in game data, not up-front. This ensures we only store reference records for entities that appear in our games, and reference data stays fresh (always fetched from API, never cached).

**Upsert Behavior:**
- Use `INSERT OR REPLACE` for all tables (full row replacement on primary key conflict)
- Re-syncing a game overwrites all its data with fresh API data
- Reference data always fetched fresh and upserted (keeps `lastPlayedDate`, `currentTeam_id`, etc. current)
- The `_written_at` timestamp reflects the most recent write, not the original insert

**Transaction Boundaries:**
- Each game is its own transaction (all tables for one game committed together)
- Reference data (players, teams, venues) are individual transactions
- Batch inserts within a transaction for performance (e.g., all pitches for a game)

**Write Order (foreign key compliance):**
1. Teams and venues (no dependencies) - fetched when game encountered
2. Players (depends on teams) - fetched when boxscore encountered
3. Games (depends on teams, venues)
4. Game officials (depends on games)
5. Game batting/pitching (depends on games, players, teams)
6. At-bats (depends on games, players)
7. Pitches (depends on games, players)
8. Batted balls (depends on games, players, pitches)

### 3.5 Schema Versioning and Migration

**Version Tracking:**
```sql
CREATE TABLE _meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Initial insert
INSERT INTO _meta (key, value) VALUES ('schema_version', '1.0.0');
```

**Migration Strategy:**
- On startup, compare `_meta.schema_version` against code's expected version
- **Patch version bump** (1.0.0 → 1.0.1): No schema changes, no action needed
- **Minor version bump** (1.0.0 → 1.1.0): New columns/tables added, run `ALTER TABLE` migrations automatically
- **Major version bump** (1.0.0 → 2.0.0): Breaking changes, require explicit `mlb-stats migrate` command

**Migration Files:**
```
src/mlb_stats/db/migrations/
├── 001_initial_schema.sql
├── 002_add_batted_balls.sql
└── 003_add_spin_axis.sql
```

Each migration file contains:
```sql
-- Migration: 002_add_batted_balls
-- Version: 1.1.0
-- Description: Add batted_balls table for Statcast hit data

CREATE TABLE IF NOT EXISTS batted_balls (...);
```

### 3.6 Sample Queries (Design Validation)

These queries validate that the schema is intuitive and queryable:

**Player's batting stats for a date range:**
```sql
SELECT 
    p.fullName,
    SUM(gb.hits) as hits,
    SUM(gb.homeRuns) as hr,
    SUM(gb.strikeOuts) as so,
    SUM(gb.baseOnBalls) as bb
FROM game_batting gb
JOIN players p ON gb.player_id = p.id
JOIN games g ON gb.gamePk = g.gamePk
WHERE g.gameDate BETWEEN '2024-07-01' AND '2024-07-31'
GROUP BY p.id
ORDER BY hits DESC;
```

**Pitcher's average spin rate by pitch type:**
```sql
SELECT 
    type_code,
    type_description,
    ROUND(AVG(spinRate), 0) as avg_spin,
    ROUND(AVG(startSpeed), 1) as avg_velo,
    COUNT(*) as pitch_count
FROM pitches
WHERE pitcher_id = 543243
  AND spinRate IS NOT NULL
GROUP BY type_code
ORDER BY pitch_count DESC;
```

**Exit velocity leaders for a season (min 100 balls in play):**
```sql
SELECT 
    p.fullName,
    ROUND(AVG(bb.launchSpeed), 1) as avg_exit_velo,
    ROUND(MAX(bb.launchSpeed), 1) as max_exit_velo,
    COUNT(*) as balls_in_play
FROM batted_balls bb
JOIN players p ON bb.batter_id = p.id
JOIN games g ON bb.gamePk = g.gamePk
WHERE g.season = 2024 
  AND bb.launchSpeed IS NOT NULL
GROUP BY p.id
HAVING balls_in_play >= 100
ORDER BY avg_exit_velo DESC
LIMIT 20;
```

**Pitch type breakdown for a specific game:**
```sql
SELECT 
    p.fullName as pitcher,
    pit.type_code,
    COUNT(*) as count,
    ROUND(AVG(pit.startSpeed), 1) as avg_velo,
    SUM(pit.isStrike) as strikes,
    SUM(pit.isInPlay) as in_play
FROM pitches pit
JOIN players p ON pit.pitcher_id = p.id
WHERE pit.gamePk = 745927
GROUP BY pit.pitcher_id, pit.type_code
ORDER BY p.fullName, count DESC;
```

**Barrel rate by batter (launch speed >= 98, launch angle 26-30):**
```sql
SELECT 
    p.fullName,
    COUNT(*) as batted_balls,
    SUM(CASE WHEN bb.launchSpeed >= 98 
             AND bb.launchAngle BETWEEN 26 AND 30 
        THEN 1 ELSE 0 END) as barrels,
    ROUND(100.0 * SUM(CASE WHEN bb.launchSpeed >= 98 
                           AND bb.launchAngle BETWEEN 26 AND 30 
                      THEN 1 ELSE 0 END) / COUNT(*), 1) as barrel_pct
FROM batted_balls bb
JOIN players p ON bb.batter_id = p.id
JOIN games g ON bb.gamePk = g.gamePk
WHERE g.season = 2024
GROUP BY p.id
HAVING batted_balls >= 50
ORDER BY barrel_pct DESC
LIMIT 20;
```

**Called strike rate by home plate umpire (no JOIN needed):**
```sql
SELECT 
    g.umpire_HP_name,
    COUNT(*) as pitches_called,
    SUM(CASE WHEN p.call_code = 'C' THEN 1 ELSE 0 END) as called_strikes,
    ROUND(100.0 * SUM(CASE WHEN p.call_code = 'C' THEN 1 ELSE 0 END) / COUNT(*), 1) as called_strike_pct
FROM pitches p
JOIN games g ON p.gamePk = g.gamePk
WHERE p.call_code IN ('B', 'C')  -- Only called balls and strikes
  AND g.season = 2024
GROUP BY g.umpire_HP_id
HAVING pitches_called >= 1000
ORDER BY called_strike_pct DESC;
```

---

## 4. Project Structure

```
mlb-stats-collector/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint + test on push/PR
│       └── release.yml            # Tag-triggered releases
├── src/
│   └── mlb_stats/
│       ├── __init__.py
│       ├── cli.py                 # CLI entry points (Click or argparse)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py          # HTTP client with retry/rate limiting
│       │   ├── endpoints.py       # Endpoint definitions
│       │   └── cache.py           # Response caching logic
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py      # SQLite connection management
│       │   ├── schema.py          # Schema creation/migration
│       │   └── queries.py         # Common query helpers
│       ├── models/
│       │   ├── __init__.py
│       │   ├── game.py            # Game data transformations
│       │   ├── player.py          # Player data transformations
│       │   ├── team.py            # Team data transformations
│       │   ├── boxscore.py        # Boxscore transformations
│       │   └── pitch.py           # Pitch data transformations
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py            # Base collector class
│       │   ├── schedule.py        # Schedule collector
│       │   ├── game.py            # Game data collector
│       │   ├── boxscore.py        # Boxscore collector
│       │   ├── play_by_play.py    # Play-by-play collector
│       │   ├── player.py          # Player info collector
│       │   └── team.py            # Team info collector
│       └── utils/
│           ├── __init__.py
│           ├── logging.py         # Logging configuration
│           ├── dates.py           # Date handling utilities
│           └── metadata.py        # Write metadata (git hash, version, timestamp)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_client.py
│   │   ├── test_models.py
│   │   └── test_transformations.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_api.py            # Live API tests (marked slow)
│   │   └── test_database.py       # Database integration tests
│   └── fixtures/
│       └── *.json                 # Sample API responses
├── docs/
│   ├── DATA_DICTIONARY.md         # Field definitions and sources
│   ├── SCHEMA.md                  # Database schema documentation
│   ├── API_REFERENCE.md           # MLB API endpoint reference
│   └── USAGE.md                   # CLI usage guide
├── cache/                         # JSON response cache (gitignored)
├── data/                          # SQLite databases (gitignored)
├── pyproject.toml                 # Project config and dependencies
├── Makefile                       # Development commands
├── README.md                      # Project overview
├── CHANGELOG.md                   # Version history
├── LICENSE
└── .gitignore
```

---

## 5. Implementation Phases

### Phase 1: Project Foundation
**Goal:** Establish project structure, tooling, database schema, and basic API connectivity.

**Deliverables:**
1. Initialize project with `uv`
2. Create directory structure
3. Set up Makefile with lint/format/test targets
4. Implement basic HTTP client with:
   - Request retries with exponential backoff
   - Rate limiting (configurable delay between requests)
   - Response caching to disk (game data only, not reference data)
   - Proper User-Agent header
5. Implement logging infrastructure
6. Create basic CLI skeleton
7. Set up pytest infrastructure
8. Initialize GitHub Actions CI
9. **Create full database schema (all 11 tables)**
10. Implement schema creation/migration logic

**File Deliverables:**
```
pyproject.toml
Makefile
README.md
CHANGELOG.md
LICENSE
.gitignore
.github/
  workflows/
    ci.yml
src/
  mlb_stats/
    __init__.py                    # Package init with __version__
    cli.py                         # CLI entry point with --version, --help
    api/
      __init__.py
      client.py                    # MLBStatsClient class
      cache.py                     # File-based JSON caching (game data only)
      endpoints.py                 # Endpoint URL constants
    db/
      __init__.py
      connection.py                # get_connection(), init_db()
      schema.py                    # create_tables(), get_schema_version()
      migrations/
        __init__.py
        001_initial_schema.sql     # ALL tables: teams, venues, players, games, etc.
    utils/
      __init__.py
      logging.py                   # configure_logging()
      metadata.py                  # get_write_metadata(), get_git_hash()
tests/
  __init__.py
  conftest.py                      # Shared fixtures
  unit/
    __init__.py
    test_client.py                 # Client retry, rate limiting tests
    test_cache.py                  # Cache read/write tests
    test_metadata.py               # Git hash, version tests
    test_schema.py                 # Schema creation tests
  integration/
    __init__.py
    test_database.py               # Table creation, foreign keys
```

**Acceptance Criteria:**
- [ ] `make install` succeeds on fresh clone
- [ ] `make lint` passes with no errors
- [ ] `make test` passes with >90% coverage on new code
- [ ] `mlb-stats --version` prints version number
- [ ] `mlb-stats --help` shows available commands
- [ ] `mlb-stats init-db` creates database with all 11 tables
- [ ] Schema version stored in `_meta` table
- [ ] Unit test: client retries on HTTP 500
- [ ] Unit test: client respects rate limit delay
- [ ] Unit test: cache writes and reads JSON correctly
- [ ] Unit test: cache skips reference data endpoints
- [ ] Integration test: fetch live data from schedule endpoint
- [ ] Integration test: all foreign key constraints valid

**Tests:**
- Unit tests for HTTP client retry logic
- Unit tests for caching logic (verify reference data not cached)
- Unit tests for schema creation
- Integration test: successfully fetch from schedule endpoint
- Integration test: database schema creation and foreign keys

### Phase 2: Schedule, Games, and Reference Data (Teams/Venues)
**Goal:** Fetch game schedules and metadata, with teams and venues fetched on-demand as encountered.

**Key Principle:** Games drive everything. When we encounter a team_id or venue_id in game data, we fetch and upsert that reference record immediately (no caching for reference data).

**Deliverables:**
1. Build schedule collector (date range based)
2. Build game metadata transformer
3. Build team collector and transformer (called on-demand)
4. Build venue collector and transformer (called on-demand)
5. Implement `sync_team()` and `sync_venue()` helpers that always fetch fresh and upsert
6. Add CLI commands:
   - `mlb-stats sync games --start-date YYYY-MM-DD --end-date YYYY-MM-DD`
   - `mlb-stats sync games --season YYYY`
7. Write data dictionary documentation for teams, venues, games tables

**Data Flow:**
```
sync games --date 2024-07-01
  │
  ├─► Fetch schedule for date → list of gamePks
  │
  └─► For each gamePk:
        ├─► Fetch game feed
        ├─► Extract away_team_id, home_team_id → sync_team() for each
        ├─► Extract venue_id → sync_venue()
        ├─► Transform and upsert game record
        └─► Transform and upsert game_officials records
```

**File Deliverables:**
```
src/mlb_stats/
  models/
    __init__.py
    team.py                        # transform_team()
    venue.py                       # transform_venue()
    game.py                        # transform_game(), transform_official()
  collectors/
    __init__.py
    base.py                        # BaseCollector class
    schedule.py                    # ScheduleCollector
    game.py                        # GameCollector
    team.py                        # TeamCollector (on-demand)
    venue.py                       # VenueCollector (on-demand)
  db/
    queries.py                     # upsert helpers
  utils/
    dates.py                       # parse_date(), date_range(), etc.
docs/
  DATA_DICTIONARY.md               # Begin documenting tables
  SCHEMA.md                        # Schema documentation
tests/
  unit/
    test_models.py                 # Transformation tests
    test_dates.py
    test_game_models.py
  integration/
    test_game_sync.py
  fixtures/
    team_119.json                  # Sample team response
    venue_1.json                   # Sample venue response
    schedule_2024-07-01.json
    game_feed_745927.json
```

**Acceptance Criteria:**
- [ ] `mlb-stats sync games --start-date 2024-07-01 --end-date 2024-07-07` inserts ~100 games
- [ ] `mlb-stats sync games --season 2024` inserts full season (~2,430 regular season games)
- [ ] Teams table populated only with teams encountered in synced games
- [ ] Venues table populated only with venues encountered in synced games
- [ ] Re-running same date range updates `_written_at` timestamps (upsert works)
- [ ] Teams/venues always fetched fresh (not cached)
- [ ] All rows have `_written_at`, `_git_hash`, `_version` populated
- [ ] Home plate umpire populated on games table
- [ ] Game officials stored in game_officials table
- [ ] Weather data captured when available
- [ ] Doubleheaders correctly marked with gameNumber 1 and 2
- [ ] DATA_DICTIONARY.md documents teams, venues, games tables

**Tests:**
- Unit tests for team/venue/game transformations
- Unit tests for schedule parsing
- Unit tests for date range handling
- Integration test: sync a week of games
- Verify teams/venues created as side effect of game sync
- Verify idempotent re-syncs

### Phase 3: Box Scores and Player Reference Data
**Goal:** Collect per-game batting and pitching statistics, with players fetched on-demand as encountered.

**Key Principle:** Players are fetched when encountered in box score data. Every player in a box score triggers a fresh fetch and upsert of their player record.

**Deliverables:**
1. Build boxscore collector
2. Build batting stats transformer
3. Build pitching stats transformer
4. Build player collector and transformer (called on-demand)
5. Implement `sync_player()` helper that always fetches fresh and upserts
6. Add CLI commands:
   - `mlb-stats sync boxscores <gamePk>`
   - `mlb-stats sync boxscores --start-date YYYY-MM-DD --end-date YYYY-MM-DD`
7. Handle edge cases:
   - Postponed/suspended games
   - Missing data fields
8. Update data dictionary with batting, pitching, players tables

**Data Flow:**
```
sync boxscores --date 2024-07-01
  │
  ├─► Get list of gamePks for date (from games table or schedule API)
  │
  └─► For each gamePk:
        ├─► Fetch boxscore
        ├─► For each player in batting/pitching:
        │     └─► sync_player(player_id)  # Always fresh fetch
        ├─► Transform and upsert game_batting records
        └─► Transform and upsert game_pitching records
```

**File Deliverables:**
```
src/mlb_stats/
  models/
    player.py                      # transform_player()
    boxscore.py                    # transform_batting(), transform_pitching()
  collectors/
    player.py                      # PlayerCollector (on-demand)
    boxscore.py                    # BoxscoreCollector
tests/
  unit/
    test_player_models.py
    test_boxscore_models.py
  integration/
    test_boxscore_sync.py
  fixtures/
    player_660271.json             # Sample player response
    boxscore_745927.json
```

**Acceptance Criteria:**
- [ ] `mlb-stats sync boxscores 745927` inserts batting and pitching records for all players
- [ ] Players table populated only with players encountered in synced boxscores
- [ ] Players always fetched fresh (not cached), so `lastPlayedDate` stays current
- [ ] Batting order captured correctly (100, 200, ... 900 for starters)
- [ ] Starting pitcher flagged with isStartingPitcher = 1
- [ ] Win/loss/save attribution in pitching `note` field
- [ ] Postponed games handled gracefully (skip or mark status)
- [ ] Sum of player runs equals game score (data integrity check)
- [ ] DATA_DICTIONARY.md updated with players, game_batting, game_pitching

**Tests:**
- Unit tests for player transformations
- Unit tests for batting stat transformations
- Unit tests for pitching stat transformations
- Integration test: sync boxscores for a date
- Verify players created as side effect of boxscore sync
- Verify stat totals match game scores

### Phase 4: Pitch-Level and Statcast Data
**Goal:** Collect detailed pitch-by-pitch data including Statcast metrics and batted ball data.

**Deliverables:**
1. Build play-by-play collector
2. Build pitch data transformer (including Statcast fields)
3. Build batted ball transformer
4. Build at-bat summary transformer
5. Add CLI commands:
   - `mlb-stats sync pitches <gamePk>`
   - `mlb-stats sync pitches --start-date YYYY-MM-DD --end-date YYYY-MM-DD`
6. Handle edge cases:
   - Incomplete play data
   - Non-pitch events (pickoffs, balks, etc.)
   - Missing Statcast data (pre-2015 games, tracking failures)
   - Estimated vs measured batted ball data
7. Update data dictionary with pitches, at_bats, batted_balls tables

**File Deliverables:**
```
src/mlb_stats/
  models/
    pitch.py                       # transform_pitch(), transform_batted_ball()
    at_bat.py                      # transform_at_bat()
  collectors/
    play_by_play.py                # PlayByPlayCollector
tests/
  unit/
    test_pitch_models.py
    test_at_bat_models.py
  integration/
    test_pitch_sync.py
  fixtures/
    play_by_play_745927.json
```

**Acceptance Criteria:**
- [ ] `mlb-stats sync pitches 745927` inserts all pitches for the game
- [ ] Pitch count in pitches table matches boxscore numberOfPitches
- [ ] Statcast fields (spinRate, extension, etc.) populated for 2017+ games
- [ ] Statcast fields NULL for pre-2015 games (no errors)
- [ ] Batted balls table populated for all balls in play
- [ ] At-bats table has one row per plate appearance
- [ ] Foreign key from batted_balls to pitches works
- [ ] Non-pitch events (pickoffs) excluded from pitches table
- [ ] DATA_DICTIONARY.md updated with pitches, at_bats, batted_balls

**Tests:**
- Unit tests for pitch data transformations
- Unit tests for Statcast field extraction
- Unit tests for batted ball transformations
- Integration test: sync pitches for a game
- Verify pitch counts match boxscore totals
- Test handling of missing Statcast fields

### Phase 5: CLI Polish and Documentation
**Goal:** Create production-ready CLI and comprehensive documentation.

**Deliverables:**
1. Add composite CLI commands:
   - `mlb-stats sync all --start-date --end-date`
   - `mlb-stats backfill --season YYYY`
2. Add query/export commands:
   - `mlb-stats query "SQL"`
   - `mlb-stats export --table TABLE --format csv`
3. Add status/info commands:
   - `mlb-stats status` (show sync state)
   - `mlb-stats info <gamePk>` (show game summary)
4. Complete all documentation:
   - DATA_DICTIONARY.md
   - SCHEMA.md  
   - USAGE.md
   - API_REFERENCE.md
5. Add progress bars for long operations
6. Add `--dry-run` flag for preview mode

**File Deliverables:**
```
src/mlb_stats/
  cli.py                           # Updated with all commands
  commands/
    __init__.py
    sync.py                        # sync subcommands
    query.py                       # query, export commands
    info.py                        # status, info commands
  utils/
    progress.py                    # Progress bar wrapper
    export.py                      # CSV/JSON export utilities
docs/
  DATA_DICTIONARY.md               # Complete field documentation
  SCHEMA.md                        # Complete schema documentation
  USAGE.md                         # CLI usage guide with examples
  API_REFERENCE.md                 # MLB API endpoint reference
tests/
  integration/
    test_full_sync.py              # End-to-end tests
    test_cli.py                    # CLI command tests
```

**Acceptance Criteria:**
- [ ] `mlb-stats sync all --start-date 2024-07-01 --end-date 2024-07-01` syncs games, boxscores, and pitches
- [ ] `mlb-stats backfill --season 2024` runs complete season sync
- [ ] `mlb-stats query "SELECT COUNT(*) FROM games"` returns result
- [ ] `mlb-stats export --table pitches --format csv > pitches.csv` produces valid CSV
- [ ] `mlb-stats status` shows last sync date, record counts
- [ ] Progress bars display during long operations
- [ ] `--dry-run` shows what would be synced without writing
- [ ] `--quiet` suppresses progress output
- [ ] `-v` / `-vv` increase logging verbosity
- [ ] All documentation complete and accurate
- [ ] README.md has quick-start guide

**Tests:**
- End-to-end test: full season backfill
- Test all CLI commands
- Test export functionality

---

## 6. Technical Requirements

### 6.1 Configuration Management

**Configuration Priority (highest to lowest):**
1. CLI flags (e.g., `--db-path`, `--cache-dir`, `--request-delay`)
2. Environment variables (e.g., `MLB_STATS_DB_PATH`, `MLB_STATS_CACHE_DIR`)
3. Config file (`~/.config/mlb-stats/config.toml` or `./mlb-stats.toml`)
4. Built-in defaults

**Default Values:**
```toml
# Default configuration (built into code)
[database]
path = "./data/mlb_stats.db"

[cache]
dir = "./cache"
enabled = true

[api]
request_delay = 0.5      # seconds between requests
max_retries = 3
timeout = 30             # seconds

[output]
verbosity = 0            # 0=WARNING, 1=INFO, 2=DEBUG
progress_bars = true
```

**Environment Variable Mapping:**
| Variable | Config Key | CLI Flag |
|----------|------------|----------|
| `MLB_STATS_DB_PATH` | database.path | `--db-path` |
| `MLB_STATS_CACHE_DIR` | cache.dir | `--cache-dir` |
| `MLB_STATS_NO_CACHE` | cache.enabled | `--no-cache` |
| `MLB_STATS_REQUEST_DELAY` | api.request_delay | `--request-delay` |
| `MLB_STATS_VERBOSITY` | output.verbosity | `-v`, `-vv` |

### 6.2 Error Handling Strategy

**Partial Failure Behavior:**
- **Atomic per-record**: Each game/player is its own transaction
- **Continue on failure**: Log error and continue to next record (don't abort entire sync)
- **Summary at end**: Report "Synced 94/100 games. 6 failures. See log for details."
- **Exit codes**: 0 = success, 1 = partial failure, 2 = total failure

**Error Recovery:**
```bash
# Retry only previously failed records
mlb-stats sync boxscores --start-date 2024-07-01 --end-date 2024-07-07 --retry-failed

# Strict mode: abort on first error (useful for CI)
mlb-stats sync boxscores --start-date 2024-07-01 --end-date 2024-07-07 --strict
```

**Error Logging:**
```python
# All errors logged with full context
logger.error(
    "Failed to sync boxscore",
    extra={
        "gamePk": 745927,
        "error_type": "HTTPError",
        "status_code": 500,
        "attempt": 3,
    }
)
```

**Sync Log Table:**
The `sync_log` table tracks all sync operations for debugging and recovery:
```sql
-- Find failed syncs
SELECT * FROM sync_log WHERE status = 'failed' ORDER BY started_at DESC;

-- Find games that failed
SELECT gamePk FROM sync_log 
WHERE sync_type = 'boxscore' AND status = 'failed';
```

### 6.3 CLI Output Standards

**Verbosity Levels:**
| Flag | Level | Output |
|------|-------|--------|
| (none) | WARNING | Progress bar + summary only |
| `-v` | INFO | Which games/players being processed |
| `-vv` | DEBUG | API calls, SQL statements, timing |
| `--quiet` | ERROR | Summary only, no progress bar |
| `--json` | - | Output results as JSON (for scripting) |

**Log Levels (use correctly!):**
| Level | When to Use | Example |
|-------|-------------|---------|
| `DEBUG` | Detailed diagnostic info for debugging. Not shown in normal operation. | Row-by-row processing details, SQL queries being executed |
| `INFO` | Confirmation that things are working as expected. Progress updates. | "Syncing game 745927...", "Inserted 47 pitches" |
| `WARNING` | Something unexpected but not an error. Program continues. | "Player ID 999999 not found, skipping row" |
| `ERROR` | A specific operation failed but program can continue. | "Failed to sync game 745927, will retry", "API returned 500" |
| `CRITICAL` | Program cannot continue. About to crash. | "Database file corrupted", "Cannot connect to database" |

**Progress Bar Format:**
```
Syncing boxscores: 47/100 [████████████░░░░░░░░░░░░] 47% 00:02:34 remaining
```

**Summary Output:**
```
Sync complete.
  Games:     100 synced, 0 failed
  Boxscores: 94 synced, 6 failed
  Duration:  5m 23s

Failed records logged to: ./logs/sync_2024-07-01.log
```

### 6.4 Python Version
- Minimum: Python 3.10
- Target: Python 3.11+

### 6.2 Dependencies

**Required (keep minimal):**
```toml
[project]
dependencies = [
    "requests>=2.28.0",    # HTTP client (ubiquitous, well-maintained)
    "click>=8.0.0",        # CLI framework (or argparse from stdlib)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "autoflake>=2.0.0",
    "responses>=0.23.0",   # Mock HTTP responses in tests
]
```

**Explicitly NOT using:**
- pandas (not needed for collection; users can query with whatever they want)
- SQLAlchemy (overkill for SQLite; use raw sqlite3)
- asyncio/aiohttp (unnecessary complexity for rate-limited API)

### 6.3 Makefile Targets

```makefile
.PHONY: install lint reformat test test-unit test-integration clean

install:  ## Install dependencies
	uv sync

lint:  ## Check for linter issues
	isort --check --profile black src/ tests/ && echo "No import format issues!" || exit 1
	black --check -t py310 src/ tests/ && echo "No linting issues!" || exit 1
	autoflake -r -c --exclude=./build/* src/ tests/ > /dev/null && echo "No unused imports!" || exit 1

reformat:  ## Fix linter issues
	isort --profile black src/ tests/
	black -t py310 src/ tests/
	autoflake -r -i --exclude=./build/* src/ tests/

test:  ## Run all tests
	pytest tests/ -v

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v

test-integration:  ## Run integration tests
	pytest tests/integration/ -v -m "not slow"

test-slow:  ## Run slow integration tests (live API)
	pytest tests/integration/ -v -m "slow"

coverage:  ## Run tests with coverage
	pytest tests/ --cov=mlb_stats --cov-report=html

clean:  ## Clean up build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
```

### 6.4 Logging Configuration

```python
import logging

def configure_logging(verbosity: int = 0) -> None:
    """Configure logging based on verbosity level.
    
    Parameters
    ----------
    verbosity : int
        0 = WARNING, 1 = INFO, 2+ = DEBUG
    """
    level = {
        0: logging.WARNING,
        1: logging.INFO,
    }.get(verbosity, logging.DEBUG)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
```

### 6.5 API Client Pattern

```python
import time
import logging
from typing import Any
import requests

logger = logging.getLogger(__name__)

class MLBStatsClient:
    """HTTP client for MLB Stats API with retry and rate limiting.
    
    Parameters
    ----------
    base_url : str
        API base URL
    request_delay : float
        Seconds to wait between requests
    max_retries : int
        Maximum retry attempts for failed requests
    """
    
    BASE_URL = "https://statsapi.mlb.com/api/"
    
    def __init__(
        self,
        request_delay: float = 0.5,
        max_retries: int = 3,
        cache_dir: str | None = None,
    ) -> None:
        self.request_delay = request_delay
        self.max_retries = max_retries
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "mlb-stats-collector/1.0 (research project)"
        })
        self._last_request_time = 0.0
    
    def _wait_for_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
    
    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        """Make GET request with retry logic.
        
        Parameters
        ----------
        endpoint : str
            API endpoint (e.g., 'v1/schedule')
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
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(self.max_retries):
            self._wait_for_rate_limit()
            
            try:
                logger.debug(f"GET {url} params={params}")
                response = self.session.get(url, params=params, timeout=30)
                self._last_request_time = time.time()
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                wait_time = 2 ** attempt
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Waiting {wait_time}s before retry."
                )
                time.sleep(wait_time)
        
        # Final attempt
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
```

### 6.6 Write Metadata Pattern

Every database write must include provenance metadata. Use a centralized helper:

```python
import subprocess
from datetime import datetime, timezone
from functools import lru_cache

# Version should match pyproject.toml
__version__ = "1.0.0"


@lru_cache(maxsize=1)
def get_git_hash() -> str:
    """Get current git commit hash.
    
    Returns
    -------
    str
        Short git hash, or 'unknown' if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return "unknown"


def get_write_metadata() -> dict[str, str]:
    """Get metadata dict for database writes.
    
    Returns
    -------
    dict
        Contains _written_at, _git_hash, _version keys
        
    Examples
    --------
    >>> row_data = {"id": 123, "name": "Test"}
    >>> row_data.update(get_write_metadata())
    >>> # row_data now includes _written_at, _git_hash, _version
    """
    return {
        "_written_at": datetime.now(timezone.utc).isoformat(),
        "_git_hash": get_git_hash(),
        "_version": __version__,
    }
```

**Usage in collectors:**
```python
def insert_team(conn: sqlite3.Connection, team_data: dict) -> None:
    """Insert team record with write metadata."""
    team_data.update(get_write_metadata())
    
    columns = ", ".join(team_data.keys())
    placeholders = ", ".join("?" * len(team_data))
    
    conn.execute(
        f"INSERT OR REPLACE INTO teams ({columns}) VALUES ({placeholders})",
        list(team_data.values())
    )
```

---

## 7. Testing Strategy

### 7.1 Test Categories

**Unit Tests:**
- Data transformation functions
- Date parsing and handling
- SQL query builders
- Cache key generation
- Error handling logic

**Integration Tests:**
- Database schema creation
- Insert/update operations
- Foreign key constraint enforcement
- Full collector workflows with mocked HTTP

**Live API Tests (marked `@pytest.mark.slow`):**
- Actual API endpoint connectivity
- Response schema validation
- Data freshness verification

### 7.2 Fixtures

Store sample API responses in `tests/fixtures/`:
- `schedule_2024-07-01.json`
- `game_feed_745927.json`
- `boxscore_745927.json`
- `play_by_play_745927.json`
- `player_660271.json`
- `team_119.json`

### 7.3 Test Database

```python
# tests/conftest.py
import pytest
import sqlite3
from pathlib import Path

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    # Create schema
    yield conn
    conn.close()

@pytest.fixture  
def sample_schedule():
    """Load sample schedule response."""
    fixture_path = Path(__file__).parent / "fixtures" / "schedule_2024-07-01.json"
    return json.loads(fixture_path.read_text())
```

---

## 8. Documentation Requirements

### 8.1 DATA_DICTIONARY.md

For each table, document:
- Table purpose
- All columns with:
  - Data type
  - Description
  - Source (which API endpoint and JSON path)
  - Nullable?
  - Example value

Example format:
```markdown
## game_batting

Per-player batting statistics for each game.

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| gamePk | INTEGER | No | liveData.boxscore | Unique game identifier |
| player_id | INTEGER | No | liveData.boxscore.teams.*.players.*.person.id | MLB player ID |
| hits | INTEGER | Yes | liveData.boxscore.teams.*.players.*.stats.batting.hits | Total hits |
```

### 8.2 SCHEMA.md

- Full CREATE TABLE statements
- Index definitions and rationale
- Foreign key relationships (diagram recommended)
- Migration notes for schema changes

### 8.3 USAGE.md

- Installation instructions
- Quick start guide
- All CLI commands with examples
- Common workflows:
  - Initial setup
  - Backfilling a season
  - Daily updates
  - Querying data

---

## 9. CI/CD and Version Control

### 9.1 Git Conventions

**Branching:**
- `main` - stable, release-ready code
- `develop` - integration branch (optional)
- `feature/description` - new features
- `bugfix/description` - bug fixes
- `hotfix/description` - urgent production fixes

**Commit Messages:**
```
type: short description

Longer explanation if needed.

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 9.2 Semantic Versioning

Format: `MAJOR.MINOR.PATCH`

- MAJOR: Breaking changes to CLI interface or database schema
- MINOR: New features, new data fields
- PATCH: Bug fixes, documentation updates

### 9.3 GitHub Actions

**.github/workflows/ci.yml:**
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: make lint

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: uv sync --dev
      - run: make test
      - run: make coverage
      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'
```

**.github/workflows/release.yml:**
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv build
      - uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

---

## Appendix A: Game Type Codes

| Code | Description |
|------|-------------|
| R | Regular Season |
| F | Wild Card Game |
| D | Division Series |
| L | League Championship Series |
| W | World Series |
| S | Spring Training |
| E | Exhibition |
| A | All-Star Game |

## Appendix B: Position Codes

| Code | Position |
|------|----------|
| 1 | Pitcher |
| 2 | Catcher |
| 3 | First Base |
| 4 | Second Base |
| 5 | Third Base |
| 6 | Shortstop |
| 7 | Left Field |
| 8 | Center Field |
| 9 | Right Field |
| 10 | Designated Hitter |
| Y | Two-Way Player |

## Appendix C: Common Pitch Type Codes

| Code | Description |
|------|-------------|
| FF | Four-Seam Fastball |
| FT | Two-Seam Fastball |
| FC | Cutter |
| SI | Sinker |
| SL | Slider |
| CU | Curveball |
| KC | Knuckle Curve |
| CH | Changeup |
| FS | Splitter |
| KN | Knuckleball |
| EP | Eephus |
| SC | Screwball |
| SW | Sweeper |
| ST | Sweeping Curve |
| SV | Slurve |

## Appendix D: Pitch Result Codes

| Code | Description |
|------|-------------|
| B | Ball |
| C | Called Strike |
| S | Swinging Strike |
| F | Foul |
| X | In Play |
| T | Foul Tip |
| L | Foul Bunt |
| I | Intentional Ball |
| P | Pitchout |
| H | Hit By Pitch |
| M | Missed Bunt |
| O | Foul Tip Out |
| Q | Swinging Pitchout |
| R | Foul Pitchout |
| V | Ball In Dirt |
| W | Swinging Strike (Blocked) |
| Z | In Play, Runs |

## Appendix E: Batted Ball Trajectory Codes

| Code | Description |
|------|-------------|
| fly_ball | Fly Ball |
| ground_ball | Ground Ball |
| line_drive | Line Drive |
| popup | Pop Up |
| bunt_grounder | Bunt Ground Ball |
| bunt_popup | Bunt Pop Up |
| bunt_line_drive | Bunt Line Drive |

## Appendix F: Statcast Data Availability

| Season | Data Available |
|--------|----------------|
| 2008-2014 | PITCHf/x only (velocity, location, movement) |
| 2015-2016 | Statcast introduced (exit velo, launch angle added) |
| 2017+ | Full Statcast (spin rate standardized, extension added) |
| 2020+ | Enhanced tracking, improved pitch classification |
| 2024+ | Bat tracking data (bat speed, swing length) |

**Note:** Pre-2017 velocity readings were measured at 50 feet from home plate. From 2017 onwards, velocity is measured at release point, resulting in slightly higher readings for the same pitches.

## Appendix G: Statcast Metric Definitions

### Pitch Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| startSpeed | mph | Velocity at release point |
| endSpeed | mph | Velocity at home plate |
| spinRate | RPM | Revolutions per minute at release |
| spinDirection | degrees | Spin axis (180° = pure backspin fastball) |
| extension | feet | Distance in front of rubber at release |
| plateTime | seconds | Time from release to crossing the plate |
| pfxX | inches | Horizontal movement vs. spinless pitch |
| pfxZ | inches | Vertical movement vs. spinless pitch (gravity-adjusted) |
| breakAngle | degrees | Angle of total break |
| breakLength | inches | Total break distance |

### Batted Ball Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| launchSpeed | mph | Exit velocity off the bat |
| launchAngle | degrees | Vertical angle of batted ball (-90 to 90) |
| totalDistance | feet | Projected or actual distance traveled |
| hardness | category | soft (<70 mph), medium (70-95 mph), hard (>95 mph) |

### Strike Zone Reference

Zone numbers 1-9 represent the strike zone in a 3x3 grid:
```
     Inside    Middle   Outside
     ------    ------   -------
Top    1         2         3
Mid    4         5         6
Bot    7         8         9
```

Zones 11-14 are outside the strike zone:
- 11: Above zone
- 12: Below zone  
- 13: Inside (to batter)
- 14: Outside (from batter)
