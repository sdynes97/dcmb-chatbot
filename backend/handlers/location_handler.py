import json
import logging
import os

import azure.functions as func

import services.location_service as location_service

logger = logging.getLogger(__name__)

_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")


def _is_authorized(req: func.HttpRequest) -> bool:
    provided = req.headers.get("X-Admin-Key", "")
    return bool(_ADMIN_KEY) and provided == _ADMIN_KEY


def handle(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        return _get_eta(req)
    elif req.method == "POST":
        return _set_eta(req)
    elif req.method == "DELETE":
        return _clear_eta(req)
    return func.HttpResponse("Method Not Allowed", status_code=405)


def _get_eta(req: func.HttpRequest) -> func.HttpResponse:
    eta = location_service.get_current_eta()
    if eta is None:
        return func.HttpResponse(
            json.dumps({"eta": None}),
            status_code=200,
            mimetype="application/json",
        )
    return func.HttpResponse(
        json.dumps({"eta": eta.to_dict()}),
        status_code=200,
        mimetype="application/json",
    )


def _set_eta(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_authorized(req):
        return func.HttpResponse("Unauthorized", status_code=401)

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

    try:
        eta = location_service.set_eta(
            message=message,
            eta_time=body.get("eta_time", ""),
            event_row_key=body.get("event_row_key", ""),
        )
    except Exception:
        logger.exception("Failed to set ETA")
        return func.HttpResponse(
            json.dumps({"error": "Failed to save ETA"}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"status": "ok", "eta": eta.to_dict()}),
        status_code=200,
        mimetype="application/json",
    )


def _clear_eta(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_authorized(req):
        return func.HttpResponse("Unauthorized", status_code=401)

    location_service.clear_eta()
    return func.HttpResponse(
        json.dumps({"status": "cleared"}),
        status_code=200,
        mimetype="application/json",
    )
