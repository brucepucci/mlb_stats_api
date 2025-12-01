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
    (teams, venues, players, games, pitches, etc.).
    """
    db_path = ctx.obj["db_path"]
    conn = do_init_db(db_path)
    conn.close()
    click.echo(f"Database initialized at {db_path}")


@cli.group()
def sync() -> None:
    """Sync data from MLB Stats API."""
    pass


@sync.command("games")
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
@click.pass_context
def sync_games(
    ctx: click.Context,
    start_date: str | None,
    end_date: str | None,
    season: int | None,
) -> None:
    """Sync games for date range or season.

    Fetches game schedules, team and venue reference data, and game
    details from the MLB Stats API.

    Examples:

        mlb-stats sync games --start-date 2024-07-01 --end-date 2024-07-07

        mlb-stats sync games --season 2024
    """
    from mlb_stats.api.client import MLBStatsClient
    from mlb_stats.collectors.game import sync_games_for_date_range
    from mlb_stats.utils.dates import parse_date, season_dates

    # Validate options
    if season:
        if start_date or end_date:
            raise click.UsageError("Cannot use --season with --start-date/--end-date")
        start_date, end_date = season_dates(season)
    elif not (start_date and end_date):
        raise click.UsageError(
            "Must provide either --season or both --start-date and --end-date"
        )

    # Validate date format
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

    # Progress callback for simple text output
    def progress(current: int, total: int) -> None:
        click.echo(f"\rSyncing game {current}/{total}...", nl=False)

    click.echo(f"Syncing games from {start_date} to {end_date}")

    try:
        success, failures = sync_games_for_date_range(
            client, conn, start_date, end_date, progress_callback=progress
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
