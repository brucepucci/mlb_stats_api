"""Date handling utilities for MLB Stats Collector."""

from datetime import date, datetime


def parse_date(date_str: str) -> date:
    """Parse YYYY-MM-DD string to date object.

    Parameters
    ----------
    date_str : str
        Date string in YYYY-MM-DD format

    Returns
    -------
    date
        Parsed date object

    Raises
    ------
    ValueError
        If date string is not in valid format
    """
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_date(date_obj: date) -> str:
    """Format date object to YYYY-MM-DD string.

    Parameters
    ----------
    date_obj : date
        Date object to format

    Returns
    -------
    str
        Date string in YYYY-MM-DD format
    """
    return date_obj.strftime("%Y-%m-%d")


def season_dates(year: int) -> tuple[str, str]:
    """Get approximate start and end dates for MLB season.

    Parameters
    ----------
    year : int
        Season year (e.g., 2024)

    Returns
    -------
    tuple[str, str]
        (start_date, end_date) in YYYY-MM-DD format

    Notes
    -----
    Uses February 15 to November 15 to capture spring training
    through World Series. Actual dates vary by year.
    """
    return (f"{year}-02-15", f"{year}-11-15")
