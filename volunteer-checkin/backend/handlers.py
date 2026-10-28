"""Volunteer check-in API.

Kiosk endpoints (/kiosk, /checkin) require X-Kiosk-Key when KIOSK_API_KEY is
set; admin endpoints (/roster, /activities, /checkins) require X-Admin-Key.
"""
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone

import azure.functions as func

import validators
import checkin_service

logger = logging.getLogger(__name__)

_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")
_KIOSK_KEY = os.environ.get("KIOSK_API_KEY", "")

_MAX_NAME_LEN = 80
# Offline-queued check-ins from the iPad may carry their original tap time.
_MAX_BACKDATE = timedelta(days=7)
_MAX_CLOCK_SKEW = timedelta(minutes=5)
_MAX_EXPORT_DAYS = 400


def _is_admin(req: func.HttpRequest) -> bool:
    provided = req.headers.get("X-Admin-Key", "")
    # Constant-time comparison to avoid leaking the key via timing.
    return bool(_ADMIN_KEY) and hmac.compare_digest(provided, _ADMIN_KEY)


def _is_kiosk(req: func.HttpRequest) -> bool:
    if _is_admin(req):
        return True
    if not _KIOSK_KEY:
        return True
    return hmac.compare_digest(req.headers.get("X-Kiosk-Key", ""), _KIOSK_KEY)


def _json(body, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body), status_code=status_code, mimetype="application/json")


def _error(message: str, status_code: int = 400) -> func.HttpResponse:
    return _json({"error": message}, status_code)


def _clean_name(value) -> str:
    if not isinstance(value, str):
        return ""
    # Collapse whitespace and strip control characters.
    cleaned = " ".join("".join(ch for ch in value if ch.isprintable()).split())
    return cleaned[:_MAX_NAME_LEN]


def _get_body(req: func.HttpRequest):
    try:
        body = req.get_json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


# ── Kiosk ────────────────────────────────────────────────────────────────────

def handle_kiosk(req: func.HttpRequest) -> func.HttpResponse:
    """GET: everything the kiosk needs to render (names + activities)."""
    if not _is_kiosk(req):
        return func.HttpResponse("Unauthorized", status_code=401)
    try:
        volunteers = checkin_service.list_volunteers()
        activities = checkin_service.list_activities()
    except Exception:
        logger.exception("Failed to load kiosk data")
        return _error("Failed to load volunteers", 500)
    return _json({
        "volunteers": [v.to_dict() for v in volunteers],
        "activities": [a.to_dict() for a in activities],
    })


