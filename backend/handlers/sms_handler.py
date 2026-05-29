import json
import logging
import os

import azure.functions as func

import services.claude_service as claude_service
import services.schedule_service as schedule_service
import services.location_service as location_service
import services.telnyx_service as telnyx_service

logger = logging.getLogger(__name__)

_DIRECTOR_PHONE = os.environ.get("DIRECTOR_PHONE", "")


def _is_director(from_number: str) -> bool:
    return bool(_DIRECTOR_PHONE) and from_number == _DIRECTOR_PHONE


def handle(req: func.HttpRequest) -> func.HttpResponse:
    # Validate Telnyx webhook signature
    timestamp = req.headers.get("telnyx-timestamp", "")
    signature = req.headers.get("telnyx-signature-ed25519", "")
    raw_body = req.get_body()

    if not telnyx_service.validate_webhook_signature(raw_body, timestamp, signature):
        logger.warning("Invalid Telnyx webhook signature")
        return func.HttpResponse("Forbidden", status_code=403)

    try:
        payload = json.loads(raw_body)
    except ValueError:
        return func.HttpResponse("Bad Request", status_code=400)

    data = payload.get("data", {})
    event_type = data.get("event_type", "")

    # Only process inbound messages
    if event_type != "message.received":
        return func.HttpResponse("OK", status_code=200)

    payload_obj = data.get("payload", {})
    from_number = payload_obj.get("from", {}).get("phone_number", "")
    text = (payload_obj.get("text") or "").strip()

    if not from_number or not text:
        return func.HttpResponse("OK", status_code=200)

    try:
        if _is_director(from_number):
            _handle_director_update(from_number, text)
        else:
            _handle_parent_query(from_number, text)
    except Exception:
        logger.exception("SMS handler error for %s", from_number)
        telnyx_service.send_sms(
            from_number,
            "Sorry, something went wrong. Please try again.",
        )

    return func.HttpResponse("OK", status_code=200)


def _handle_director_update(phone: str, text: str) -> None:
    """Store the director's message as the current ETA update."""
    eta = location_service.set_eta(message=text)
    telnyx_service.send_sms(phone, "ETA update saved. Parents can now query it.")


def _handle_parent_query(phone: str, text: str) -> None:
    events = schedule_service.get_all_events()
    eta = location_service.get_current_eta()
    reply = claude_service.get_reply(
        message=text,
        events=events,
        eta=eta,
        channel="sms",
    )
    # Truncate to 160 chars if Claude went over
    if len(reply) > 160:
        reply = reply[:157] + "..."
    telnyx_service.send_sms(phone, reply)
