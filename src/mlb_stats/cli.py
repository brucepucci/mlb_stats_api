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
@click.pass_context
def sync(
    ctx: click.Context,
    game_pk: int | None,
    start_date: str | None,
    end_date: str | None,
    season: int | None,
) -> None:
    """Sync all game data from MLB Stats API.

    Fetches games, teams, players, and batting/pitching stats.
    Can sync a single game by gamePk, a date range, or an entire season.

    Examples:

        mlb-stats sync 745927

        mlb-stats sync --start-date 2024-07-01 --end-date 2024-07-07

        mlb-stats sync --season 2024
    """
    from mlb_stats.api.client import MLBStatsClient
    from mlb_stats.collectors.boxscore import (
        sync_boxscore,
        sync_boxscores_for_date_range,
    )
    from mlb_stats.utils.dates import parse_date, season_dates

    # Validate options
    if game_pk is not None:
        if start_date or end_date or season:
            raise click.UsageError(
                "Cannot use gamePk with --start-date/--end-date/--season"
            )
    elif season:
        if start_date or end_date:
            raise click.UsageError("Cannot use --season with --start-date/--end-date")
        start_date, end_date = season_dates(season)
    elif not (start_date and end_date):
        raise click.UsageError(
            "Must provide gamePk, --season, or both --start-date and --end-date"
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
        else:
            # Date range sync
            def progress(current: int, total: int) -> None:
                click.echo(f"\rSyncing game {current}/{total}...", nl=False)

            click.echo(f"Syncing games from {start_date} to {end_date}")

            success, failures = sync_boxscores_for_date_range(
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
