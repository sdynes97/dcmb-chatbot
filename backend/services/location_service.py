import os
from typing import Optional
from datetime import datetime, timezone

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

from models.location_update import ETAUpdate

_TABLE_NAME = os.environ.get("TABLE_STORAGE_TABLE_NAME", "bandschedule")
_CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")


def _get_table_client():
    service = TableServiceClient.from_connection_string(_CONN_STR)
    try:
        service.create_table(_TABLE_NAME)
    except ResourceExistsError:
        pass
    return service.get_table_client(_TABLE_NAME)


def get_current_eta() -> Optional[ETAUpdate]:
    client = _get_table_client()
    try:
        entity = client.get_entity(
            partition_key=ETAUpdate.PARTITION_KEY,
            row_key=ETAUpdate.ROW_KEY,
        )
        return ETAUpdate.from_table_entity(entity)
    except ResourceNotFoundError:
        return None


def set_eta(message: str, eta_time: str = "", event_row_key: str = "") -> ETAUpdate:
    now = datetime.now(timezone.utc).isoformat()
    update = ETAUpdate(
        eta_time=eta_time,
        message=message,
        updated_at=now,
        event_row_key=event_row_key,
    )
    client = _get_table_client()
    client.upsert_entity(update.to_table_entity())
    return update


def clear_eta() -> None:
    client = _get_table_client()
    try:
        client.delete_entity(
            partition_key=ETAUpdate.PARTITION_KEY,
            row_key=ETAUpdate.ROW_KEY,
        )
    except ResourceNotFoundError:
        pass
