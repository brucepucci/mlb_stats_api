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
| active | INTEGER | Yes | `teams[0].active` | 1 if active, 0 if inactive |

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
| venue_name | TEXT | Yes | `gameData.venue.name` | Venue name (denormalized) |
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

## players

Reference table for player information. Always fetched fresh (never cached) to keep mutable fields current.

**Source:** `/v1/people/{personId}`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | `people[0].id` | MLB person ID (primary key) |
| fullName | TEXT | No | `people[0].fullName` | Full name (e.g., "Shohei Ohtani") |
| firstName | TEXT | Yes | `people[0].firstName` | First name |
| lastName | TEXT | Yes | `people[0].lastName` | Last name |
| useName | TEXT | Yes | `people[0].useName` | Preferred name |
| middleName | TEXT | Yes | `people[0].middleName` | Middle name |
| boxscoreName | TEXT | Yes | `people[0].boxscoreName` | Boxscore format (e.g., "Ohtani, S") |
| nickName | TEXT | Yes | `people[0].nickName` | Nickname |
| primaryNumber | TEXT | Yes | `people[0].primaryNumber` | Jersey number |
| birthDate | TEXT | Yes | `people[0].birthDate` | Birth date (YYYY-MM-DD) |
| birthCity | TEXT | Yes | `people[0].birthCity` | Birth city |
| birthStateProvince | TEXT | Yes | `people[0].birthStateProvince` | Birth state/province |
| birthCountry | TEXT | Yes | `people[0].birthCountry` | Birth country |
| deathDate | TEXT | Yes | `people[0].deathDate` | Death date (YYYY-MM-DD) |
| deathCity | TEXT | Yes | `people[0].deathCity` | Death city |
| deathStateProvince | TEXT | Yes | `people[0].deathStateProvince` | Death state/province |
| deathCountry | TEXT | Yes | `people[0].deathCountry` | Death country |
| height | TEXT | Yes | `people[0].height` | Height (e.g., "6' 4\"") |
| weight | INTEGER | Yes | `people[0].weight` | Weight in pounds |
| primaryPosition_code | TEXT | Yes | `people[0].primaryPosition.code` | Position code |
| primaryPosition_name | TEXT | Yes | `people[0].primaryPosition.name` | Position name |
| primaryPosition_type | TEXT | Yes | `people[0].primaryPosition.type` | Position type |
| primaryPosition_abbreviation | TEXT | Yes | `people[0].primaryPosition.abbreviation` | Position abbreviation |
| batSide_code | TEXT | Yes | `people[0].batSide.code` | Batting side (L, R, S) |
| batSide_description | TEXT | Yes | `people[0].batSide.description` | Batting side description |
| pitchHand_code | TEXT | Yes | `people[0].pitchHand.code` | Throwing hand (L, R, S) |
| pitchHand_description | TEXT | Yes | `people[0].pitchHand.description` | Throwing hand description |
| draftYear | INTEGER | Yes | `people[0].draftYear` | Year drafted |
| mlbDebutDate | TEXT | Yes | `people[0].mlbDebutDate` | MLB debut date |
| lastPlayedDate | TEXT | Yes | `people[0].lastPlayedDate` | Last game played date |
| active | INTEGER | Yes | `people[0].active` | 1 if active, 0 if inactive |
| currentTeam_id | INTEGER | Yes | `people[0].currentTeam.id` | Current team ID (FK to teams) |

**Foreign Keys:**
- `currentTeam_id` → `teams(id)`

---

## game_batting

Per-player batting statistics for each game.

