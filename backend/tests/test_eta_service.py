import pytest
from services.eta_service import haversine_miles, calculate_eta, SCHOOL_LAT, SCHOOL_LNG


def test_haversine_same_point():
    assert haversine_miles(41.5236, -90.5776, 41.5236, -90.5776) == 0.0


def test_haversine_known_distance():
    # Bettendorf HS to Davenport Central is roughly 5–6 miles
    dist = haversine_miles(41.5236, -90.5776, 41.5600, -90.4900)
    assert 4.0 < dist < 8.0


def test_calculate_eta_far_away():
    # ~50 miles out (Iowa City area)
    result = calculate_eta(41.6611, -91.5302)
    assert result["distance_mi"] > 40
    assert result["travel_minutes"] > 60
    assert "mi away" in result["message"]
    assert "ETA" in result["message"]
    assert "auto-updated" in result["message"]


def test_calculate_eta_nearby():
    # Very close — less than 0.3 miles
    result = calculate_eta(SCHOOL_LAT + 0.001, SCHOOL_LNG + 0.001)
    assert result["distance_mi"] < 0.5
    assert "arrived" in result["message"]


def test_calculate_eta_almost_there():
    # About 2 miles away
    result = calculate_eta(SCHOOL_LAT + 0.015, SCHOOL_LNG + 0.015)
    assert result["distance_mi"] < 5
    # Should produce a message (either "almost" or miles+ETA)
    assert result["message"]


def test_calculate_eta_returns_iso_string():
    result = calculate_eta(41.5600, -90.4900)
    from datetime import datetime
    # Should parse without error
    datetime.fromisoformat(result["eta_iso"])
