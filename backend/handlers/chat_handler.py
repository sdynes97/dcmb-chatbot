import json
import logging

import azure.functions as func

import services.claude_service as claude_service
import services.schedule_service as schedule_service
import services.location_service as location_service

logger = logging.getLogger(__name__)

# Cap how much client-supplied history we trust, to bound prompt size/cost.
_MAX_HISTORY_TURNS = 20
_MAX_CONTENT_CHARS = 2000


def _sanitize_history(raw) -> list:
    """Validate and normalize client-supplied conversation history.

    The client sends prior turns back with each request. We never trust this
    blindly: only well-formed {role: user|assistant, content: str} entries are
    kept, content is length-capped, and the list is truncated to recent turns.
    """
    if not isinstance(raw, list):
        return []
    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        cleaned.append({"role": role, "content": content[:_MAX_CONTENT_CHARS]})
    return cleaned[-_MAX_HISTORY_TURNS:]


def handle(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    message = (body.get("message") or "").strip()
    if not message:
        return func.HttpResponse(
            json.dumps({"error": "message is required"}),
            status_code=400,
            mimetype="application/json",
        )

    history = _sanitize_history(body.get("history", []))

    try:
        events = schedule_service.get_all_events()
        eta = location_service.get_current_eta()
        reply = claude_service.get_reply(
            message=message,
            events=events,
            eta=eta,
            channel="web",
            conversation_history=history,
        )
    except Exception:
        logger.exception("Chat handler error")
        return func.HttpResponse(
            json.dumps({"error": "Something went wrong. Please try again."}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"reply": reply}),
        status_code=200,
        mimetype="application/json",
    )
