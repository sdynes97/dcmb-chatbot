import json
import logging
import os

import azure.functions as func

import services.schedule_service as schedule_service
from models.event import ScheduleEvent

logger = logging.getLogger(__name__)

_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")


def _is_authorized(req: func.HttpRequest) -> bool:
    provided = req.headers.get("X-Admin-Key", "")
    return bool(_ADMIN_KEY) and provided == _ADMIN_KEY


def handle_events(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_authorized(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    if req.method == "GET":
        return _list_events(req)
    elif req.method == "POST":
        return _upsert_event(req)
    elif req.method == "DELETE":
        return _delete_event(req)
    return func.HttpResponse("Method Not Allowed", status_code=405)


def _list_events(req: func.HttpRequest) -> func.HttpResponse:
    season = req.params.get("season")
    events = schedule_service.get_all_events(season=season)
    return func.HttpResponse(
        json.dumps([e.to_dict() for e in events]),
        status_code=200,
        mimetype="application/json",
    )


def _upsert_event(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    required = [
        "partition_key", "row_key", "event_type", "event_name",
        "event_date", "call_time", "performance_time",
        "estimated_return", "location_name", "location_address",
        "drop_off_location",
    ]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return func.HttpResponse(
            json.dumps({"error": f"Missing fields: {missing}"}),
            status_code=400,
            mimetype="application/json",
        )

    event = ScheduleEvent(
        partition_key=body["partition_key"],
        row_key=body["row_key"],
        event_type=body["event_type"],
        event_name=body["event_name"],
        event_date=body["event_date"],
        call_time=body["call_time"],
        performance_time=body["performance_time"],
        estimated_return=body["estimated_return"],
        location_name=body["location_name"],
        location_address=body["location_address"],
        drop_off_location=body["drop_off_location"],
        is_away=bool(body.get("is_away", False)),
        notes=body.get("notes", ""),
    )

    try:
        schedule_service.upsert_event(event)
    except Exception:
        logger.exception("Failed to upsert event")
        return func.HttpResponse(
            json.dumps({"error": "Failed to save event"}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"status": "ok", "row_key": event.row_key}),
        status_code=200,
        mimetype="application/json",
    )


def _delete_event(req: func.HttpRequest) -> func.HttpResponse:
    partition_key = req.params.get("partition_key")
    row_key = req.params.get("row_key")
    if not partition_key or not row_key:
        return func.HttpResponse(
            json.dumps({"error": "partition_key and row_key are required"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        schedule_service.delete_event(partition_key, row_key)
    except Exception:
        logger.exception("Failed to delete event")
        return func.HttpResponse(
            json.dumps({"error": "Failed to delete event"}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"status": "deleted"}),
        status_code=200,
        mimetype="application/json",
    )
