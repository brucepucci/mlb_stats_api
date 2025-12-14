# MLB Stats Database Query Guide

This document provides everything needed to query the MLB Stats SQLite database. Use this reference when answering questions about baseball statistics.

## Database Connection

```
Path: /Users/brucepucci/Desktop/mlb_stats/data/mlb_stats.db
Type: SQLite (WAL mode enabled)
```

## IMPORTANT: Default Query Behavior

**Unless explicitly instructed otherwise, always filter to regular season games only:**

```sql
WHERE g.gameType = 'R'  -- Regular season only
```

Game type codes:
- **R** = Regular Season (DEFAULT - use this unless told otherwise)
- S = Spring Training
- F = Wild Card
- D = Division Series
- L = League Championship Series
- W = World Series
- A = All-Star Game
- E = Exhibition

---

## Current Data Coverage

**Last Updated:** 2025-12-03

| Table | Row Count | Description |
|-------|-----------|-------------|
| games | 51,574 | Game metadata (2008-2025) |
| teams | 136 | Team reference data (including historical) |
| players | 19,401 | Player biographical data |
| game_batting | 1,329,168 | Per-player batting stats per game |
| game_pitching | 454,620 | Per-player pitching stats per game |
| at_bats | 3,910,551 | Plate appearance summaries |
| pitches | 14,067,818 | Individual pitch data with Statcast |
| batted_balls | 2,723,285 | Balls put in play with exit velo/launch angle |
| game_officials | 206,010 | Umpires per game |
| game_rosters | ~2,680,000 | Active 26-man roster per team per game |

**Date Range:** 2008-02-26 to 2025-11-01
**Seasons:** 18 (2008-2025)
**Regular Season Games:** 42,190
**Postseason Games:** 9,384

### Database File Statistics

- **File Size:** 10.3 GB
- **Page Count:** 2,709,537 pages
- **Page Size:** 4,096 bytes
- **Cache Size:** 2,000 pages (~8 MB)

### Statcast Data Coverage

**Pitch-Level Metrics:**
- Spin Rate: 92.0% coverage (12.9M of 14.1M pitches)
- Extension: 45.7% coverage (6.4M of 14.1M pitches)
- Average pitches per game: 273.9

**Batted Ball Metrics:**
- Exit Velocity: 48.1% coverage (1.3M of 2.7M batted balls)
- Launch Angle: 48.1% coverage (1.3M of 2.7M batted balls)

*Note: Coverage varies by era - pre-2015 games have limited Statcast data.*

---

## Table Schemas and Relationships

### Entity Relationship Overview

```
teams (id) ←──┬── players (currentTeam_id)
              ├── games (away_team_id, home_team_id)
              ├── game_batting (team_id)
              ├── game_pitching (team_id)
              └── game_rosters (team_id)

players (id) ←──┬── game_batting (player_id)
                ├── game_pitching (player_id)
                ├── game_rosters (player_id)
                ├── at_bats (batter_id, pitcher_id)
                ├── pitches (batter_id, pitcher_id)
                └── batted_balls (batter_id, pitcher_id)

games (gamePk) ←──┬── game_batting (gamePk)
                  ├── game_pitching (gamePk)
                  ├── game_officials (gamePk)
                  ├── game_rosters (gamePk)
                  ├── at_bats (gamePk)
                  ├── pitches (gamePk)
                  └── batted_balls (gamePk)

pitches (gamePk, atBatIndex, pitchNumber) ←── batted_balls (FK)
```

---

## Table Details

### 1. `teams` - Team Reference Data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | MLB team ID (PRIMARY KEY) |
| name | TEXT | Full name ("Los Angeles Dodgers") |
| abbreviation | TEXT | 3-letter code ("LAD") |
| teamName | TEXT | Short name ("Dodgers") |
| locationName | TEXT | City ("Los Angeles") |
| league_id | INTEGER | League ID (103=AL, 104=NL) |
| league_name | TEXT | "American League" or "National League" |
| division_id | INTEGER | Division ID |
| division_name | TEXT | Full division name |
| active | INTEGER | 1=active, 0=inactive |

