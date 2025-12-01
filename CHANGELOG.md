# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Reference tables: `teams`, `venues`, `players`
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
