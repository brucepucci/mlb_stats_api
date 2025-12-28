"""Logging configuration for MLB Stats Collector."""

import logging


def configure_logging(verbosity: int = 0) -> None:
    """Configure logging based on verbosity level.

    Parameters
    ----------
    verbosity : int
        Verbosity level:
        - -1 = ERROR (--quiet flag, errors only)
        - 0 = WARNING (default, progress bar + summary)
        - 1 = INFO (which games/players processing)
        - 2+ = DEBUG (API calls, SQL statements)
    """
    level = {
        -1: logging.ERROR,  # --quiet flag
        0: logging.WARNING,
        1: logging.INFO,
    }.get(verbosity, logging.DEBUG)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
