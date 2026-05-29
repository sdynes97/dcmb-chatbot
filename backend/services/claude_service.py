import os
from typing import List, Optional

import anthropic

from models.event import ScheduleEvent
from models.location_update import ETAUpdate

_client: Optional[anthropic.Anthropic] = None

# Stable prefix: instructions + the full season schedule. This is byte-identical
# across requests (within a season), so it's the cache target.
_SYSTEM_PREFIX = """\
You are a helpful assistant for the Davenport Central Marching Band.
Your job is to answer questions from parents about the band's schedule, performances, and logistics.

Answer questions ONLY using the schedule data and ETA update provided below.
If the information is not in the data, respond with:
"I don't have that information — please contact the band director."

Keep your responses concise, friendly, and easy to read on a phone.

Current season schedule:
{schedule_text}"""

_ETA_SECTION = """\
Most recent director ETA update:
{eta_text}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _build_system_blocks(
    events: List[ScheduleEvent], eta: Optional[ETAUpdate]
) -> list:
    """Build the system prompt as cacheable blocks.

    The schedule rarely changes within a season, so the instructions + schedule
    block carries a cache_control breakpoint and is served from cache on repeat
    queries. The ETA can change every ~30s during live tracking, so it lives in
    a separate block *after* the breakpoint — updating it doesn't invalidate the
    cached schedule prefix.
    """
    if events:
        schedule_text = "\n---\n".join(e.to_readable_text() for e in events)
    else:
        schedule_text = "No events currently scheduled."

    if eta:
        eta_text = _ETA_SECTION.format(eta_text=eta.to_readable_text())
    else:
        eta_text = "No director ETA update available."

    return [
        {
            "type": "text",
            "text": _SYSTEM_PREFIX.format(schedule_text=schedule_text),
            # 1-hour TTL: parent queries during an event window are spread over
            # hours, so the longer TTL keeps the schedule warm between them.
            "cache_control": {"type": "ephemeral", "ttl": "1h"},
        },
        {
            "type": "text",
            "text": eta_text,  # volatile — intentionally after the breakpoint
        },
    ]


def get_reply(
    message: str,
    events: List[ScheduleEvent],
    eta: Optional[ETAUpdate],
    conversation_history: Optional[list] = None,
) -> str:
    system_blocks = _build_system_blocks(events, eta)

    messages = conversation_history or []
    messages = messages + [{"role": "user", "content": message}]

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system=system_blocks,
        messages=messages,
    )
    return response.content[0].text.strip()
