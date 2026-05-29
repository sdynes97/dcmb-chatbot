import json
import logging
from typing import Optional

import azure.functions as func

import services.claude_service as claude_service
import services.schedule_service as schedule_service
import services.location_service as location_service

logger = logging.getLogger(__name__)


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

    history = body.get("history", [])

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
    except Exception as exc:
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