**Source:** `/v1/game/{gamePk}/boxscore` → `teams.{away,home}.players.*.stats.batting`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | auto | Auto-increment primary key |
| gamePk | INTEGER | No | - | Game ID (FK to games) |
| player_id | INTEGER | No | `players.*.person.id` | Player ID (FK to players) |
| team_id | INTEGER | No | `teams.{side}.team.id` | Team ID (FK to teams) |
| battingOrder | INTEGER | Yes | `players.*.battingOrder` | Batting order (100=leadoff, 200=2nd, etc.) |
| position_code | TEXT | Yes | `players.*.position.code` | Position code |
| position_name | TEXT | Yes | `players.*.position.name` | Position name |
| position_abbreviation | TEXT | Yes | `players.*.position.abbreviation` | Position abbreviation |
| gamesPlayed | INTEGER | Yes | `stats.batting.gamesPlayed` | Games played (always 1) |
| flyOuts | INTEGER | Yes | `stats.batting.flyOuts` | Fly outs |
| groundOuts | INTEGER | Yes | `stats.batting.groundOuts` | Ground outs |
| runs | INTEGER | Yes | `stats.batting.runs` | Runs scored |
| doubles | INTEGER | Yes | `stats.batting.doubles` | Doubles |
| triples | INTEGER | Yes | `stats.batting.triples` | Triples |
| homeRuns | INTEGER | Yes | `stats.batting.homeRuns` | Home runs |
| strikeOuts | INTEGER | Yes | `stats.batting.strikeOuts` | Strikeouts |
| baseOnBalls | INTEGER | Yes | `stats.batting.baseOnBalls` | Walks |
| intentionalWalks | INTEGER | Yes | `stats.batting.intentionalWalks` | Intentional walks |
| hits | INTEGER | Yes | `stats.batting.hits` | Hits |
| hitByPitch | INTEGER | Yes | `stats.batting.hitByPitch` | Hit by pitch |
| atBats | INTEGER | Yes | `stats.batting.atBats` | At bats |
| caughtStealing | INTEGER | Yes | `stats.batting.caughtStealing` | Caught stealing |
| stolenBases | INTEGER | Yes | `stats.batting.stolenBases` | Stolen bases |
| groundIntoDoublePlay | INTEGER | Yes | `stats.batting.groundIntoDoublePlay` | GIDP |
| groundIntoTriplePlay | INTEGER | Yes | `stats.batting.groundIntoTriplePlay` | GITP |
| plateAppearances | INTEGER | Yes | `stats.batting.plateAppearances` | Plate appearances |
| totalBases | INTEGER | Yes | `stats.batting.totalBases` | Total bases |
| rbi | INTEGER | Yes | `stats.batting.rbi` | RBIs |
| leftOnBase | INTEGER | Yes | `stats.batting.leftOnBase` | Left on base |
| sacBunts | INTEGER | Yes | `stats.batting.sacBunts` | Sacrifice bunts |
| sacFlies | INTEGER | Yes | `stats.batting.sacFlies` | Sacrifice flies |
| catchersInterference | INTEGER | Yes | `stats.batting.catchersInterference` | Catcher's interference |
| pickoffs | INTEGER | Yes | `stats.batting.pickoffs` | Picked off |
| avg | TEXT | Yes | `stats.batting.avg` | Batting average (game) |
| obp | TEXT | Yes | `stats.batting.obp` | On-base percentage (game) |
| slg | TEXT | Yes | `stats.batting.slg` | Slugging percentage (game) |
| ops | TEXT | Yes | `stats.batting.ops` | OPS (game) |
| atBatsPerHomeRun | TEXT | Yes | `stats.batting.atBatsPerHomeRun` | At bats per home run |

**Foreign Keys:**
- `gamePk` → `games(gamePk)`
- `player_id` → `players(id)`
- `team_id` → `teams(id)`

**Unique Constraint:**
- `(gamePk, player_id)` - One batting record per player per game

**Indices:**
- `idx_game_batting_gamepk` on `gamePk`
- `idx_game_batting_player` on `player_id`
- `idx_game_batting_team` on `team_id`

---

## game_pitching

Per-player pitching statistics for each game.

**Source:** `/v1/game/{gamePk}/boxscore` → `teams.{away,home}.players.*.stats.pitching`

