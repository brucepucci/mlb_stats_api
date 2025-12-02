# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-12-01

### Added

- Enhanced Statcast fields in `batted_balls` table:
  - `isBarrel` - MLB's official barrel calculation (1 if barrel, 0 if not)
  - `batSpeed` - Bat speed in mph (2024+ games only)
  - `isSwordSwing` - Weak contact indicator (2024+ games only)
- Documentation for `hitProbability` (xBA) field (already captured, now documented)

### Changed

- Schema version bumped to 1.1.0

### Breaking Changes

- Existing databases must be re-initialized (`mlb-stats init-db` on a fresh database)

## [1.0.0] - 2024-12-01

### Added

- Initial project structure with `uv` package management
- HTTP client (`MLBStatsClient`) with:
  - Request retries with exponential backoff
  - Configurable rate limiting
  - Response caching for final game data
  - User-Agent header
- File-based JSON cache for game data (not reference data)
- Full database schema with all 11 tables:
  - Reference tables: `teams`, `players`
  - Game tables: `games`, `game_officials`, `game_batting`, `game_pitching`
  - Pitch-level tables: `pitches`, `at_bats`, `batted_balls`
  - Operational: `sync_log`, `_meta`
- CLI skeleton with Click:
  - `--version` flag
  - `--help` command
  - `init-db` command to create database
  - Verbosity options (`-v`, `-vv`, `--quiet`)
- Logging infrastructure with configurable verbosity
- Write metadata helper for provenance tracking
- pytest infrastructure with fixtures
- GitHub Actions CI workflow
