"""Write metadata helpers for database provenance tracking."""

import subprocess
from datetime import datetime, timezone
from functools import lru_cache

from mlb_stats import __version__


@lru_cache(maxsize=1)
def get_git_hash() -> str:
    """Get current git commit hash.

    Returns
    -------
    str
        Short git hash (7 characters), or 'unknown' if not in a git repo
        or git is not available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return "unknown"


def get_write_metadata() -> dict[str, str]:
    """Get metadata dict for database writes.

    Every row written to the database should include this metadata
    for provenance tracking.

    Returns
    -------
    dict
        Contains:
        - _written_at: ISO8601 UTC timestamp
        - _git_hash: Short git commit hash
        - _version: Package version

    Examples
    --------
    >>> row_data = {"id": 123, "name": "Test"}
    >>> row_data.update(get_write_metadata())
    >>> # row_data now includes _written_at, _git_hash, _version
    """
    return {
        "_written_at": datetime.now(timezone.utc).isoformat(),
        "_git_hash": get_git_hash(),
        "_version": __version__,
    }
