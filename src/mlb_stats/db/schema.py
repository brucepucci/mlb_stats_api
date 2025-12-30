"""Database schema for MLB Stats Collector.

All 13 tables with exact MLB field names as specified in PROJECT_PLAN.md.
Metadata columns are prefixed with underscore (_written_at, _git_hash, _version).
"""

import sqlite3

SCHEMA_VERSION = "1.2.0"

# SQL statements for each table
# Note: MLB field names are preserved exactly (gamePk, fullName, strikeOuts, etc.)

CREATE_META_TABLE = """
CREATE TABLE IF NOT EXISTS _meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_TEAMS_TABLE = """
CREATE TABLE IF NOT EXISTS teams (
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
    active INTEGER,                      -- 1 or 0

    -- API fetch metadata
    _fetched_at TEXT NOT NULL,

    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL
);
"""

CREATE_TEAMS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_teams_abbreviation ON teams(abbreviation);
CREATE INDEX IF NOT EXISTS idx_teams_division ON teams(division_id);
"""


CREATE_VENUES_TABLE = """
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER NOT NULL,                 -- MLB venueId
    year INTEGER NOT NULL,               -- Year this venue data applies to
    name TEXT NOT NULL,                  -- "Dodger Stadium"
    active INTEGER,                      -- 1 or 0

    -- Location
    address1 TEXT,
    city TEXT,
    state TEXT,
    stateAbbrev TEXT,
    postalCode TEXT,
    country TEXT,
    phone TEXT,
    latitude REAL,                       -- location.defaultCoordinates.latitude
    longitude REAL,                      -- location.defaultCoordinates.longitude
    azimuthAngle REAL,                   -- Field orientation in degrees
    elevation INTEGER,                   -- Feet above sea level

    -- Time zone
    timeZone_id TEXT,                    -- "America/Los_Angeles"
    timeZone_offset INTEGER,             -- UTC offset (e.g., -8)
    timeZone_tz TEXT,                    -- "PST"

    -- Field info
    capacity INTEGER,                    -- Seating capacity
    turfType TEXT,                       -- "Grass", "Artificial Turf"
    roofType TEXT,                       -- "Open", "Retractable", "Dome"

    -- Field dimensions (feet from home plate)
    leftLine INTEGER,
    leftCenter INTEGER,
    center INTEGER,
    rightCenter INTEGER,
    rightLine INTEGER,

    -- API fetch metadata
    _fetched_at TEXT NOT NULL,

    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,

    PRIMARY KEY (id, year)
);
"""

CREATE_VENUES_INDICES = """
CREATE INDEX IF NOT EXISTS idx_venues_name ON venues(name);
CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city);
CREATE INDEX IF NOT EXISTS idx_venues_year ON venues(year);
"""


CREATE_PLAYERS_TABLE = """
CREATE TABLE IF NOT EXISTS players (
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

    height TEXT,                         -- "6' 4\\""
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
"""

