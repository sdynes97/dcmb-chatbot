"""
Calculates ETA from GPS coordinates to the school using haversine distance
and an assumed average speed. No external API required.
"""
import math
import os
from datetime import datetime, timezone, timedelta

# School coordinates — override via env vars if needed
SCHOOL_LAT = float(os.environ.get("SCHOOL_LAT", "41.5236"))
SCHOOL_LNG = float(os.environ.get("SCHOOL_LNG", "-90.5776"))

# Conservative average speed in mph for a school bus on mixed roads
AVG_SPEED_MPH = float(os.environ.get("AVG_SPEED_MPH", "35"))

EARTH_RADIUS_MI = 3958.8


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance between two GPS coordinates in miles."""
    r = EARTH_RADIUS_MI
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_eta(director_lat: float, director_lng: float) -> dict:
    """
    Returns distance in miles, ETA datetime, and a human-readable message.
    """
    distance_mi = haversine_miles(director_lat, director_lng, SCHOOL_LAT, SCHOOL_LNG)

    # Add a 10% buffer for roads vs straight line
    travel_time_hours = (distance_mi * 1.10) / AVG_SPEED_MPH
    travel_time_minutes = round(travel_time_hours * 60)

    now = datetime.now(timezone.utc)
    eta_dt = now + timedelta(hours=travel_time_hours)

    # Format ETA in local-ish display (ISO stored, formatted for message)
    eta_str = eta_dt.strftime("%I:%M %p").lstrip("0")
    updated_str = now.strftime("%I:%M %p").lstrip("0")

    if distance_mi < 0.3:
        message = f"Bus has arrived. (auto-updated {updated_str})"
    elif travel_time_minutes < 5:
        message = f"Bus is almost there — {round(distance_mi, 1)} mi away. (auto-updated {updated_str})"
    else:
        message = (
            f"Bus is {round(distance_mi, 1)} mi away, ETA ~{eta_str}. "
            f"(auto-updated {updated_str})"
        )

    return {
        "distance_mi": round(distance_mi, 2),
        "travel_minutes": travel_time_minutes,
        "eta_iso": eta_dt.isoformat(),
        "message": message,
    }
