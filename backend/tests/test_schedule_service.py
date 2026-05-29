from unittest.mock import MagicMock, patch
import pytest

import services.schedule_service as schedule_service


@pytest.fixture(autouse=True)
def clear_cache():
    schedule_service._cache = None
    yield
    schedule_service._cache = None


def _make_entity(row_key: str, event_date: str) -> dict:
    return {
        "PartitionKey": "2025",
        "RowKey": row_key,
        "event_type": "football_game",
        "event_name": "Test Event",
        "event_date": event_date,
        "call_time": "17:00",
        "performance_time": "19:00",
        "estimated_return": "22:00",
        "location_name": "Stadium",
        "location_address": "123 Main St",
        "drop_off_location": "Door 7",
        "is_away": False,
        "notes": "",
    }


def test_get_all_events_sorts_by_date():
    entities = [
        _make_entity("2025-09-20_game", "2025-09-20"),
        _make_entity("2025-09-06_game", "2025-09-06"),
        _make_entity("2025-09-13_game", "2025-09-13"),
    ]
    mock_client = MagicMock()
    mock_client.list_entities.return_value = iter(entities)
    with patch("services.schedule_service._get_table_client", return_value=mock_client):
        events = schedule_service.get_all_events()
        dates = [e.event_date for e in events]
        assert dates == sorted(dates)


def test_get_all_events_caches_result():
    entities = [_make_entity("2025-09-06_game", "2025-09-06")]
    mock_client = MagicMock()
    mock_client.list_entities.return_value = iter(entities)
    with patch("services.schedule_service._get_table_client", return_value=mock_client):
        schedule_service.get_all_events()
        schedule_service.get_all_events()
        assert mock_client.list_entities.call_count == 1


def test_upsert_event_invalidates_cache(sample_event):
    schedule_service._cache = [sample_event]
    mock_client = MagicMock()
    with patch("services.schedule_service._get_table_client", return_value=mock_client):
        schedule_service.upsert_event(sample_event)
        assert schedule_service._cache is None
        mock_client.upsert_entity.assert_called_once()


def test_delete_event_invalidates_cache(sample_event):
    schedule_service._cache = [sample_event]
    mock_client = MagicMock()
    with patch("services.schedule_service._get_table_client", return_value=mock_client):
        schedule_service.delete_event("2025", "2025-09-06_game")
        assert schedule_service._cache is None


def test_eta_rows_excluded():
    entities = [
        _make_entity("2025-09-06_game", "2025-09-06"),
        {"PartitionKey": "eta", "RowKey": "current", "message": "ETA update"},
    ]
    mock_client = MagicMock()
    mock_client.list_entities.return_value = iter(entities)
    with patch("services.schedule_service._get_table_client", return_value=mock_client):
        events = schedule_service.get_all_events()
        assert len(events) == 1
        assert events[0].partition_key == "2025"