### 2. `players` - Player Biographical Data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | MLB person ID (PRIMARY KEY) |
| fullName | TEXT | "Shohei Ohtani" |
| firstName | TEXT | "Shohei" |
| lastName | TEXT | "Ohtani" |
| boxscoreName | TEXT | "Ohtani, S" |
| primaryNumber | TEXT | Jersey number |
| birthDate | TEXT | YYYY-MM-DD |
| birthCountry | TEXT | Country of birth |
| height | TEXT | "6' 4\"" |
| weight | INTEGER | Pounds |
| primaryPosition_code | TEXT | Position code (see appendix) |
| primaryPosition_name | TEXT | "Designated Hitter" |
| batSide_code | TEXT | L, R, or S (switch) |
| pitchHand_code | TEXT | L or R |
| mlbDebutDate | TEXT | YYYY-MM-DD |
| lastPlayedDate | TEXT | Most recent game |
| active | INTEGER | 1=active, 0=inactive |
| currentTeam_id | INTEGER | FK to teams.id |

### 3. `games` - Game Metadata

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | Unique game ID (PRIMARY KEY) |
| season | INTEGER | Year (2024) |
| **gameType** | TEXT | **R=Regular, F=WildCard, D=Division, L=LCS, W=WorldSeries, S=Spring, A=AllStar** |
| gameDate | TEXT | YYYY-MM-DD |
| gameDateTime | TEXT | ISO8601 UTC timestamp |
| away_team_id | INTEGER | FK to teams.id |
| home_team_id | INTEGER | FK to teams.id |
| away_score | INTEGER | Final away score |
| home_score | INTEGER | Final home score |
| abstractGameState | TEXT | 'Final', 'Live', 'Preview' |
| venue_name | TEXT | Stadium name |
| dayNight | TEXT | 'day' or 'night' |
| weather_condition | TEXT | "Clear", "Cloudy", etc. |
| weather_temp | TEXT | Temperature |
| weather_wind | TEXT | Wind description |
| attendance | INTEGER | Crowd size |
| doubleHeader | TEXT | Y/N/S |
| gameNumber | INTEGER | 1 or 2 for doubleheaders |
| umpire_HP_id | INTEGER | Home plate umpire ID |
| umpire_HP_name | TEXT | Home plate umpire name |

### 4. `game_batting` - Per-Game Batting Stats

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| player_id | INTEGER | FK to players |
| team_id | INTEGER | FK to teams |
| battingOrder | INTEGER | 100=leadoff, 200=2nd, ... 900=9th |
| position_code | TEXT | Position played |
| position_abbreviation | TEXT | "SS", "CF", "DH", etc. |
| atBats | INTEGER | At bats |
| hits | INTEGER | Hits |
| doubles | INTEGER | 2B |
| triples | INTEGER | 3B |
| homeRuns | INTEGER | HR |
| runs | INTEGER | R |
| rbi | INTEGER | RBI |
| baseOnBalls | INTEGER | BB |
| strikeOuts | INTEGER | K |
| stolenBases | INTEGER | SB |
| caughtStealing | INTEGER | CS |
| hitByPitch | INTEGER | HBP |
| sacFlies | INTEGER | SF |
| sacBunts | INTEGER | SAC |
| plateAppearances | INTEGER | PA |
| totalBases | INTEGER | TB |
| groundIntoDoublePlay | INTEGER | GIDP |
| leftOnBase | INTEGER | LOB |

**UNIQUE:** (gamePk, player_id)

### 5. `game_pitching` - Per-Game Pitching Stats

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| player_id | INTEGER | FK to players |
| team_id | INTEGER | FK to teams |
| pitchingOrder | INTEGER | 1=starter, 2=first reliever, etc. |
| isStartingPitcher | INTEGER | 1 or 0 (NOTE: may be 0, use pitchingOrder=1) |
| inningsPitched | TEXT | "6.2" format |
| outs | INTEGER | Total outs recorded |
| hits | INTEGER | H |
| runs | INTEGER | R |
| earnedRuns | INTEGER | ER |
| baseOnBalls | INTEGER | BB |
| strikeOuts | INTEGER | K |
| homeRuns | INTEGER | HR |
| hitByPitch | INTEGER | HBP |
| numberOfPitches | INTEGER | Pitch count |
| strikes | INTEGER | Strikes thrown |
| balls | INTEGER | Balls thrown |
| wins | INTEGER | 1 if got W |
| losses | INTEGER | 1 if got L |
| saves | INTEGER | 1 if got S |
| holds | INTEGER | 1 if got H |
| blownSaves | INTEGER | 1 if BS |
| battersFaced | INTEGER | BF |
| inheritedRunners | INTEGER | Runners inherited |
| inheritedRunnersScored | INTEGER | IR that scored |
| wildPitches | INTEGER | WP |
| balks | INTEGER | BK |
| note | TEXT | 'W', 'L', 'S', 'H', 'BS', etc. |

