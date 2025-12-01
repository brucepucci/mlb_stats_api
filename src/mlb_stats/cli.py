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


if __name__ == "__main__":
    cli()