def handle_checkin(req: func.HttpRequest) -> func.HttpResponse:
    """POST {volunteer_id | name, activity_id | activity, checked_in_at?}."""
    if not _is_kiosk(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    body = _get_body(req)
    if body is None:
        return _error("Invalid JSON")

    volunteer_id = body.get("volunteer_id") or ""
    if volunteer_id:
        if not validators.is_valid_table_key(volunteer_id):
            return _error("volunteer_id is invalid")
        volunteer = checkin_service.get_volunteer(volunteer_id)
        if volunteer is None:
            return _error("Volunteer not found", 404)
        name = volunteer.name
    else:
        # Walk-in: not on the roster, typed their own name.
        name = _clean_name(body.get("name"))
        if not name:
            return _error("volunteer_id or name is required")

    activity_id = body.get("activity_id") or ""
    if activity_id:
        if not validators.is_valid_table_key(activity_id):
            return _error("activity_id is invalid")
        activity = checkin_service.get_activity(activity_id)
        if activity is None:
            return _error("Activity not found", 404)
        activity_name = activity.name
    else:
        activity_name = _clean_name(body.get("activity")) or "General"

    at = None
    raw_at = body.get("checked_in_at")
    if raw_at:
        if not validators.is_valid_iso_datetime(raw_at):
            return _error("checked_in_at must be an ISO datetime")
        at = datetime.fromisoformat(raw_at)
        if at.tzinfo is None:
            return _error("checked_in_at must include a timezone")
        now = datetime.now(timezone.utc)
        if not (now - _MAX_BACKDATE <= at <= now + _MAX_CLOCK_SKEW):
            at = None  # Out of range — fall back to server time.

    try:
        checkin = checkin_service.record_checkin(
            volunteer_name=name,
            activity=activity_name,
            volunteer_id=volunteer_id,
            at=at,
        )
    except Exception:
        logger.exception("Failed to record check-in")
        return _error("Failed to save check-in", 500)

    return _json({"status": "ok", "checkin": checkin.to_dict()})


# ── Admin: roster ────────────────────────────────────────────────────────────

def handle_roster(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_admin(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    if req.method == "GET":
        return _json([v.to_dict() for v in checkin_service.list_volunteers()])

    if req.method == "POST":
        body = _get_body(req)
        if body is None:
            return _error("Invalid JSON")
        raw = body.get("names")
        if raw is None:
            raw = [body.get("name")]
        if not isinstance(raw, list):
            return _error("names must be a list")
        names = [n for n in (_clean_name(x) for x in raw) if n]
        if not names:
            return _error("At least one name is required")
        try:
            added = checkin_service.add_volunteers(names)
        except Exception:
            logger.exception("Failed to add volunteers")
            return _error("Failed to save volunteers", 500)
        return _json({"status": "ok", "added": [v.to_dict() for v in added]})

    if req.method == "DELETE":
        return _delete_by_id(req, checkin_service.delete_volunteer)

    return func.HttpResponse("Method Not Allowed", status_code=405)


# ── Admin: activities ────────────────────────────────────────────────────────

def handle_activities(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_admin(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    if req.method == "GET":
        return _json([a.to_dict() for a in checkin_service.list_activities()])

    if req.method == "POST":
        body = _get_body(req)
        if body is None:
            return _error("Invalid JSON")
        name = _clean_name(body.get("name"))
        if not name:
            return _error("name is required")
        try:
            activity = checkin_service.add_activity(name)
        except Exception:
            logger.exception("Failed to add activity")
            return _error("Failed to save activity", 500)
        return _json({"status": "ok", "activity": activity.to_dict()})

    if req.method == "DELETE":
        return _delete_by_id(req, checkin_service.delete_activity)

    return func.HttpResponse("Method Not Allowed", status_code=405)


# ── Admin: check-in log / spreadsheet export ─────────────────────────────────

def handle_checkins(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_admin(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    if req.method == "DELETE":
        return _delete_by_id(req, checkin_service.delete_checkin)
    if req.method != "GET":
        return func.HttpResponse("Method Not Allowed", status_code=405)

    today = checkin_service.local_today()
    date_from = req.params.get("from") or today
    date_to = req.params.get("to") or date_from
    if not (validators.is_valid_date(date_from) and validators.is_valid_date(date_to)):
        return _error("from and to must be YYYY-MM-DD dates")
    if date_from > date_to:
        return _error("from must be on or before to")
    span = datetime.strptime(date_to, "%Y-%m-%d") - datetime.strptime(date_from, "%Y-%m-%d")
    if span.days > _MAX_EXPORT_DAYS:
        return _error(f"Date range may not exceed {_MAX_EXPORT_DAYS} days")

    try:
        checkins = checkin_service.list_checkins(date_from, date_to)
    except Exception:
        logger.exception("Failed to list check-ins")
        return _error("Failed to load check-ins", 500)

    if req.params.get("format") == "csv":
        filename = f"volunteer-checkins_{date_from}_to_{date_to}.csv"
        return func.HttpResponse(
            checkin_service.checkins_to_csv(checkins),
            status_code=200,
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return _json([c.to_dict() for c in checkins])


def _delete_by_id(req: func.HttpRequest, delete_fn) -> func.HttpResponse:
    item_id = req.params.get("id", "")
    if not item_id or not validators.is_valid_table_key(item_id):
        return _error("id is required")
    try:
        delete_fn(item_id)
    except Exception:
        logger.exception("Failed to delete %s", item_id)
        return _error("Failed to delete", 500)
    return _json({"status": "deleted"})
