from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import checkin_service
from models import CheckIn


def test_record_checkin_uses_local_date_and_time():
    client = MagicMock()
    # 02:30 UTC on Oct 29 is 21:30 on Oct 28 in Davenport (CDT).
    at = datetime(2026, 10, 29, 2, 30, tzinfo=timezone.utc)
    with patch.object(checkin_service, "_get_table_client", return_value=client):
        c = checkin_service.record_checkin("Jane Smith", "Concessions", "v1", at=at)
    assert c.check_in_date == "2026-10-28"
    assert c.check_in_time == "21:30:00"
    entity = client.upsert_entity.call_args.args[0]
    assert entity["PartitionKey"] == "checkin"
    assert entity["volunteer_name"] == "Jane Smith"


def test_add_volunteers_skips_duplicates():
    client = MagicMock()
    client.query_entities.return_value = [{"PartitionKey": "roster", "RowKey": "v1", "name": "Jane Smith"}]
    with patch.object(checkin_service, "_get_table_client", return_value=client):
        added = checkin_service.add_volunteers(["jane smith", "Al B", "al b"])
    assert [v.name for v in added] == ["Al B"]
    assert client.upsert_entity.call_count == 1


def test_csv_escapes_formula_names():
    c = CheckIn("rk", "2026-10-28", "10:00:00", "2026-10-28T15:00:00+00:00", "=HYPERLINK(1)", "General")
    out = checkin_service.checkins_to_csv([c])
    assert "'=HYPERLINK(1)" in out
    assert ",yes," in out  # walk-in (no volunteer_id)
