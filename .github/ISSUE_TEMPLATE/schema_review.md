# Database Schema Review Findings

Expert DBA review of the MLB Stats API database schema, highlighting opportunities for performance optimization, data integrity improvements, and best practices.

## 🔴 Critical Issues

### 1. Data Type Mismatches for Rate Statistics
**Problem:** Rate statistics stored as TEXT instead of REAL, requiring CAST operations in queries and preventing numeric indexing.

**Affected columns:**
- `game_batting`: `atBatsPerHomeRun`, `stolenBasePercentage`
- `game_pitching`: `era`, `whip`, `strikePercentage`, `runsScoredPer9`, `homeRunsPer9`

**Recommendation:**
```sql
-- Change from TEXT to REAL
avg REAL,
era REAL,
whip REAL,
-- etc.
```

**Impact:** Improved query performance, more efficient storage, native numeric operations

---

### 2. Missing CHECK Constraints on Boolean Fields
**Problem:** INTEGER fields representing booleans (0/1) have no constraints, allowing invalid values.

**Affected columns:**
- `teams.active`, `players.active`
- `game_pitching.isStartingPitcher`
- `at_bats.isComplete`, `hasReview`, `hasOut`, `isScoringPlay`
- `pitches.isInPlay`, `isStrike`, `isBall`

**Recommendation:**
```sql
active INTEGER CHECK (active IN (0, 1)),
isStartingPitcher INTEGER CHECK (isStartingPitcher IN (0, 1)),
```

**Impact:** Prevents invalid data, catches transformation bugs early

---

### 3. Data Denormalization Inconsistency Risk
**Problem:** Home plate umpire stored in both `games` table (`umpire_HP_id`, `umpire_HP_name`) AND `game_officials` table, creating potential for data inconsistency.

**Recommendation:**
- **Option A (Preferred):** Remove `umpire_HP_id` and `umpire_HP_name` from `games` table
- **Option B:** Add trigger to keep values in sync
- **Option C:** Document which source is canonical

**Impact:** Single source of truth, eliminates potential conflicts

---

## ⚠️ Performance Issues

### 4. Missing Critical Indexes

Based on query patterns in `DATABASE_GUIDE.md`, these indexes would significantly improve performance:

```sql
-- Games table - gameType='R' appears in almost every example query
CREATE INDEX idx_games_type ON games(gameType);
CREATE INDEX idx_games_state ON games(abstractGameState);
CREATE INDEX idx_games_season_type ON games(season, gameType);

-- Players table - name lookups are common
CREATE INDEX idx_players_name ON players(fullName);
CREATE INDEX idx_players_team ON players(currentTeam_id);
CREATE INDEX idx_players_active ON players(active);

-- Teams table
CREATE INDEX idx_teams_name ON teams(name);
CREATE INDEX idx_teams_abbr ON teams(abbreviation);

-- Game pitching - identifying starters (pitchingOrder=1)
CREATE INDEX idx_game_pitching_order ON game_pitching(pitchingOrder);
CREATE INDEX idx_game_pitching_player_game ON game_pitching(player_id, gamePk);

-- Game batting - player-centric queries
CREATE INDEX idx_game_batting_player_game ON game_batting(player_id, gamePk);

-- Pitches - pitch arsenal analysis
CREATE INDEX idx_pitches_pitcher_type ON pitches(pitcher_id, type_code);
CREATE INDEX idx_pitches_call ON pitches(call_code);
CREATE INDEX idx_pitches_game_atbat ON pitches(gamePk, atBatIndex);

-- Batted balls - exit velocity queries
CREATE INDEX idx_batted_balls_batter_ev ON batted_balls(batter_id, launchSpeed);
CREATE INDEX idx_batted_balls_game_atbat ON batted_balls(gamePk, atBatIndex);

-- At-bats
CREATE INDEX idx_at_bats_game_index ON at_bats(gamePk, atBatIndex);

-- Game officials - reverse lookups
CREATE INDEX idx_game_officials_official ON game_officials(official_id);

-- Sync log - time-based queries
CREATE INDEX idx_sync_log_started ON sync_log(started_at);
CREATE INDEX idx_sync_log_gamepk ON sync_log(gamePk);
```

