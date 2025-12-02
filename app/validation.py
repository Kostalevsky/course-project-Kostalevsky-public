from datetime import datetime, timezone


def normalize_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
