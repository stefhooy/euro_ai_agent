import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.city_data import load_all_city_profiles

logger = logging.getLogger(__name__)

# Coordinates for common departure cities not in the seed file.
# Covers cities users are likely to depart from that Hermes won't recommend.
_DEP_COORDS: Dict[str, Tuple[float, float]] = {
    "Glasgow":     (55.8642,   -4.2518),
    "Birmingham":  (52.4862,   -1.8904),
    "Bristol":     (51.4545,   -2.5879),
    "Liverpool":   (53.4084,   -2.9916),
    "Leeds":       (53.8008,   -1.5491),
    "Cardiff":     (51.4816,   -3.1791),
    "Marseille":   (43.2965,    5.3698),
    "Toulouse":    (43.6047,    1.4442),
    "Turin":       (45.0703,    7.6869),
    "Bologna":     (44.4949,   11.3426),
    "Bilbao":      (43.2630,   -2.9350),
    "Malaga":      (36.7213,   -4.4214),
    "Seville":     (37.3891,   -5.9845),
    "The Hague":   (52.0705,    4.3007),
    "Dusseldorf":  (51.2217,    6.7762),
    "Stuttgart":   (48.7758,    9.1829),
    "Leipzig":     (51.3397,   12.3731),
    "Kaunas":      (54.8985,   23.9036),
    "Minsk":       (53.9045,   27.5615),
    "Kyiv":        (50.4501,   30.5234),
    "New York":    (40.7128,  -74.0060),
    "Los Angeles": (34.0522,  -118.2437),
    "Chicago":     (41.8781,  -87.6298),
    "Miami":       (25.7617,  -80.1918),
    "Toronto":     (43.6532,  -79.3832),
    "Montreal":    (45.5017,  -73.5673),
    "Sydney":      (-33.8688, 151.2093),
    "Melbourne":   (-37.8136, 144.9631),
    "Dubai":       (25.2048,   55.2708),
    "Singapore":   (1.3521,   103.8198),
}