| Column | Type | Nullable | Source | Description |
|--------|------|----------|--------|-------------|
| id | INTEGER | No | auto | Auto-increment primary key |
| gamePk | INTEGER | No | - | Game ID (FK to games) |
| player_id | INTEGER | No | `players.*.person.id` | Player ID (FK to players) |
| team_id | INTEGER | No | `teams.{side}.team.id` | Team ID (FK to teams) |
| isStartingPitcher | INTEGER | Yes | `gameStatus.isStartingPitcher` | 1 if starter, 0 if reliever |
| pitchingOrder | INTEGER | Yes | Position in `teams.{side}.pitchers[]` | Order of appearance (1=starter) |
| gamesPlayed | INTEGER | Yes | `stats.pitching.gamesPlayed` | Games played (always 1) |
| gamesStarted | INTEGER | Yes | `stats.pitching.gamesStarted` | Games started |
| flyOuts | INTEGER | Yes | `stats.pitching.flyOuts` | Fly outs |
| groundOuts | INTEGER | Yes | `stats.pitching.groundOuts` | Ground outs |
| airOuts | INTEGER | Yes | `stats.pitching.airOuts` | Air outs |
| runs | INTEGER | Yes | `stats.pitching.runs` | Runs allowed |
| doubles | INTEGER | Yes | `stats.pitching.doubles` | Doubles allowed |
| triples | INTEGER | Yes | `stats.pitching.triples` | Triples allowed |
| homeRuns | INTEGER | Yes | `stats.pitching.homeRuns` | Home runs allowed |
| strikeOuts | INTEGER | Yes | `stats.pitching.strikeOuts` | Strikeouts |
| baseOnBalls | INTEGER | Yes | `stats.pitching.baseOnBalls` | Walks |
| intentionalWalks | INTEGER | Yes | `stats.pitching.intentionalWalks` | Intentional walks |
| hits | INTEGER | Yes | `stats.pitching.hits` | Hits allowed |
| hitByPitch | INTEGER | Yes | `stats.pitching.hitByPitch` | Hit batters |
| atBats | INTEGER | Yes | `stats.pitching.atBats` | At bats against |
| caughtStealing | INTEGER | Yes | `stats.pitching.caughtStealing` | Caught stealing |
| stolenBases | INTEGER | Yes | `stats.pitching.stolenBases` | Stolen bases allowed |
| numberOfPitches | INTEGER | Yes | `stats.pitching.numberOfPitches` | Pitch count |
| inningsPitched | TEXT | Yes | `stats.pitching.inningsPitched` | Innings pitched (e.g., "6.2") |
| wins | INTEGER | Yes | `stats.pitching.wins` | Wins (game) |
| losses | INTEGER | Yes | `stats.pitching.losses` | Losses (game) |
| saves | INTEGER | Yes | `stats.pitching.saves` | Saves (game) |
| saveOpportunities | INTEGER | Yes | `stats.pitching.saveOpportunities` | Save opportunities |
| holds | INTEGER | Yes | `stats.pitching.holds` | Holds |
| blownSaves | INTEGER | Yes | `stats.pitching.blownSaves` | Blown saves |
| earnedRuns | INTEGER | Yes | `stats.pitching.earnedRuns` | Earned runs |
| battersFaced | INTEGER | Yes | `stats.pitching.battersFaced` | Batters faced |
| outs | INTEGER | Yes | `stats.pitching.outs` | Outs recorded |
| pitchesThrown | INTEGER | Yes | `stats.pitching.pitchesThrown` | Pitches thrown |
| balls | INTEGER | Yes | `stats.pitching.balls` | Balls thrown |
| strikes | INTEGER | Yes | `stats.pitching.strikes` | Strikes thrown |
| strikePercentage | TEXT | Yes | `stats.pitching.strikePercentage` | Strike percentage |
| hitBatsmen | INTEGER | Yes | `stats.pitching.hitBatsmen` | Hit batsmen |
| balks | INTEGER | Yes | `stats.pitching.balks` | Balks |
| wildPitches | INTEGER | Yes | `stats.pitching.wildPitches` | Wild pitches |
| pickoffs | INTEGER | Yes | `stats.pitching.pickoffs` | Pickoffs |
| inheritedRunners | INTEGER | Yes | `stats.pitching.inheritedRunners` | Inherited runners |
| inheritedRunnersScored | INTEGER | Yes | `stats.pitching.inheritedRunnersScored` | Inherited runners scored |
| era | TEXT | Yes | `stats.pitching.era` | ERA (game) |
| whip | TEXT | Yes | `stats.pitching.whip` | WHIP (game) |
| note | TEXT | Yes | `seasonStats.pitching.note` | Game decision (W, L, S, H, BS) |

**Foreign Keys:**
- `gamePk` → `games(gamePk)`
- `player_id` → `players(id)`
- `team_id` → `teams(id)`

**Unique Constraint:**
- `(gamePk, player_id)` - One pitching record per player per game

**Indices:**
- `idx_game_pitching_gamepk` on `gamePk`
- `idx_game_pitching_player` on `player_id`
- `idx_game_pitching_team` on `team_id`

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

### Get game with team names
```sql
SELECT
    g.gamePk,
    g.gameDate,
    away.name AS away_team,
    home.name AS home_team,
    g.away_score,
    g.home_score,
    g.venue_name
FROM games g
JOIN teams away ON g.away_team_id = away.id
JOIN teams home ON g.home_team_id = home.id
WHERE g.gamePk = 745927;
```

### List all officials for a game
```sql
SELECT official_fullName, officialType
FROM game_officials
WHERE gamePk = 745927
ORDER BY officialType;
```