**UNIQUE:** (gamePk, player_id)

**NOTE:** To identify starters, use `WHERE pitchingOrder = 1` (more reliable than isStartingPitcher)

### 6. `at_bats` - Plate Appearance Summaries

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| atBatIndex | INTEGER | 0-indexed within game |
| inning | INTEGER | Inning number |
| halfInning | TEXT | 'top' or 'bottom' |
| batter_id | INTEGER | FK to players |
| pitcher_id | INTEGER | FK to players |
| batSide_code | TEXT | L or R |
| pitchHand_code | TEXT | L or R |
| event | TEXT | "Strikeout", "Single", "Home Run" |
| eventType | TEXT | "strikeout", "single", "home_run" |
| description | TEXT | Full play description |
| rbi | INTEGER | RBI on play |
| awayScore | INTEGER | Score after PA |
| homeScore | INTEGER | Score after PA |
| pitchCount | INTEGER | Pitches in PA |
| balls | INTEGER | Final ball count |
| strikes | INTEGER | Final strike count |
| outs | INTEGER | Outs after PA |
| isScoringPlay | INTEGER | 1 if run(s) scored |

**UNIQUE:** (gamePk, atBatIndex)

### 7. `pitches` - Individual Pitch Data (Statcast)

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| atBatIndex | INTEGER | Links to at_bats |
| pitchNumber | INTEGER | Pitch # within at-bat (1-indexed) |
| inning | INTEGER | Inning |
| halfInning | TEXT | 'top' or 'bottom' |
| batter_id | INTEGER | FK to players |
| pitcher_id | INTEGER | FK to players |
| batSide_code | TEXT | L or R |
| pitchHand_code | TEXT | L or R |
| balls | INTEGER | Ball count BEFORE pitch |
| strikes | INTEGER | Strike count BEFORE pitch |
| outs | INTEGER | Outs BEFORE pitch |
| **Pitch Result** | | |
| call_code | TEXT | B, C, S, F, X, etc. (see appendix) |
| call_description | TEXT | "Ball", "Called Strike", "In Play" |
| isInPlay | INTEGER | 1 if ball was put in play |
| isStrike | INTEGER | 1 if strike (any type) |
| isBall | INTEGER | 1 if ball |
| **Pitch Type** | | |
| type_code | TEXT | FF, SL, CH, etc. (see appendix) |
| type_description | TEXT | "Four-Seam Fastball" |
| typeConfidence | REAL | Classification confidence 0-1 |
| **Velocity** | | |
| startSpeed | REAL | Release velocity (mph) |
| endSpeed | REAL | Velocity at plate (mph) |
| **Location** | | |
| zone | INTEGER | Strike zone 1-9, outside 11-14 |
| plateX | REAL | Horizontal location (ft from center, + = catcher's right) |
| plateZ | REAL | Vertical location (ft from ground) |
| strikeZoneTop | REAL | Top of zone for this batter (ft) |
| strikeZoneBottom | REAL | Bottom of zone for this batter (ft) |
| **Movement** | | |
| pfxX | REAL | Horizontal movement (inches) |
| pfxZ | REAL | Vertical movement (inches, gravity-adjusted) |
| **Spin (Statcast)** | | |
| spinRate | INTEGER | Spin rate (RPM) |
| spinDirection | INTEGER | Spin axis (degrees, 0-360) |
| **Release** | | |
| extension | REAL | Release extension (feet) |
| x0 | REAL | Horizontal release point (ft) |
| z0 | REAL | Vertical release point (ft) |
| **Timing** | | |
| plateTime | REAL | Time to plate (seconds) |

**UNIQUE:** (gamePk, atBatIndex, pitchNumber)

### 8. `batted_balls` - Balls in Play (Statcast)

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| atBatIndex | INTEGER | Links to at_bats |
| pitchNumber | INTEGER | Which pitch was hit |
| batter_id | INTEGER | FK to players |
| pitcher_id | INTEGER | FK to players |
| inning | INTEGER | Inning |
| halfInning | TEXT | 'top' or 'bottom' |
| **Statcast Metrics** | | |
| launchSpeed | REAL | Exit velocity (mph) |
| launchAngle | REAL | Launch angle (degrees, - = down) |
| totalDistance | REAL | Distance traveled (feet) |
| **Classification** | | |
| trajectory | TEXT | fly_ball, ground_ball, line_drive, popup |
| hardness | TEXT | soft, medium, hard |
| **Result** | | |
| event | TEXT | "Single", "Home Run", "Flyout" |
| eventType | TEXT | "single", "home_run", "field_out" |
| description | TEXT | Full description |
| rbi | INTEGER | RBI on play |
| location | TEXT | Fielder position (1-9) |
| coordinates_x | REAL | Spray chart X |
| coordinates_y | REAL | Spray chart Y |

**UNIQUE:** (gamePk, atBatIndex, pitchNumber)

### 9. `game_officials` - Umpires

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| official_id | INTEGER | Umpire ID |
| official_fullName | TEXT | Umpire name |
| officialType | TEXT | "Home Plate", "First Base", "Second Base", "Third Base" |

### 10. `game_rosters` - Active Roster Per Game

Tracks which players were on each team's active 26-man roster for each game. Players absent from the roster were on IL/DL.

| Column | Type | Description |
|--------|------|-------------|
| gamePk | INTEGER | FK to games |
| team_id | INTEGER | FK to teams |
| player_id | INTEGER | FK to players |
| jerseyNumber | TEXT | Jersey number at time of game |
| position_code | TEXT | Position code (1-10, Y) |
| position_name | TEXT | "Pitcher", "Catcher", etc. |
| position_type | TEXT | "Pitcher", "Infielder", "Outfielder", etc. |
| position_abbreviation | TEXT | "P", "C", "SS", "DH", etc. |
| status_code | TEXT | "A" for Active |
| status_description | TEXT | "Active" |

**UNIQUE:** (gamePk, team_id, player_id)

**Use Case:** Detect IL/DL stints by finding games where a player is NOT on their team's roster.

---

## Code Reference Tables

### Pitch Type Codes (type_code)

| Code | Description |
|------|-------------|
| FF | Four-Seam Fastball |
| SI | Sinker |
| FC | Cutter |
| SL | Slider |
| ST | Sweeper |
| SV | Slurve |
| CU | Curveball |
| KC | Knuckle Curve |
| CH | Changeup |
| FS | Splitter |
| KN | Knuckleball |
| EP | Eephus |
| FA | Fastball (generic) |

### Pitch Result Codes (call_code)

| Code | Description |
|------|-------------|
| B | Ball |
| C | Called Strike |
| S | Swinging Strike |
| F | Foul |
| X | In Play |
| T | Foul Tip |
| W | Swinging Strike (Blocked) |
| H | Hit By Pitch |
| I | Intentional Ball |
| L | Foul Bunt |
| M | Missed Bunt |

### Batted Ball Trajectories

| Value | Description |
|-------|-------------|
| fly_ball | Fly Ball |
| ground_ball | Ground Ball |
| line_drive | Line Drive |
| popup | Pop Up |
| bunt_grounder | Bunt Ground Ball |
| bunt_popup | Bunt Pop Up |

### Event Types (eventType in at_bats/batted_balls)

| Event | Description |
|-------|-------------|
| single | Single |
| double | Double |
| triple | Triple |
| home_run | Home Run |
| field_out | Fielded Out |
| strikeout | Strikeout |
| walk | Walk |
| intent_walk | Intentional Walk |
| hit_by_pitch | Hit By Pitch |
| sac_fly | Sacrifice Fly |
| sac_bunt | Sacrifice Bunt |
| grounded_into_double_play | GIDP |
| force_out | Force Out |
| field_error | Error |
| fielders_choice | Fielder's Choice |
| double_play | Double Play |

### Position Codes

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

### Strike Zone Numbers

```
Zones 1-9 (inside strike zone, 3x3 grid):
         Inside    Middle   Outside
         ------    ------   -------
  Top      1         2         3
  Mid      4         5         6
  Bot      7         8         9

Zones 11-14 (outside strike zone):
  11 = Above zone
  12 = Below zone
  13 = Inside (to batter)
  14 = Outside (from batter)
```

---

## Common Query Patterns

### Player Stats Over Date Range (Regular Season)

```sql
-- Batting stats for a player (regular season only)
SELECT
    p.fullName,
    SUM(gb.hits) as H,
    SUM(gb.homeRuns) as HR,
    SUM(gb.rbi) as RBI,
    SUM(gb.strikeOuts) as K,
    SUM(gb.baseOnBalls) as BB,
    ROUND(1.0 * SUM(gb.hits) / NULLIF(SUM(gb.atBats), 0), 3) as AVG
FROM game_batting gb
JOIN players p ON gb.player_id = p.id
JOIN games g ON gb.gamePk = g.gamePk
WHERE p.fullName = 'Shohei Ohtani'
  AND g.gameType = 'R'  -- Regular season only
  AND g.gameDate BETWEEN '2024-07-01' AND '2024-07-31'
GROUP BY p.id;
```

### Pitcher Game Score (Regular Season)

```sql
-- Game Score = 50 + (3×outs) + (2×K) - (2×H) - (4×ER) - (2×BB) - HR
SELECT
    p.fullName,
    g.gameDate,
    gp.inningsPitched,
    gp.strikeOuts as K,
    gp.hits as H,
    gp.earnedRuns as ER,
    (50 + (3 * gp.outs) + (2 * gp.strikeOuts) - (2 * gp.hits)
       - (4 * gp.earnedRuns) - (2 * gp.baseOnBalls) - gp.homeRuns) as game_score
FROM game_pitching gp
JOIN players p ON gp.player_id = p.id
JOIN games g ON gp.gamePk = g.gamePk
WHERE gp.pitchingOrder = 1  -- Starters only
  AND g.gameType = 'R'      -- Regular season only
ORDER BY game_score DESC;
```

### Pitch Arsenal Analysis (Regular Season)

```sql
-- Pitcher's pitch mix with avg velocity and spin
SELECT
    p.fullName,
    pit.type_code,
    pit.type_description,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY pit.pitcher_id), 1) as pct,
    ROUND(AVG(pit.startSpeed), 1) as avg_velo,
    ROUND(AVG(pit.spinRate), 0) as avg_spin
FROM pitches pit
JOIN players p ON pit.pitcher_id = p.id
JOIN games g ON pit.gamePk = g.gamePk
WHERE p.fullName = 'Tyler Glasnow'
  AND g.gameType = 'R'  -- Regular season only
GROUP BY pit.pitcher_id, pit.type_code
ORDER BY count DESC;
```

### Exit Velocity Leaders (Regular Season)

```sql
-- Average exit velocity (min 20 batted balls)
SELECT
    p.fullName,
    ROUND(AVG(bb.launchSpeed), 1) as avg_EV,
    ROUND(MAX(bb.launchSpeed), 1) as max_EV,
    COUNT(*) as batted_balls
FROM batted_balls bb
JOIN players p ON bb.batter_id = p.id
JOIN games g ON bb.gamePk = g.gamePk
WHERE bb.launchSpeed IS NOT NULL
  AND g.gameType = 'R'  -- Regular season only
GROUP BY bb.batter_id
HAVING COUNT(*) >= 20
ORDER BY avg_EV DESC
LIMIT 20;
```

### Barrel Rate (Regular Season)

```sql
-- Barrel = Exit Velo >= 98 AND Launch Angle 26-30 degrees
SELECT
    p.fullName,
    COUNT(*) as batted_balls,
    SUM(CASE WHEN bb.launchSpeed >= 98 AND bb.launchAngle BETWEEN 26 AND 30
        THEN 1 ELSE 0 END) as barrels,
    ROUND(100.0 * SUM(CASE WHEN bb.launchSpeed >= 98 AND bb.launchAngle BETWEEN 26 AND 30
        THEN 1 ELSE 0 END) / COUNT(*), 1) as barrel_pct
FROM batted_balls bb
JOIN players p ON bb.batter_id = p.id
JOIN games g ON bb.gamePk = g.gamePk
WHERE bb.launchSpeed IS NOT NULL
  AND g.gameType = 'R'  -- Regular season only
GROUP BY bb.batter_id
HAVING COUNT(*) >= 30
ORDER BY barrel_pct DESC;
```

### Platoon Splits (Regular Season)

```sql
-- Batter vs LHP/RHP
SELECT
    pit.pitchHand_code as pitcher_hand,
    COUNT(*) as PA,
    SUM(CASE WHEN ab.eventType IN ('single','double','triple','home_run') THEN 1 ELSE 0 END) as hits,
    SUM(CASE WHEN ab.eventType = 'strikeout' THEN 1 ELSE 0 END) as K,
    SUM(CASE WHEN ab.eventType IN ('walk','intent_walk') THEN 1 ELSE 0 END) as BB
FROM at_bats ab
JOIN pitches pit ON ab.gamePk = pit.gamePk AND ab.atBatIndex = pit.atBatIndex
JOIN players p ON ab.batter_id = p.id
JOIN games g ON ab.gamePk = g.gamePk
WHERE p.fullName = 'Mookie Betts'
  AND pit.pitchNumber = 1  -- Just get one pitch per AB for the handedness
  AND g.gameType = 'R'     -- Regular season only
GROUP BY pit.pitchHand_code;
```

### Umpire Strike Zone Analysis (Regular Season)

```sql
-- Called strike rate by umpire
SELECT
    g.umpire_HP_name,
    COUNT(*) as pitches_called,
    SUM(CASE WHEN p.call_code = 'C' THEN 1 ELSE 0 END) as called_strikes,
    ROUND(100.0 * SUM(CASE WHEN p.call_code = 'C' THEN 1 ELSE 0 END) / COUNT(*), 1) as K_rate
FROM pitches p
JOIN games g ON p.gamePk = g.gamePk
WHERE p.call_code IN ('B', 'C')  -- Only called pitches (not swings)
  AND g.gameType = 'R'           -- Regular season only
GROUP BY g.umpire_HP_id
HAVING COUNT(*) >= 200
ORDER BY K_rate DESC;
```

### Team Stats (Regular Season)

```sql
-- Team batting totals
SELECT
    t.abbreviation,
    SUM(gb.runs) as R,
    SUM(gb.hits) as H,
    SUM(gb.homeRuns) as HR,
    SUM(gb.strikeOuts) as K,
    SUM(gb.baseOnBalls) as BB
FROM game_batting gb
JOIN teams t ON gb.team_id = t.id
JOIN games g ON gb.gamePk = g.gamePk
WHERE g.gameType = 'R'  -- Regular season only
GROUP BY t.id
ORDER BY R DESC;
```

### Pitch Sequence in At-Bat

```sql
-- All pitches in a specific at-bat
SELECT
    pitchNumber,
    type_code,
    ROUND(startSpeed, 1) as velo,
    call_description,
    balls || '-' || strikes as count
FROM pitches
WHERE gamePk = 745927
  AND atBatIndex = 0
ORDER BY pitchNumber;
```

### IL/DL Detection (Using game_rosters)

```sql
-- Find dates when a player was NOT on active roster (IL/DL stint)
SELECT g.gameDate, g.gamePk
FROM games g
WHERE (g.away_team_id = 119 OR g.home_team_id = 119)  -- Team ID
  AND g.season = 2024
  AND g.gameType = 'R'
  AND NOT EXISTS (
    SELECT 1 FROM game_rosters gr
    WHERE gr.gamePk = g.gamePk
      AND gr.player_id = 660271   -- Player ID (e.g., Shohei Ohtani)
      AND gr.team_id = 119        -- Player's team
  )
ORDER BY g.gameDate;
```

```sql
-- Compare roster vs boxscore: who was on roster but didn't play?
SELECT
    p.fullName,
    gr.position_abbreviation
FROM game_rosters gr
JOIN players p ON gr.player_id = p.id
LEFT JOIN game_batting gb ON gr.gamePk = gb.gamePk AND gr.player_id = gb.player_id
LEFT JOIN game_pitching gp ON gr.gamePk = gp.gamePk AND gr.player_id = gp.player_id
WHERE gr.gamePk = 745927
  AND gb.player_id IS NULL
  AND gp.player_id IS NULL;
```

---

## Important Notes

1. **ALWAYS FILTER BY GAME TYPE:** Unless explicitly asked for postseason or all games, include `WHERE g.gameType = 'R'` to limit to regular season.

2. **Starters:** Use `pitchingOrder = 1` to identify starting pitchers (more reliable than `isStartingPitcher`)

3. **Null Handling:** Statcast fields (spinRate, launchSpeed, etc.) may be NULL for older games or tracking failures. Always use `COALESCE()` or `WHERE ... IS NOT NULL` as appropriate.

4. **Innings Pitched:** The `inningsPitched` field is TEXT (e.g., "6.2" means 6⅔ innings). Use `outs` column for calculations.

5. **Dates:** All dates are TEXT in YYYY-MM-DD format. Use string comparisons for filtering.

6. **Scores:** `awayScore`/`homeScore` in at_bats and batted_balls reflect score AFTER the play.

7. **Pitch Counts:** In the `pitches` table, `balls` and `strikes` are the count BEFORE the pitch.

8. **Player Names:** Always join to `players` table to get names. Use `fullName` for display.

9. **Team Names:** Join to `teams` table. Use `abbreviation` for compact display, `name` for full name.
