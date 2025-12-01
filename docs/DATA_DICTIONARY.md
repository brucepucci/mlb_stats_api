# Data Dictionary

Field definitions and sources for MLB Stats Collector database tables.

## Metadata Columns

All tables include the following metadata columns:

| Column | Type | Description |
|--------|------|-------------|
| `_fetched_at` | TEXT | ISO8601 UTC timestamp when data was fetched from API |
| `_written_at` | TEXT | ISO8601 UTC timestamp when row was written to database |
| `_git_hash` | TEXT | Git commit hash of code that wrote the row |
| `_version` | TEXT | Semantic version of the application |

---

## teams

Reference table for team information. Always fetched fresh (never cached) to keep mutable fields current.

**Source:** `/v1/teams/{teamId}`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | `teams[0].id` | MLB team ID (primary key) |
| name | TEXT | No | `teams[0].name` | Full team name (e.g., "Los Angeles Dodgers") |
| teamCode | TEXT | Yes | `teams[0].teamCode` | Short code (e.g., "lan") |
| fileCode | TEXT | Yes | `teams[0].fileCode` | File code (e.g., "la") |
| abbreviation | TEXT | Yes | `teams[0].abbreviation` | Standard abbreviation (e.g., "LAD") |
| teamName | TEXT | Yes | `teams[0].teamName` | Team name only (e.g., "Dodgers") |
| locationName | TEXT | Yes | `teams[0].locationName` | City/location (e.g., "Los Angeles") |
| firstYearOfPlay | TEXT | Yes | `teams[0].firstYearOfPlay` | Year franchise started |
| league_id | INTEGER | Yes | `teams[0].league.id` | League ID |
| league_name | TEXT | Yes | `teams[0].league.name` | League name (e.g., "National League") |
| division_id | INTEGER | Yes | `teams[0].division.id` | Division ID |
| division_name | TEXT | Yes | `teams[0].division.name` | Division name (e.g., "National League West") |
| venue_id | INTEGER | Yes | `teams[0].venue.id` | Home venue ID (FK to venues) |
| active | INTEGER | Yes | `teams[0].active` | 1 if active, 0 if inactive |

**Foreign Keys:**
- `venue_id` → `venues(id)`

---

## venues

Reference table for venue/stadium information. Always fetched fresh (never cached).

**Source:** `/v1/venues/{venueId}`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | `venues[0].id` | MLB venue ID (primary key) |
| name | TEXT | No | `venues[0].name` | Venue name (e.g., "Dodger Stadium") |
| city | TEXT | Yes | `venues[0].location.city` | City |
| state | TEXT | Yes | `venues[0].location.state` | State |
| stateAbbrev | TEXT | Yes | `venues[0].location.stateAbbrev` | State abbreviation |
| country | TEXT | Yes | `venues[0].location.country` | Country |
| latitude | REAL | Yes | `venues[0].location.defaultCoordinates.latitude` | Latitude |
| longitude | REAL | Yes | `venues[0].location.defaultCoordinates.longitude` | Longitude |
| elevation | REAL | Yes | `venues[0].location.elevation` | Elevation in feet |
| timezone | TEXT | Yes | `venues[0].timeZone.id` | Timezone ID |

---

## games

Core game information table. Cached only when game state is "Final".

