import json
from unittest.mock import patch, MagicMock

import azure.functions as func
import pytest

import handlers.chat_handler as chat_handler


def _make_request(body: dict, method: str = "POST") -> func.HttpRequest:
    return func.HttpRequest(
        method=method,
        url="https://func.example.com/api/chat",
        body=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )


def test_chat_returns_reply(mock_schedule_service, mock_location_service, mock_claude_service):
    req = _make_request({"message": "When is the next game?"})
    resp = chat_handler.handle(req)
    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert data["reply"] == "Test reply from Claude"


def test_chat_missing_message():
    req = _make_request({"message": ""})
    resp = chat_handler.handle(req)
    assert resp.status_code == 400


def test_chat_invalid_json():
    req = func.HttpRequest(
        method="POST",
        url="https://func.example.com/api/chat",
        body=b"not json",
        headers={},
    )
    resp = chat_handler.handle(req)
    assert resp.status_code == 400


def test_chat_passes_history(mock_schedule_service, mock_location_service, mock_claude_service):
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
    req = _make_request({"message": "Next?", "history": history})
    resp = chat_handler.handle(req)
    assert resp.status_code == 200
    # Verify history was passed to claude service
    call_kwargs = mock_claude_service.call_args[1]
    assert len(call_kwargs["conversation_history"]) == 2


def test_chat_claude_error_returns_500(mock_schedule_service, mock_location_service):
    with patch("services.claude_service.get_reply", side_effect=Exception("API down")):
        req = _make_request({"message": "Hello"})
        resp = chat_handler.handle(req)
        assert resp.status_code == 500
        data = json.loads(resp.get_body())
        assert "error" in data
