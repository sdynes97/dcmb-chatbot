"""
Integration test: simulates the full web chat flow → Claude → reply.
All external services (Azure, Anthropic) are mocked.
"""
import json
from unittest.mock import patch, MagicMock

import azure.functions as func

import function_app


def test_chat_endpoint_end_to_end(sample_event, sample_eta):
    with (
        patch("services.schedule_service.get_all_events", return_value=[sample_event]),
        patch("services.location_service.get_current_eta", return_value=sample_eta),
        patch("anthropic.Anthropic") as MockAnthropic,
    ):
        mock_instance = MockAnthropic.return_value
        mock_instance.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Drop-off is at Band Room Parking Lot, Door 7")]
        )
        import services.claude_service as cs
        cs._client = mock_instance

        req = func.HttpRequest(
            method="POST",
            url="https://func.example.com/api/chat",
            body=json.dumps({"message": "Where do I pick up my kid?"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = function_app.chat(req)
        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert "Door 7" in data["reply"]
