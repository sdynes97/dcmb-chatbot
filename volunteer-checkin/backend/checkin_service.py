import csv
import io
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from models import Activity, CheckIn, Volunteer

_TABLE_NAME = os.environ.get("TABLE_NAME", "volunteercheckins")
_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
# Davenport, IA. Check-in date/time columns are recorded in this zone.
_TZ = ZoneInfo(os.environ.get("KIOSK_TIMEZONE", "America/Chicago"))


def _get_table_client():
    service = TableServiceClient.from_connection_string(_CONN_STR)
    try:
        service.create_table(_TABLE_NAME)
    except ResourceExistsError:
        pass
    return service.get_table_client(_TABLE_NAME)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _sorted_by_name(items):
    return sorted(items, key=lambda x: x.name.lower())


# ── Roster ───────────────────────────────────────────────────────────────────

def list_volunteers() -> List[Volunteer]:
    client = _get_table_client()
    entities = client.query_entities(f"PartitionKey eq '{Volunteer.PARTITION_KEY}'")
    return _sorted_by_name(Volunteer.from_table_entity(e) for e in entities)


def get_volunteer(volunteer_id: str) -> Optional[Volunteer]:
    client = _get_table_client()
    try:
        return Volunteer.from_table_entity(
            client.get_entity(partition_key=Volunteer.PARTITION_KEY, row_key=volunteer_id)
        )
    except ResourceNotFoundError:
        return None


def add_volunteers(names: List[str]) -> List[Volunteer]:
    """Add names to the roster, skipping any that already exist (case-insensitive)."""
    existing = {v.name.lower() for v in list_volunteers()}
    client = _get_table_client()
    added = []
    for name in names:
        if name.lower() in existing:
            continue
        v = Volunteer(id=_new_id(), name=name)
        client.upsert_entity(v.to_table_entity())
        existing.add(name.lower())
        added.append(v)
    return added


def delete_volunteer(volunteer_id: str) -> None:
    _delete(Volunteer.PARTITION_KEY, volunteer_id)


# ── Activities ───────────────────────────────────────────────────────────────

def list_activities() -> List[Activity]:
    client = _get_table_client()
    entities = client.query_entities(f"PartitionKey eq '{Activity.PARTITION_KEY}'")
    return _sorted_by_name(Activity.from_table_entity(e) for e in entities)


def get_activity(activity_id: str) -> Optional[Activity]:
    client = _get_table_client()
    try:
        return Activity.from_table_entity(
            client.get_entity(partition_key=Activity.PARTITION_KEY, row_key=activity_id)
        )
    except ResourceNotFoundError:
        return None


def add_activity(name: str) -> Activity:
    a = Activity(id=_new_id(), name=name)
    _get_table_client().upsert_entity(a.to_table_entity())
    return a


def delete_activity(activity_id: str) -> None:
    _delete(Activity.PARTITION_KEY, activity_id)


def _delete(partition_key: str, row_key: str) -> None:
    client = _get_table_client()
    try:
        client.delete_entity(partition_key=partition_key, row_key=row_key)
    except ResourceNotFoundError:
        pass


# ── Check-ins ────────────────────────────────────────────────────────────────

def record_checkin(
    volunteer_name: str,
    activity: str,
    volunteer_id: str = "",
    at: Optional[datetime] = None,
) -> CheckIn:
    at_utc = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = at_utc.astimezone(_TZ)
    checkin = CheckIn(
        # Sortable by time; suffix avoids collisions when two people tap at once.
        row_key=f"{at_utc.strftime('%Y%m%dT%H%M%S%f')}_{_new_id()}",
        check_in_date=local.strftime("%Y-%m-%d"),
        check_in_time=local.strftime("%H:%M:%S"),
        checked_in_at_utc=at_utc.isoformat(),
        volunteer_name=volunteer_name,
        activity=activity,
        volunteer_id=volunteer_id,
    )
    _get_table_client().upsert_entity(checkin.to_table_entity())
    return checkin


def list_checkins(date_from: str, date_to: str) -> List[CheckIn]:
    """Check-ins with local date in [date_from, date_to], oldest first.

    Callers must validate both dates as YYYY-MM-DD before calling.
    """
    client = _get_table_client()
    entities = client.query_entities(
        "PartitionKey eq @pk and check_in_date ge @date_from and check_in_date le @date_to",
        parameters={"pk": CheckIn.PARTITION_KEY, "date_from": date_from, "date_to": date_to},
    )
    rows = [CheckIn.from_table_entity(e) for e in entities]
    return sorted(rows, key=lambda c: c.checked_in_at_utc)


def delete_checkin(row_key: str) -> None:
    _delete(CheckIn.PARTITION_KEY, row_key)


def checkins_to_csv(checkins: List[CheckIn]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CheckIn.CSV_FIELDS)
    writer.writeheader()
    for c in checkins:
        writer.writerow({k: _csv_safe(v) for k, v in c.to_csv_row().items()})
    return buf.getvalue()


def _csv_safe(value: str) -> str:
    # Prevent spreadsheet formula injection from typed walk-in names.
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def local_today() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%d")