CREATE_PLAYERS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_players_active ON players(active);
CREATE INDEX IF NOT EXISTS idx_players_lastPlayedDate ON players(lastPlayedDate);
"""

CREATE_GAMES_TABLE = """
CREATE TABLE IF NOT EXISTS games (
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
    venue_id INTEGER,                    -- FK to venues(id, year) with season

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

    -- API fetch metadata
    _fetched_at TEXT NOT NULL,

    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,

    FOREIGN KEY (away_team_id) REFERENCES teams(id),
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (venue_id, season) REFERENCES venues(id, year)
);
"""

CREATE_GAMES_INDICES = """
CREATE INDEX IF NOT EXISTS idx_games_date ON games(gameDate);
CREATE INDEX IF NOT EXISTS idx_games_season ON games(season);
CREATE INDEX IF NOT EXISTS idx_games_away_team ON games(away_team_id);
CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team_id);
CREATE INDEX IF NOT EXISTS idx_games_venue ON games(venue_id);
CREATE INDEX IF NOT EXISTS idx_games_venue_season ON games(venue_id, season);
"""

CREATE_GAME_OFFICIALS_TABLE = """
CREATE TABLE IF NOT EXISTS game_officials (
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
"""

CREATE_GAME_OFFICIALS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_game_officials_gamepk ON game_officials(gamePk);
"""

CREATE_GAME_BATTING_TABLE = """
CREATE TABLE IF NOT EXISTS game_batting (
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

    -- Rate stats from API (sparse - only provided in some contexts)
    atBatsPerHomeRun TEXT,
    stolenBasePercentage TEXT,

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
"""

CREATE_GAME_BATTING_INDICES = """
CREATE INDEX IF NOT EXISTS idx_game_batting_gamepk ON game_batting(gamePk);
CREATE INDEX IF NOT EXISTS idx_game_batting_player ON game_batting(player_id);
CREATE INDEX IF NOT EXISTS idx_game_batting_team ON game_batting(team_id);
CREATE INDEX IF NOT EXISTS idx_game_batting_position ON game_batting(position_code);
CREATE INDEX IF NOT EXISTS idx_game_batting_order ON game_batting(battingOrder);
"""

CREATE_GAME_PITCHING_TABLE = """
CREATE TABLE IF NOT EXISTS game_pitching (
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
"""

CREATE_GAME_PITCHING_INDICES = """
CREATE INDEX IF NOT EXISTS idx_game_pitching_gamepk ON game_pitching(gamePk);
CREATE INDEX IF NOT EXISTS idx_game_pitching_player ON game_pitching(player_id);
CREATE INDEX IF NOT EXISTS idx_game_pitching_team ON game_pitching(team_id);
CREATE INDEX IF NOT EXISTS idx_game_pitching_earnedRuns ON game_pitching(earnedRuns);
CREATE INDEX IF NOT EXISTS idx_game_pitching_isStarter ON game_pitching(isStartingPitcher);
"""

CREATE_PITCHES_TABLE = """
CREATE TABLE IF NOT EXISTS pitches (
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
"""

CREATE_PITCHES_INDICES = """
CREATE INDEX IF NOT EXISTS idx_pitches_gamepk ON pitches(gamePk);
CREATE INDEX IF NOT EXISTS idx_pitches_batter ON pitches(batter_id);
CREATE INDEX IF NOT EXISTS idx_pitches_pitcher ON pitches(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_pitches_atbat ON pitches(gamePk, atBatIndex);
CREATE INDEX IF NOT EXISTS idx_pitches_type ON pitches(type_code);
CREATE INDEX IF NOT EXISTS idx_pitches_spin ON pitches(spinRate);
CREATE INDEX IF NOT EXISTS idx_pitches_velo ON pitches(startSpeed);
"""

CREATE_BATTED_BALLS_TABLE = """
CREATE TABLE IF NOT EXISTS batted_balls (
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
"""

CREATE_BATTED_BALLS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_batted_balls_gamepk ON batted_balls(gamePk);
CREATE INDEX IF NOT EXISTS idx_batted_balls_batter ON batted_balls(batter_id);
CREATE INDEX IF NOT EXISTS idx_batted_balls_pitcher ON batted_balls(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_batted_balls_exit_velo ON batted_balls(launchSpeed);
CREATE INDEX IF NOT EXISTS idx_batted_balls_launch_angle ON batted_balls(launchAngle);
CREATE INDEX IF NOT EXISTS idx_batted_balls_trajectory ON batted_balls(trajectory);
CREATE INDEX IF NOT EXISTS idx_batted_balls_event ON batted_balls(eventType);
"""

CREATE_GAME_ROSTERS_TABLE = """
CREATE TABLE IF NOT EXISTS game_rosters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gamePk INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,

    -- Position at time of roster snapshot
    jerseyNumber TEXT,
    position_code TEXT,
    position_name TEXT,
    position_type TEXT,
    position_abbreviation TEXT,

    -- Roster status
    status_code TEXT,
    status_description TEXT,

    -- API fetch metadata
    _fetched_at TEXT NOT NULL,

    -- Write metadata (provenance)
    _written_at TEXT NOT NULL,
    _git_hash TEXT NOT NULL,
    _version TEXT NOT NULL,

    FOREIGN KEY (gamePk) REFERENCES games(gamePk),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    UNIQUE(gamePk, team_id, player_id)
);
"""

CREATE_GAME_ROSTERS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_game_rosters_gamepk ON game_rosters(gamePk);
CREATE INDEX IF NOT EXISTS idx_game_rosters_team ON game_rosters(team_id);
CREATE INDEX IF NOT EXISTS idx_game_rosters_player ON game_rosters(player_id);
"""

CREATE_AT_BATS_TABLE = """
CREATE TABLE IF NOT EXISTS at_bats (
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
"""

CREATE_AT_BATS_INDICES = """
CREATE INDEX IF NOT EXISTS idx_at_bats_gamepk ON at_bats(gamePk);
CREATE INDEX IF NOT EXISTS idx_at_bats_batter ON at_bats(batter_id);
CREATE INDEX IF NOT EXISTS idx_at_bats_pitcher ON at_bats(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_at_bats_event ON at_bats(eventType);
CREATE INDEX IF NOT EXISTS idx_at_bats_inning ON at_bats(inning);
"""

CREATE_SYNC_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS sync_log (
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
"""

CREATE_SYNC_LOG_INDICES = """
CREATE INDEX IF NOT EXISTS idx_sync_log_type ON sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_gamepk ON sync_log(gamePk);
"""


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables.

    Creates all 13 tables with their indices. Tables are created in order
    to satisfy foreign key dependencies.

    Parameters
    ----------
    conn : sqlite3.Connection
        Database connection
    """
    cursor = conn.cursor()

    # Create tables in dependency order
    # 1. _meta (no dependencies)
    cursor.execute(CREATE_META_TABLE)

    # 2. teams (no dependencies)
    cursor.execute(CREATE_TEAMS_TABLE)
    cursor.executescript(CREATE_TEAMS_INDICES)

    # 3. venues (no dependencies)
    cursor.execute(CREATE_VENUES_TABLE)
    cursor.executescript(CREATE_VENUES_INDICES)

    # 4. players (depends on teams)
    cursor.execute(CREATE_PLAYERS_TABLE)
    cursor.executescript(CREATE_PLAYERS_INDICES)

    # 5. games (depends on teams, venues)
    cursor.execute(CREATE_GAMES_TABLE)
    cursor.executescript(CREATE_GAMES_INDICES)

    # 6. game_officials (depends on games)
    cursor.execute(CREATE_GAME_OFFICIALS_TABLE)
    cursor.executescript(CREATE_GAME_OFFICIALS_INDICES)

    # 7. game_batting (depends on games, players, teams)
    cursor.execute(CREATE_GAME_BATTING_TABLE)
    cursor.executescript(CREATE_GAME_BATTING_INDICES)

    # 8. game_pitching (depends on games, players, teams)
    cursor.execute(CREATE_GAME_PITCHING_TABLE)
    cursor.executescript(CREATE_GAME_PITCHING_INDICES)

    # 9. at_bats (depends on games, players)
    cursor.execute(CREATE_AT_BATS_TABLE)
    cursor.executescript(CREATE_AT_BATS_INDICES)

    # 10. pitches (depends on games, players)
    cursor.execute(CREATE_PITCHES_TABLE)
    cursor.executescript(CREATE_PITCHES_INDICES)

    # 11. batted_balls (depends on games, players, pitches)
    cursor.execute(CREATE_BATTED_BALLS_TABLE)
    cursor.executescript(CREATE_BATTED_BALLS_INDICES)

    # 12. game_rosters (depends on games, teams, players)
    cursor.execute(CREATE_GAME_ROSTERS_TABLE)
    cursor.executescript(CREATE_GAME_ROSTERS_INDICES)

    # 13. sync_log (no dependencies)
    cursor.execute(CREATE_SYNC_LOG_TABLE)
    cursor.executescript(CREATE_SYNC_LOG_INDICES)

    conn.commit()


def get_table_names() -> list[str]:
    """Get list of all table names in the schema.

    Returns
    -------
    list of str
        Table names in creation order
    """
    return [
        "_meta",
        "teams",
        "venues",
        "players",
        "games",
        "game_officials",
        "game_batting",
        "game_pitching",
        "at_bats",
        "pitches",
        "batted_balls",
        "game_rosters",
        "sync_log",
    ]
