import json
from unittest.mock import patch, MagicMock

import azure.functions as func

import handlers.location_handler as location_handler


def _make_request(body: dict, authed: bool = True) -> func.HttpRequest:
    return func.HttpRequest(
        method="POST",
        url="https://func.example.com/api/location/track",
        body=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Admin-Key": "test-admin-key" if authed else "wrong-key",
        },
    )


def test_track_calculates_and_stores_eta():
    mock_eta = MagicMock()
    with (
        patch("services.location_service.set_eta", return_value=mock_eta) as mock_set,
        patch("services.eta_service.calculate_eta", return_value={
            "distance_mi": 8.2,
            "travel_minutes": 14,
            "eta_iso": "2025-09-06T22:45:00+00:00",
            "message": "Bus is 8.2 mi away, ETA ~10:45 PM. (auto-updated 10:31 PM)",
        }) as mock_calc,
    ):
        req = _make_request({"lat": 41.56, "lng": -90.49})
        resp = location_handler.handle_track(req)

        assert resp.status_code == 200
        data = json.loads(resp.get_body())
        assert data["status"] == "ok"
        assert data["eta"]["distance_mi"] == 8.2
        mock_calc.assert_called_once_with(41.56, -90.49)
        mock_set.assert_called_once()


def test_track_requires_auth():
    req = _make_request({"lat": 41.56, "lng": -90.49}, authed=False)
    resp = location_handler.handle_track(req)
    assert resp.status_code == 401


def test_track_missing_lat_lng():
    req = _make_request({"message": "oops"})
    resp = location_handler.handle_track(req)
    assert resp.status_code == 400


def test_track_invalid_lat_lng():
    req = _make_request({"lat": "not-a-number", "lng": -90.49})
    resp = location_handler.handle_track(req)
    assert resp.status_code == 400