def _haversine_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def _get_dep_coords(
    departure_city: str,
    seed_cities: List[Dict[str, Any]],
) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) for a departure city, or None if unknown.

    City profiles store coordinates under profile["geo"]["lat/lon"];
    raw seed dicts store them at the top level - handles both forms.
    """
    dep_lower = departure_city.strip().lower()
    for c in seed_cities:
        if c["name"].lower() == dep_lower:
            geo = c.get("geo", {})
            lat = geo.get("lat") if geo else c.get("lat")
            lon = geo.get("lon") if geo else c.get("lon")
            if lat is not None and lon is not None:
                return float(lat), float(lon)
    for city_name, coords in _DEP_COORDS.items():
        if city_name.lower() == dep_lower:
            return coords
    return None


# Countries for common departure cities not in the seed
_EXTRA_CITY_COUNTRIES: Dict[str, str] = {
    "London": "United Kingdom", "Manchester": "United Kingdom",
    "Edinburgh": "United Kingdom", "Glasgow": "United Kingdom",
    "Dublin": "Ireland",
    "Frankfurt": "Germany", "Cologne": "Germany",
    "Dusseldorf": "Germany",
    "Lyon": "France", "Marseille": "France", "Toulouse": "France",
    "Naples": "Italy", "Turin": "Italy", "Bologna": "Italy",
    "Valencia": "Spain", "Bilbao": "Spain", "Malaga": "Spain",
    "Rotterdam": "Netherlands", "The Hague": "Netherlands",
    "New York": "United States", "Los Angeles": "United States",
    "Chicago": "United States", "Miami": "United States",
    "Toronto": "Canada", "Montreal": "Canada", "Vancouver": "Canada",
    "Sydney": "Australia", "Melbourne": "Australia",
    "Dubai": "UAE", "Singapore": "Singapore",
}


def _get_departure_country(
    departure_city: str,
    seed_cities: List[Dict[str, Any]],
) -> str:
    """Map a departure city name to its country."""
    dep_lower = departure_city.strip().lower()
    for c in seed_cities:
        if c["name"].lower() == dep_lower:
            return c["country"]
    for city_name, country in _EXTRA_CITY_COUNTRIES.items():
        if city_name.lower() == dep_lower:
            return country
    return ""


def score_destinations(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Score and select the best European cities based on user preferences.

    Args:
        preferences: Dict containing budget, duration, travel_style,
                     activity_preferences, travel_month, and optionally
                     trip_type and departure_city. International trips
                     exclude cities in the departure country when known.

    Returns:
        Dict with 'top_destinations' (scored city list) and
        'domestic_fallback' (True if domestic filter found no matches).
    """
    logger.info(
        "Starting destination scoring using live city profiles..."
    )

    seed_path = str(
        Path(__file__).parent.parent / "data" / "european_cities_seed.json"
    )
    cities = load_all_city_profiles(seed_path)

    budget = preferences.get("budget", 0)
    duration = preferences.get("duration", 1)
    budget_per_day = budget / duration if duration > 0 else 0
    travel_style = preferences.get("travel_style", "mid_range")
    activity_prefs = preferences.get("activity_preferences", [])
    travel_month = preferences.get("travel_month", 6)
    trip_type = preferences.get("trip_type", "international")
    departure_city = preferences.get("departure_city", "")

    domestic_fallback = False
    dep_country = (
        _get_departure_country(departure_city, cities)
        if departure_city else ""
    )
    dep_coords: Optional[Tuple[float, float]] = (
        _get_dep_coords(departure_city, cities)
        if departure_city else None
    )

    if trip_type == "domestic" and departure_city:
        if dep_country:
            domestic_cities = [
                c for c in cities if c.get("country") == dep_country
            ]
            if domestic_cities:
                logger.info(
                    f"Domestic trip: restricting to {dep_country} "
                    f"({len(domestic_cities)} cities found)."
                )
                cities = domestic_cities
            else:
                logger.warning(
                    f"No seed cities in '{dep_country}'. "
                    "Falling back to international."
                )
                domestic_fallback = True
        else:
            logger.warning(
                f"Could not determine country for '{departure_city}'. "
                "Using all destinations."
            )
            domestic_fallback = True
    elif trip_type == "international" and dep_country:
        international_cities = [
            c for c in cities if c.get("country") != dep_country
        ]
        if international_cities:
            logger.info(
                f"International trip: excluding {dep_country} "
                f"({len(cities) - len(international_cities)} "
                "domestic cities removed)."
            )
            cities = international_cities
        else:
            logger.warning(
                f"No international seed cities outside '{dep_country}'. "
                "Using all destinations."
            )

    scored_cities: List[Dict[str, Any]] = []

    for city in cities:
        reasons: List[str] = []

        city_tags = city.get("activity_tags", [])
        if activity_prefs:
            matches = set(activity_prefs).intersection(set(city_tags))
            activity_score = (len(matches) / len(activity_prefs)) * 30
            if matches:
                reasons.append(
                    f"Matches {len(matches)} of your activity preferences."
                )
        else:
            activity_score = 30

        city_cost = city.get("avg_daily_cost", {}).get(travel_style, 0)
        if budget_per_day <= 0:
            budget_score = 0
        elif city_cost <= budget_per_day:
            budget_score = 30
            reasons.append("Fits perfectly within your daily budget.")
        elif city_cost <= budget_per_day * 1.5:
            overage = (city_cost - budget_per_day) / (budget_per_day * 0.5)
            budget_score = 30 * (1 - overage)
            reasons.append("Slightly over your daily budget but manageable.")
        else:
            budget_score = 0
            reasons.append("Significantly over your daily budget.")

        best_months = city.get("best_months", [])
        prev_month = 12 if travel_month == 1 else travel_month - 1
        next_month = 1 if travel_month == 12 else travel_month + 1

        if travel_month in best_months:
            season_score = 20
            reasons.append("Perfect time of year to visit.")
        elif prev_month in best_months or next_month in best_months:
            season_score = 10
            reasons.append("Shoulder season, decent time to visit.")
        else:
            season_score = 0
            reasons.append("Off-peak season for this destination.")

        # Proximity score: 20 pts, decays linearly to 0 at 3000 km.
        # Rewards cities near the departure point so routes stay coherent
        # and less-famous nearby gems can compete with famous distant ones.
        prox_score = 0.0
        if dep_coords is not None:
            geo = city.get("geo", {})
            city_lat = float(geo.get("lat", 0.0)) if geo else 0.0
            city_lon = float(geo.get("lon", 0.0)) if geo else 0.0
            dist_km = _haversine_km(
                dep_coords[0], dep_coords[1],
                city_lat,
                city_lon,
            )
            prox_score = max(0.0, 20.0 * (1.0 - dist_km / 3000.0))
            if dist_km < 800:
                reasons.append(
                    f"Close to your departure city "
                    f"({dist_km:,.0f} km away)."
                )

        total_score = (
            activity_score + budget_score + season_score + prox_score
        )
        city_data = city.copy()
        city_data["score"] = round(total_score, 1)
        city_data["reasons"] = reasons
        scored_cities.append(city_data)

    num_countries = preferences.get("num_countries", 4)
    pool_size = max(10, num_countries * 3)
    top_cities = sorted(
        scored_cities, key=lambda x: x["score"], reverse=True
    )[:pool_size]
    logger.info(
        f"Top {len(top_cities)} destinations selected "
        f"from {len(cities)} cities."
    )
    return {
        "top_destinations": top_cities,
        "domestic_fallback": domestic_fallback,
    }