**Source:** `/v1.1/game/{gamePk}/feed/live`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| gamePk | INTEGER | No | `gamePk` | Unique game identifier (primary key) |
| season | INTEGER | No | `gameData.game.season` | Season year |
| gameType | TEXT | No | `gameData.game.type` | Game type code (R=Regular, F=Wild Card, D=Division Series, L=League Championship, W=World Series, S=Spring Training, E=Exhibition, A=All-Star) |
| gameDate | TEXT | No | `gameData.datetime.officialDate` | Date (YYYY-MM-DD) |
| gameDateTime | TEXT | Yes | `gameData.datetime.dateTime` | Full ISO8601 UTC timestamp |
| officialDate | TEXT | Yes | `gameData.datetime.officialDate` | MLB official game date |
| away_team_id | INTEGER | No | `gameData.teams.away.id` | Away team ID (FK to teams) |
| home_team_id | INTEGER | No | `gameData.teams.home.id` | Home team ID (FK to teams) |
| away_score | INTEGER | Yes | `liveData.linescore.teams.away.runs` | Away team runs |
| home_score | INTEGER | Yes | `liveData.linescore.teams.home.runs` | Home team runs |
| abstractGameState | TEXT | Yes | `gameData.status.abstractGameState` | State: Final, Live, Preview |
| detailedState | TEXT | Yes | `gameData.status.detailedState` | Detailed state (e.g., "Final", "In Progress") |
| statusCode | TEXT | Yes | `gameData.status.statusCode` | Status code |
| venue_id | INTEGER | Yes | `gameData.venue.id` | Venue ID (FK to venues) |
| venue_name | TEXT | Yes | `gameData.venue.name` | Venue name (denormalized for convenience) |
| dayNight | TEXT | Yes | `gameData.datetime.dayNight` | "day" or "night" |
| scheduledInnings | INTEGER | Yes | `gameData.game.scheduledInnings` | Scheduled innings (usually 9) |
| inningCount | INTEGER | Yes | `liveData.linescore.currentInning` | Actual innings played |
| weather_condition | TEXT | Yes | `gameData.weather.condition` | Weather condition (e.g., "Clear") |
| weather_temp | TEXT | Yes | `gameData.weather.temp` | Temperature (e.g., "72") |
| weather_wind | TEXT | Yes | `gameData.weather.wind` | Wind description |
| attendance | INTEGER | Yes | `liveData.boxscore.info[label=Att].value` | Attendance count |
| firstPitch | TEXT | Yes | `gameData.datetime.firstPitch` | First pitch time (ISO8601 UTC) |
| gameEndDateTime | TEXT | Yes | `gameData.datetime.gameEndDateTime` | Game end time (ISO8601 UTC) |
| doubleHeader | TEXT | Yes | `gameData.game.doubleHeader` | "Y", "N", or "S" (split) |
| gameNumber | INTEGER | Yes | `gameData.game.gameNumber` | 1 or 2 for doubleheaders |
| seriesDescription | TEXT | Yes | `gameData.game.seriesDescription` | Series description |
| seriesGameNumber | INTEGER | Yes | `gameData.game.seriesGameNumber` | Game number in series |
| gamesInSeries | INTEGER | Yes | `gameData.game.gamesInSeries` | Total games in series |
| umpire_HP_id | INTEGER | Yes | `liveData.boxscore.officials[type=Home Plate].official.id` | Home plate umpire ID |
| umpire_HP_name | TEXT | Yes | `liveData.boxscore.officials[type=Home Plate].official.fullName` | Home plate umpire name |

**Foreign Keys:**
- `away_team_id` → `teams(id)`
- `home_team_id` → `teams(id)`
- `venue_id` → `venues(id)`

**Indices:**
- `idx_games_date` on `gameDate`
- `idx_games_season` on `season`
- `idx_games_away_team` on `away_team_id`
- `idx_games_home_team` on `home_team_id`

---

## game_officials

Umpires and officials for each game.

**Source:** `/v1.1/game/{gamePk}/feed/live` → `liveData.boxscore.officials`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | auto | Auto-increment primary key |
| gamePk | INTEGER | No | - | Game ID (FK to games) |
| official_id | INTEGER | Yes | `officials[].official.id` | Official MLB ID |
| official_fullName | TEXT | Yes | `officials[].official.fullName` | Official full name |
| officialType | TEXT | Yes | `officials[].officialType` | Position type (e.g., "Home Plate", "First Base") |

**Foreign Keys:**
- `gamePk` → `games(gamePk)`

**Unique Constraint:**
- `(gamePk, officialType)` - One official per position per game

**Indices:**
- `idx_game_officials_gamepk` on `gamePk`

---

## Game Type Codes

| Code | Description |
|------|-------------|
| R | Regular Season |
| F | Wild Card |
| D | Division Series |
| L | League Championship Series |
| W | World Series |
| S | Spring Training |
| E | Exhibition |
| A | All-Star Game |

---

## Example Queries

### Find all games for a team in a season
```sql
SELECT gamePk, gameDate, away_score, home_score
FROM games
WHERE (home_team_id = 119 OR away_team_id = 119)
  AND season = 2024
ORDER BY gameDate;
```

### Get game with team and venue names
```sql
SELECT
    g.gamePk,
    g.gameDate,
    away.name AS away_team,
    home.name AS home_team,
    g.away_score,
    g.home_score,
    v.name AS venue
FROM games g
JOIN teams away ON g.away_team_id = away.id
JOIN teams home ON g.home_team_id = home.id
LEFT JOIN venues v ON g.venue_id = v.id
WHERE g.gamePk = 745927;
```

### List all officials for a game
```sql
SELECT official_fullName, officialType
FROM game_officials
WHERE gamePk = 745927
ORDER BY officialType;
```
