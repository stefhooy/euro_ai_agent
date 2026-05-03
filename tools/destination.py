import logging
from pathlib import Path
from typing import Any, Dict, List

from tools.city_data import load_all_city_profiles

logger = logging.getLogger(__name__)

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
            activity_score = (len(matches) / len(activity_prefs)) * 40
            if matches:
                reasons.append(
                    f"Matches {len(matches)} of your activity preferences."
                )
        else:
            activity_score = 40

        city_cost = city.get("avg_daily_cost", {}).get(travel_style, 0)
        if budget_per_day <= 0:
            budget_score = 0
        elif city_cost <= budget_per_day:
            budget_score = 40
            reasons.append("Fits perfectly within your daily budget.")
        elif city_cost <= budget_per_day * 1.5:
            overage = (city_cost - budget_per_day) / (budget_per_day * 0.5)
            budget_score = 40 * (1 - overage)
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

        total_score = activity_score + budget_score + season_score
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