**Impact:** 10-100x faster queries on common filter patterns

---

### 5. Consider Covering Indexes for Hot Queries

For frequently-run queries, covering indexes allow SQLite to answer entirely from the index:

```sql
-- Player batting stats aggregation (common pattern)
CREATE INDEX idx_game_batting_player_stats
  ON game_batting(player_id, gamePk, hits, homeRuns, rbi, strikeOuts, baseOnBalls);

-- Pitcher game scores (calculated frequently)
CREATE INDEX idx_game_pitching_starter_stats
  ON game_pitching(pitchingOrder, player_id, gamePk, outs, strikeOuts, hits, earnedRuns, baseOnBalls, homeRuns)
  WHERE pitchingOrder = 1;  -- Partial index for starters only

-- Exit velocity leaders (Statcast queries)
CREATE INDEX idx_batted_balls_ev_leaders
  ON batted_balls(batter_id, launchSpeed)
  WHERE launchSpeed IS NOT NULL;  -- Partial index
```

---

## 💡 Data Integrity Improvements

### 6. Missing Numeric Constraints
**Problem:** Counting statistics (hits, runs, strikeouts) can theoretically be negative.

**Recommendation:**
```sql
hits INTEGER CHECK (hits >= 0),
runs INTEGER CHECK (runs >= 0),
homeRuns INTEGER CHECK (homeRuns >= 0),
strikeOuts INTEGER CHECK (strikeOuts >= 0),
-- etc. for all counting stats
```

**Impact:** Catches data transformation bugs early

---

## 🔧 Technical Optimizations

### 7. SQLite-Specific Performance Settings

Consider adding these PRAGMA settings to `get_connection()`:

```python
conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes, still safe with WAL
conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory
conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
```

---

### 8. Future: Consider Table Partitioning at Scale

**Current status:** Not urgent (142 games, ~40K pitches)

**Trigger point:** When `pitches` table exceeds ~10 million rows

**Strategy:** Partition largest tables by season:
- `pitches_2024`, `pitches_2023`, etc.
- `batted_balls_2024`, `batted_balls_2023`, etc.

**Benefits:**
- Faster queries when filtering by season
- Easier archival of old data
- Better index performance

---

## ✅ What You're Doing Right

1. **Foreign key constraints** - Properly defined relationships
2. **UNIQUE constraints** - Prevent duplicates at natural keys
3. **Metadata tracking** - Excellent data provenance (`_written_at`, `_git_hash`, `_version`)
4. **MLB naming preservation** - Transparent API-to-DB mapping
5. **WAL mode** - Modern SQLite best practice
6. **Flattened nested objects** - Good denormalization (`primaryPosition_code` vs separate table)
7. **Index coverage on FKs** - Most foreign keys have corresponding indexes

---

## 📋 Implementation Priority

### Phase 1: High Impact, Low Effort
- [ ] Add indexes on `games.gameType`, `games.abstractGameState`, `players.fullName`
- [ ] Add CHECK constraints on boolean fields
- [ ] Change rate stat columns from TEXT to REAL
- [ ] Resolve umpire denormalization (decide on approach)

### Phase 2: Performance Optimization
- [ ] Add composite indexes for common query patterns
- [ ] Add partial indexes for filtered queries
- [ ] Implement covering indexes for hot queries
- [ ] Add numeric constraints (CHECK >= 0)

### Phase 3: Advanced Optimization
- [ ] Add SQLite PRAGMA optimizations
- [ ] Monitor query performance as data grows
- [ ] Consider table partitioning when approaching millions of rows

### Keep As-Is
- ✅ Metadata columns (valuable for research)
- ✅ `inningsPitched` as TEXT (use `outs` for calculations)
- ✅ Current normalization level (good balance)

---

## Files to Update

- `src/mlb_stats/db/schema.py` - Table definitions
- `tests/unit/test_schema.py` - Schema validation tests
- `docs/DATABASE_GUIDE.md` - Update with new indexes
- Migration script needed for existing databases

---

## References

- Database schema: `src/mlb_stats/db/schema.py`
- Query guide: `docs/DATABASE_GUIDE.md`
- Data dictionary: `docs/DATA_DICTIONARY.md`
- Project plan: `docs/PROJECT_PLAN.md`
