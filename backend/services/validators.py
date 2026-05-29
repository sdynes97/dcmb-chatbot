"""Lightweight input validators shared across handlers."""
import re
from datetime import datetime

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
# Table Storage key chars: disallow / \ # ? and control chars
_KEY_RE = re.compile(r"^[^/\\#?\x00-\x1f]{1,256}$")

_ALLOWED_EVENT_TYPES = {
    "football_game", "competition", "parade", "rehearsal", "concert",
}


def is_valid_date(value: str) -> bool:
    """True if value is a real YYYY-MM-DD calendar date."""
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_time(value: str) -> bool:
    """True if value is HH:MM 24-hour, or the literal 'N/A'."""
    if value == "N/A":
        return True
    return isinstance(value, str) and bool(_TIME_RE.match(value))


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


def is_valid_event_type(value: str) -> bool:
    return value in _ALLOWED_EVENT_TYPES


def validate_event(body: dict) -> list:
    """Return a list of human-readable validation errors for an event payload.

    An empty list means the payload is valid. Required-field presence is
    assumed to be checked separately by the caller.
    """
    errors = []
    if not is_valid_table_key(body.get("partition_key", "")):
        errors.append("partition_key contains invalid characters")
    if not is_valid_table_key(body.get("row_key", "")):
        errors.append("row_key contains invalid characters")
    if not is_valid_event_type(body.get("event_type", "")):
        errors.append("event_type is not one of the allowed values")
    if not is_valid_date(body.get("event_date", "")):
        errors.append("event_date must be a valid YYYY-MM-DD date")
    for time_field in ("call_time", "performance_time", "estimated_return"):
        if not is_valid_time(body.get(time_field, "")):
            errors.append(f"{time_field} must be HH:MM (24-hour) or 'N/A'")
    return errors
