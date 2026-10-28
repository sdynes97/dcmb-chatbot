import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import azure.functions as func

import handlers
from models import Activity, CheckIn, Volunteer


def _req(method="GET", route="kiosk", body=None, params=None, headers=None):
    return func.HttpRequest(
        method=method,
        url=f"https://func.example.com/api/{route}",
        body=json.dumps(body).encode() if body is not None else b"",
        params=params or {},
        headers={"Content-Type": "application/json", **(headers or {})},
    )


ADMIN = {"X-Admin-Key": "test-admin-key"}

_CHECKIN = CheckIn(
    row_key="20261028T180000000000_abc",
    check_in_date="2026-10-28",
    check_in_time="13:00:00",
    checked_in_at_utc="2026-10-28T18:00:00+00:00",
    volunteer_name="Jane Smith",
    activity="Concessions",
    volunteer_id="v1",
)


# ── Kiosk ────────────────────────────────────────────────────────────────────

def test_kiosk_returns_names_and_activities():
    with (
        patch("checkin_service.list_volunteers", return_value=[Volunteer("v1", "Jane Smith")]),
        patch("checkin_service.list_activities", return_value=[Activity("a1", "Concessions")]),
    ):
        resp = handlers.handle_kiosk(_req())
    assert resp.status_code == 200
    data = json.loads(resp.get_body())
    assert data["volunteers"] == [{"id": "v1", "name": "Jane Smith"}]
    assert data["activities"] == [{"id": "a1", "name": "Concessions"}]


def test_kiosk_requires_key_when_configured():
    with patch.object(handlers, "_KIOSK_KEY", "kiosk-secret"):
        assert handlers.handle_kiosk(_req()).status_code == 401
        with (
            patch("checkin_service.list_volunteers", return_value=[]),
            patch("checkin_service.list_activities", return_value=[]),
        ):
            resp = handlers.handle_kiosk(_req(headers={"X-Kiosk-Key": "kiosk-secret"}))
    assert resp.status_code == 200


def test_checkin_roster_volunteer():
    with (
        patch("checkin_service.get_volunteer", return_value=Volunteer("v1", "Jane Smith")),
        patch("checkin_service.get_activity", return_value=Activity("a1", "Concessions")),
        patch("checkin_service.record_checkin", return_value=_CHECKIN) as mock_rec,
    ):
        resp = handlers.handle_checkin(
            _req("POST", "checkin", {"volunteer_id": "v1", "activity_id": "a1"})
        )
    assert resp.status_code == 200
    kwargs = mock_rec.call_args.kwargs
    assert kwargs["volunteer_name"] == "Jane Smith"
    assert kwargs["activity"] == "Concessions"
    assert kwargs["volunteer_id"] == "v1"
    assert kwargs["at"] is None


def test_checkin_walk_in_cleans_name():
    with patch("checkin_service.record_checkin", return_value=_CHECKIN) as mock_rec:
        resp = handlers.handle_checkin(
            _req("POST", "checkin", {"name": "  Pat \n  Doe ", "activity": "Pit Crew"})
        )
    assert resp.status_code == 200
    assert mock_rec.call_args.kwargs["volunteer_name"] == "Pat Doe"
    assert mock_rec.call_args.kwargs["volunteer_id"] == ""


def test_checkin_requires_name():
    resp = handlers.handle_checkin(_req("POST", "checkin", {"name": "   "}))
    assert resp.status_code == 400


def test_checkin_unknown_volunteer_404():
    with patch("checkin_service.get_volunteer", return_value=None):
        resp = handlers.handle_checkin(_req("POST", "checkin", {"volunteer_id": "nope"}))
    assert resp.status_code == 404


def test_checkin_accepts_recent_offline_timestamp():
    at = datetime.now(timezone.utc) - timedelta(hours=1)
    with patch("checkin_service.record_checkin", return_value=_CHECKIN) as mock_rec:
        handlers.handle_checkin(
            _req("POST", "checkin", {"name": "Pat", "checked_in_at": at.isoformat()})
        )
    assert mock_rec.call_args.kwargs["at"] == at


def test_checkin_ignores_out_of_range_timestamp():
    at = datetime.now(timezone.utc) - timedelta(days=30)
    with patch("checkin_service.record_checkin", return_value=_CHECKIN) as mock_rec:
        handlers.handle_checkin(
            _req("POST", "checkin", {"name": "Pat", "checked_in_at": at.isoformat()})
        )
    assert mock_rec.call_args.kwargs["at"] is None


def test_checkin_rejects_naive_timestamp():
    resp = handlers.handle_checkin(
        _req("POST", "checkin", {"name": "Pat", "checked_in_at": "2026-10-28T10:00:00"})
    )
    assert resp.status_code == 400


# ── Admin ────────────────────────────────────────────────────────────────────

def test_roster_requires_admin():
    assert handlers.handle_roster(_req(route="roster")).status_code == 401


def test_roster_bulk_add():
    with patch("checkin_service.add_volunteers", return_value=[Volunteer("v2", "Al B")]) as m:
        resp = handlers.handle_roster(
            _req("POST", "roster", {"names": ["Al B", "", "  "]}, headers=ADMIN)
        )
    assert resp.status_code == 200
    m.assert_called_once_with(["Al B"])


def test_activities_add():
    with patch("checkin_service.add_activity", return_value=Activity("a2", "Uniforms")) as m:
        resp = handlers.handle_activities(
            _req("POST", "activities", {"name": "Uniforms"}, headers=ADMIN)
        )
    assert resp.status_code == 200
    m.assert_called_once_with("Uniforms")


def test_checkins_csv_export():
    with patch("checkin_service.list_checkins", return_value=[_CHECKIN]) as m:
        resp = handlers.handle_checkins(
            _req(route="checkins", headers=ADMIN,
                 params={"from": "2026-10-01", "to": "2026-10-31", "format": "csv"})
        )
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    m.assert_called_once_with("2026-10-01", "2026-10-31")
    lines = resp.get_body().decode().splitlines()
    assert lines[0] == "date,time,name,activity,walk_in,checked_in_at_utc"
    assert lines[1].startswith("2026-10-28,13:00:00,Jane Smith,Concessions,")


def test_checkins_rejects_bad_range():
    resp = handlers.handle_checkins(
        _req(route="checkins", headers=ADMIN, params={"from": "2026-10-31", "to": "2026-10-01"})
    )
    assert resp.status_code == 400


def test_delete_requires_valid_id():
    resp = handlers.handle_roster(_req("DELETE", "roster", headers=ADMIN, params={"id": "a/b"}))
    assert resp.status_code == 400
