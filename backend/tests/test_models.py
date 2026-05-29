from models.event import ScheduleEvent
from models.location_update import ETAUpdate


def test_schedule_event_roundtrip():
    event = ScheduleEvent(
        partition_key="2025",
        row_key="2025-09-06_football-lincoln",
        event_type="football_game",
        event_name="Home vs. Lincoln",
        event_date="2025-09-06",
        call_time="17:30",
        performance_time="19:00",
        estimated_return="22:30",
        location_name="Davenport Central Stadium",
        location_address="1120 Main St, Davenport, IA",
        drop_off_location="Band Room Parking Lot, Door 7",
        is_away=False,
        notes="Full uniform",
    )
    entity = event.to_table_entity()
    restored = ScheduleEvent.from_table_entity(entity)
    assert restored.event_name == event.event_name
    assert restored.call_time == event.call_time
    assert restored.is_away == event.is_away


def test_schedule_event_readable_text(sample_event):
    text = sample_event.to_readable_text()
    assert "Home vs. Lincoln" in text
    assert "17:30" in text
    assert "Band Room Parking Lot" in text


def test_eta_update_roundtrip():
    eta = ETAUpdate(
        eta_time="2025-09-06T22:45:00",
        message="On the way",
        updated_at="2025-09-06T21:58:00Z",
    )
    entity = eta.to_table_entity()
    restored = ETAUpdate.from_table_entity(entity)
    assert restored.message == eta.message
    assert restored.eta_time == eta.eta_time


def test_eta_readable_text():
    eta = ETAUpdate(
        eta_time="2025-09-06T22:45:00",
        message="Leaving Lincoln now, ~45 min",
        updated_at="2025-09-06T21:58:00Z",
    )
    text = eta.to_readable_text()
    assert "Leaving Lincoln now" in text
    assert "21:58" in text
