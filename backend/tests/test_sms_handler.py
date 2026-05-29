import json
from unittest.mock import patch, MagicMock

import azure.functions as func
import pytest

import handlers.sms_handler as sms_handler


def _telnyx_payload(from_number: str, text: str) -> dict:
    return {
        "data": {
            "event_type": "message.received",
            "payload": {
                "from": {"phone_number": from_number},
                "text": text,
            },
        }
    }


def _make_request(payload: dict, valid_sig: bool = True) -> func.HttpRequest:
    body = json.dumps(payload).encode()
    return func.HttpRequest(
        method="POST",
        url="https://func.example.com/api/sms",
        body=body,
        headers={
            "telnyx-timestamp": "1234567890",
            "telnyx-signature-ed25519": "valid-sig",
        },
    )


@pytest.fixture(autouse=True)
def mock_sig_validation():
    with patch("services.telnyx_service.validate_webhook_signature", return_value=True):
        yield


def test_parent_query_sends_sms(mock_schedule_service, mock_location_service, mock_claude_service, mock_telnyx_service):
    req = _make_request(_telnyx_payload("+15550000002", "What time is the game?"))
    resp = sms_handler.handle(req)
    assert resp.status_code == 200
    mock_telnyx_service.assert_called_once()
    args = mock_telnyx_service.call_args[0]
    assert args[0] == "+15550000002"
    assert args[1] == "Test reply from Claude"


def test_director_update_saves_eta(mock_telnyx_service):
    with patch("services.location_service.set_eta") as mock_set_eta:
        mock_set_eta.return_value = MagicMock()
        req = _make_request(_telnyx_payload("+15550000099", "Leaving Lincoln, home by 10:30"))
        resp = sms_handler.handle(req)
        assert resp.status_code == 200
        mock_set_eta.assert_called_once()
        call_args = mock_set_eta.call_args
        assert "Leaving Lincoln" in call_args[1]["message"] or "Leaving Lincoln" in str(call_args)


def test_invalid_signature_returns_403():
    with patch("services.telnyx_service.validate_webhook_signature", return_value=False):
        req = _make_request(_telnyx_payload("+15550000002", "Hello"))
        resp = sms_handler.handle(req)
        assert resp.status_code == 403


def test_non_message_event_returns_200():
    payload = {"data": {"event_type": "message.sent", "payload": {}}}
    req = _make_request(payload)
    resp = sms_handler.handle(req)
    assert resp.status_code == 200


def test_long_reply_truncated(mock_schedule_service, mock_location_service, mock_telnyx_service):
    long_reply = "x" * 200
    with patch("services.claude_service.get_reply", return_value=long_reply):
        req = _make_request(_telnyx_payload("+15550000002", "?"))
        sms_handler.handle(req)
        sent_text = mock_telnyx_service.call_args[0][1]
        assert len(sent_text) <= 160
        assert sent_text.endswith("...")
