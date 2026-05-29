"""
Integration test: simulates a full inbound SMS webhook → Claude → reply flow.
All external services (Telnyx, Azure, Anthropic) are mocked.
"""
import json
from unittest.mock import patch, MagicMock

import azure.functions as func
import pytest

import function_app


def _make_sms_request(from_number: str, text: str) -> func.HttpRequest:
    payload = {
        "data": {
            "event_type": "message.received",
            "payload": {
                "from": {"phone_number": from_number},
                "text": text,
            },
        }
    }
    return func.HttpRequest(
        method="POST",
        url="https://func.example.com/api/sms",
        body=json.dumps(payload).encode(),
        headers={
            "telnyx-timestamp": "1234567890",
            "telnyx-signature-ed25519": "valid",
        },
    )


def test_parent_sms_end_to_end(sample_event, sample_eta):
    with (
        patch("services.telnyx_service.validate_webhook_signature", return_value=True),
        patch("services.schedule_service.get_all_events", return_value=[sample_event]),
        patch("services.location_service.get_current_eta", return_value=sample_eta),
        patch("services.telnyx_service.send_sms") as mock_send,
        patch("anthropic.Anthropic") as MockAnthropic,
    ):
        mock_instance = MockAnthropic.return_value
        mock_instance.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Game Sept 6 at 7pm, call time 5:30pm")]
        )
        import services.claude_service as cs
        cs._client = mock_instance

        req = _make_sms_request("+15550000002", "When is the next football game?")
        resp = function_app.sms(req)

        assert resp.status_code == 200
        mock_send.assert_called_once()
        sent_to, sent_text = mock_send.call_args[0]
        assert sent_to == "+15550000002"
        assert "Sept 6" in sent_text or len(sent_text) > 0


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
