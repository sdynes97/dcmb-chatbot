from unittest.mock import MagicMock, patch

import pytest

import services.claude_service as claude_service


@pytest.fixture(autouse=True)
def reset_claude_client():
    claude_service._client = None
    yield
    claude_service._client = None


def _mock_response(text: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


def test_get_reply_web(sample_event, sample_eta):
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _mock_response("The game is on Sept 6.")
        claude_service._client = instance

        reply = claude_service.get_reply(
            message="When is the next game?",
            events=[sample_event],
            eta=sample_eta,
        )
        assert "Sept 6" in reply
        call_kwargs = instance.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5"
        assert "Davenport Central Marching Band" in call_kwargs["system"]


def test_get_reply_no_events():
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _mock_response("No events scheduled.")
        claude_service._client = instance

        claude_service.get_reply(
            message="What's next?",
            events=[],
            eta=None,
        )
        system = instance.messages.create.call_args[1]["system"]
        assert "No events currently scheduled" in system


def test_schedule_text_included_in_prompt(sample_event):
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _mock_response("...")
        claude_service._client = instance

        claude_service.get_reply("?", [sample_event], None)
        system = instance.messages.create.call_args[1]["system"]
        assert "Home vs. Lincoln" in system
        assert "17:30" in system
