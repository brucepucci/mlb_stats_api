"""CLI entry point for MLB Stats Collector."""

import click

from mlb_stats import __version__
from mlb_stats.db.connection import init_db as do_init_db
from mlb_stats.utils.logging import configure_logging


@click.group()
@click.version_option(version=__version__, prog_name="mlb-stats")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
@click.option(
    "--quiet",
    is_flag=True,
    help="Suppress output (ERROR level only)",
)
@click.option(
    "--db-path",
    default="./data/mlb_stats.db",
    envvar="MLB_STATS_DB_PATH",
    help="Path to SQLite database file",
    type=click.Path(),
)
@click.option(
    "--cache-dir",
    default="./cache",
    envvar="MLB_STATS_CACHE_DIR",
    help="Directory for caching API responses",
    type=click.Path(),
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: int,
    quiet: bool,
    db_path: str,
    cache_dir: str,
) -> None:
    """MLB Stats Collector - Fetch and store MLB game data.

    Collects game schedules, box scores, and pitch-level data from the
    MLB Stats API and stores it in a SQLite database.
    """
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path
    ctx.obj["cache_dir"] = cache_dir
    ctx.obj["verbose"] = verbose

    # Configure logging based on verbosity
    if quiet:
        verbosity = -1  # ERROR level only
    else:
        verbosity = verbose

    configure_logging(verbosity)


@cli.command("init-db")
@click.pass_context
def init_db(ctx: click.Context) -> None:
    """Initialize the database with all tables.

    Creates the SQLite database file and all required tables
    (teams, players, games, pitches, etc.).
    """
    db_path = ctx.obj["db_path"]
    conn = do_init_db(db_path)
    conn.close()
    click.echo(f"Database initialized at {db_path}")


@cli.command("sync")
@click.argument("game_pk", type=int, required=False)
@click.option(
    "--start-date",
    type=str,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end-date",
    type=str,
    help="End date (YYYY-MM-DD)",
)
@click.option(
    "--season",
    type=int,
    help="Season year (e.g., 2024). Alternative to date range.",
)
@click.option(
    "--all",
    "sync_all",
    is_flag=True,
    help="Sync all data from 2008 to today (PITCHf/x era).",
)
@click.option(
    "--start-season",
    type=int,
    help="Start season (e.g., 2008). Can be used alone or with --end-season.",
)
@click.option(
    "--end-season",
    type=int,
    help="End season (e.g., 2024). Can be used alone or with --start-season.",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    help="Always fetch schedule from API, ignoring games already in database.",
)
@click.pass_context
def sync(
    ctx: click.Context,
    game_pk: int | None,
    start_date: str | None,
    end_date: str | None,
    season: int | None,
    sync_all: bool,
    start_season: int | None,
    end_season: int | None,
    force_refresh: bool,
) -> None:
    """Sync all game data from MLB Stats API.

    Fetches games, teams, players, and batting/pitching stats.
    Can sync a single game by gamePk, a date range, an entire season,
    or a range of seasons.

    Examples:

        mlb-stats sync 745927

        mlb-stats sync --start-date 2024-07-01 --end-date 2024-07-07

        mlb-stats sync --season 2024

        mlb-stats sync --start-season 2010 --end-season 2015

        mlb-stats sync --start-season 2018

        mlb-stats sync --all --force-refresh
    """
    from datetime import date

    from mlb_stats.api.client import MLBStatsClient
    from mlb_stats.collectors.boxscore import (
        sync_boxscore,
        sync_boxscores_for_date_range,
    )
    from mlb_stats.utils.dates import parse_date, season_dates

    # Validate options
    if game_pk is not None:
        if start_date or end_date or season or sync_all or start_season or end_season:
            raise click.UsageError("Cannot use gamePk with date/season options")
    elif sync_all:
        if start_date or end_date or season or start_season or end_season:
            raise click.UsageError("Cannot use --all with other date/season options")
        # Set to full PITCHf/x era (2008-present)
        current_year = date.today().year
        start_season = 2008
        end_season = current_year
    elif start_season is not None or end_season is not None:
        if start_date or end_date or season:
            raise click.UsageError(
                "Cannot use --start-season/--end-season with date range or --season"
            )
        # Default start to 2008, end to current year
        current_year = date.today().year
        start_season = start_season or 2008
        end_season = end_season or current_year

        # Validate range
        if start_season > end_season:
            raise click.UsageError(
                f"--start-season ({start_season}) cannot be after --end-season ({end_season})"
            )
        if start_season < 2008:
            raise click.UsageError(
                "Data is only available from 2008 onwards (PITCHf/x era)"
            )
    elif season:
        if start_date or end_date:
            raise click.UsageError("Cannot use --season with --start-date/--end-date")
        start_date, end_date = season_dates(season)
    elif not (start_date and end_date):
        raise click.UsageError(
            "Must provide gamePk, --season, --all, season range, or both --start-date and --end-date"
        )

    # Validate date format if provided
    if start_date and end_date:
        try:
            parse_date(start_date)
            parse_date(end_date)
        except ValueError as e:
            raise click.UsageError(f"Invalid date format: {e}")

    db_path = ctx.obj["db_path"]
    cache_dir = ctx.obj["cache_dir"]

    # Initialize database if needed
    conn = do_init_db(db_path)

    # Create client
    client = MLBStatsClient(cache_dir=cache_dir)

    def sync_season_range(start_year: int, end_year: int) -> tuple[int, int]:
        """Sync a range of seasons year-by-year.

        Parameters
        ----------
        start_year : int
            First season to sync (inclusive)
        end_year : int
            Last season to sync (inclusive)

        Returns
        -------
        tuple[int, int]
            (total_success, total_failures) across all seasons
        """
        total_success = 0
        total_failures = 0

        for year in range(start_year, end_year + 1):
            season_start, season_end = season_dates(year)
            click.echo(f"\n=== Syncing {year} season ===")

            def progress(current: int, total: int) -> None:
                click.echo(f"\r[{year}] Syncing game {current}/{total}...", nl=False)

            success, failures = sync_boxscores_for_date_range(
                client,
                conn,
                season_start,
                season_end,
                progress_callback=progress,
                force_refresh=force_refresh,
            )
            click.echo()
            click.echo(f"[{year}] {success} games synced, {failures} failures")
            total_success += success
            total_failures += failures

        return total_success, total_failures

    try:
        if game_pk is not None:
            # Single game sync
            click.echo(f"Syncing game {game_pk}")
            success = sync_boxscore(client, conn, game_pk)
            if success:
                click.echo("Sync complete")
            else:
                click.echo("Sync failed (game may not have started)")
                ctx.exit(1)
        elif sync_all or (start_season is not None and end_season is not None):
            # Sync season range (either --all or --start-season/--end-season)
            success, failures = sync_season_range(start_season, end_season)

            click.echo("\n=== All seasons complete ===")
            click.echo(f"Total: {success} games synced, {failures} failures")

            if failures > 0:
                ctx.exit(1)
        else:
            # Date range sync
            def progress(current: int, total: int) -> None:
                click.echo(f"\rSyncing game {current}/{total}...", nl=False)

            click.echo(f"Syncing games from {start_date} to {end_date}")

            success, failures = sync_boxscores_for_date_range(
                client,
                conn,
                start_date,
                end_date,
                progress_callback=progress,
                force_refresh=force_refresh,
            )

            # Clear progress line and print summary
            click.echo()
            click.echo(f"Sync complete: {success} games synced, {failures} failures")

            if failures > 0:
                ctx.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    cli()
