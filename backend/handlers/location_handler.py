import hmac
import json
import logging
import os

import azure.functions as func

import services.location_service as location_service
import services.eta_service as eta_service
import services.validators as validators

logger = logging.getLogger(__name__)

_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")


def _is_authorized(req: func.HttpRequest) -> bool:
    provided = req.headers.get("X-Admin-Key", "")
    # Constant-time comparison to avoid leaking the key via timing.
    return bool(_ADMIN_KEY) and hmac.compare_digest(provided, _ADMIN_KEY)


def handle(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        return _get_eta(req)
    elif req.method == "POST":
        return _set_eta(req)
    elif req.method == "DELETE":
        return _clear_eta(req)
    return func.HttpResponse("Method Not Allowed", status_code=405)


def handle_track(req: func.HttpRequest) -> func.HttpResponse:
    """Receive GPS coordinates from the director's browser and auto-calculate ETA."""
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

    try:
        lat = float(body["lat"])
        lng = float(body["lng"])
    except (KeyError, TypeError, ValueError):
        return func.HttpResponse(
            json.dumps({"error": "lat and lng are required numbers"}),
            status_code=400,
            mimetype="application/json",
        )

    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        return func.HttpResponse(
            json.dumps({"error": "lat/lng out of range"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        result = eta_service.calculate_eta(lat, lng)
        location_service.set_eta(
            message=result["message"],
            eta_time=result["eta_iso"],
        )
    except Exception:
        logger.exception("Failed to calculate/store ETA")
        return func.HttpResponse(
            json.dumps({"error": "Failed to update ETA"}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps({"status": "ok", "eta": result}),
        status_code=200,
        mimetype="application/json",
    )


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
    message = message[:280]

    # eta_time is optional; accept HH:MM (manual form) or ISO datetime (auto).
    eta_time = (body.get("eta_time") or "").strip()
    if eta_time and not (
        validators.is_valid_time(eta_time) or validators.is_valid_iso_datetime(eta_time)
    ):
        return func.HttpResponse(
            json.dumps({"error": "eta_time must be HH:MM or an ISO datetime"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        eta = location_service.set_eta(
            message=message,
            eta_time=eta_time,
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
