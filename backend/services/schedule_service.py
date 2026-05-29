import os
from typing import List, Optional

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from models.event import ScheduleEvent

_TABLE_NAME = os.environ.get("TABLE_STORAGE_TABLE_NAME", "bandschedule")
_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

# Simple module-level cache — lives as long as the Function instance
_cache: Optional[List[ScheduleEvent]] = None


def _get_table_client():
    service = TableServiceClient.from_connection_string(_CONN_STR)
    try:
        service.create_table(_TABLE_NAME)
    except ResourceExistsError:
        pass
    return service.get_table_client(_TABLE_NAME)


def get_all_events(season: Optional[str] = None) -> List[ScheduleEvent]:
    global _cache
    if _cache is not None:
        return _cache

    client = _get_table_client()
    if season:
        entities = client.query_entities(f"PartitionKey eq '{season}'")
    else:
        entities = client.list_entities()

    events = [ScheduleEvent.from_table_entity(e) for e in entities
              if e.get("PartitionKey") != "eta"]
    events.sort(key=lambda e: (e.event_date, e.call_time))
    _cache = events
    return events


def upsert_event(event: ScheduleEvent) -> None:
    global _cache
    _cache = None  # invalidate cache
    client = _get_table_client()
    client.upsert_entity(event.to_table_entity())


def delete_event(partition_key: str, row_key: str) -> None:
    global _cache
    _cache = None
    client = _get_table_client()
    client.delete_entity(partition_key=partition_key, row_key=row_key)


def get_event(partition_key: str, row_key: str) -> Optional[ScheduleEvent]:
    client = _get_table_client()
    try:
        entity = client.get_entity(partition_key=partition_key, row_key=row_key)
        return ScheduleEvent.from_table_entity(entity)
    except ResourceNotFoundError:
        return None


def invalidate_cache() -> None:
    global _cache
    _cache = None
