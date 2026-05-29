import os
import sys
from unittest.mock import patch

import pytest

# Ensure backend/ is on the path so imports work without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment variables before any module-level code runs
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELNYX_API_KEY", "test-key")
os.environ.setdefault("TELNYX_PUBLIC_KEY", "dGVzdC1wdWJsaWMta2V5LWJhc2U2NA==")
os.environ.setdefault("TELNYX_PHONE_NUMBER", "+15550000001")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("DIRECTOR_PHONE", "+15550000099")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
os.environ.setdefault("TABLE_STORAGE_TABLE_NAME", "bandschedule")
os.environ.setdefault("FRONTEND_ORIGIN", "https://example.github.io")


@pytest.fixture
def sample_event():
    from models.event import ScheduleEvent
    return ScheduleEvent(
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
        notes="Full uniform required",
    )


@pytest.fixture
def sample_eta():
    from models.location_update import ETAUpdate
    return ETAUpdate(
        eta_time="2025-09-06T22:45:00",
        message="Leaving Lincoln now, ~45 min",
        updated_at="2025-09-06T21:58:00Z",
        event_row_key="2025-09-06_football-lincoln",
    )


@pytest.fixture
def mock_schedule_service(sample_event):
    with patch("services.schedule_service.get_all_events", return_value=[sample_event]) as m:
        yield m


@pytest.fixture
def mock_location_service(sample_eta):
    with patch("services.location_service.get_current_eta", return_value=sample_eta) as m:
        yield m


@pytest.fixture
def mock_claude_service():
    with patch("services.claude_service.get_reply", return_value="Test reply from Claude") as m:
        yield m


@pytest.fixture
def mock_telnyx_service():
    with patch("services.telnyx_service.send_sms", return_value={"data": {"id": "msg-1"}}) as m:
        yield m
