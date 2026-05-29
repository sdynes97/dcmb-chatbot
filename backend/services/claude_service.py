import os
from typing import List, Optional

import anthropic

from models.event import ScheduleEvent
from models.location_update import ETAUpdate

_client: Optional[anthropic.Anthropic] = None

_SYSTEM_PROMPT = """\
You are a helpful assistant for the Davenport Central Marching Band.
Your job is to answer questions from parents about the band's schedule, performances, and logistics.

Answer questions ONLY using the schedule data and ETA update provided below.
If the information is not in the data, respond with:
"I don't have that information — please contact the band director."

Keep your responses concise, friendly, and easy to read on a phone.

Current season schedule:
{schedule_text}

{eta_section}"""

_ETA_SECTION = """\
Most recent director ETA update:
{eta_text}"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _build_system_prompt(events: List[ScheduleEvent], eta: Optional[ETAUpdate]) -> str:
    if events:
        schedule_lines = [e.to_readable_text() for e in events]
        schedule_text = "\n---\n".join(schedule_lines)
    else:
        schedule_text = "No events currently scheduled."

    if eta:
        eta_section = _ETA_SECTION.format(eta_text=eta.to_readable_text())
    else:
        eta_section = "No director ETA update available."

    return _SYSTEM_PROMPT.format(
        schedule_text=schedule_text,
        eta_section=eta_section,
    )


def get_reply(
    message: str,
    events: List[ScheduleEvent],
    eta: Optional[ETAUpdate],
    conversation_history: Optional[list] = None,
) -> str:
    system_prompt = _build_system_prompt(events, eta)

    messages = conversation_history or []
    messages = messages + [{"role": "user", "content": message}]

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text.strip()
