"""Lightweight input validators."""
import re
from datetime import datetime

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Table Storage key chars: disallow / \ # ? and control chars
_KEY_RE = re.compile(r"^[^/\\#?\x00-\x1f]{1,256}$")


def is_valid_date(value: str) -> bool:
    """True if value is a real YYYY-MM-DD calendar date."""
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_iso_datetime(value: str) -> bool:
    """True if value parses as an ISO-8601 datetime."""
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def is_valid_table_key(value: str) -> bool:
    """True if value is safe to use as an Azure Table partition/row key."""
    return isinstance(value, str) and bool(_KEY_RE.match(value))
