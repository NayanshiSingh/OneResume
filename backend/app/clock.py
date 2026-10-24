"""Current time in the form DateTime columns store it."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC, matching how DateTime columns are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
