import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.seasonality import get_month_multiplier

logger = logging.getLogger(__name__)

_EASTERN = [
    "sofia", "bucharest", "warsaw", "budapest", "prague",
    "krakow", "riga", "tallinn", "vilnius",
]
_WESTERN = [
    "madrid", "barcelona", "paris", "amsterdam", "berlin",
    "rome", "milan", "vienna", "zurich", "brussels",
]


def _get_departure_region(city: str) -> str:
    """Map a departure city to a broader pricing region."""
    city_lower = city.lower()
    if city_lower in _EASTERN:
        return "from_eastern_europe"
    if city_lower in _WESTERN:
        return "from_western_europe"
    if city_lower in ["london", "manchester", "edinburgh", "dublin"]:
        return "from_uk"
    if city_lower in [
        "new york", "toronto", "chicago", "los angeles", "miami"
    ]:
        return "from_north_america"
    logger.warning(
        f"Departure city '{city}' not recognized. "
        "Defaulting to western_europe."
    )
    return "from_western_europe"


def estimate_flights(
    departure_city: str,
    destinations: List[str],
    travel_month: int,
    travel_style: str = "mid_range",
    return_city: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimate flight costs for a multi-city itinerary."""
    return_city = return_city or departure_city
    logger.info(
        f"Estimating flights from {departure_city} "
        f"to {destinations}, ending in {return_city}, "
        f"month {travel_month}."
    )

    base_dir = Path(__file__).parent.parent
    cities_path = base_dir / "data" / "cities.json"

    try:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
    except FileNotFoundError:
        logger.error(
            f"Database not found: could not load {cities_path}"
        )
        return {"flight_legs": [], "total_flights_cost": 0}

    city_cost_map = {
        city["name"]: city.get("avg_flight_cost", {})
        for city in cities_data
    }

    region_key = _get_departure_region(departure_city)
    month_multiplier = get_month_multiplier(travel_month)

    legs: List[Dict[str, Any]] = []
    total_cost = 0.0

    if not destinations:
        return {"flight_legs": legs, "total_flights_cost": total_cost}

    inter_city_rates = {
        "backpacker": 60,
        "mid_range": 115,
        "luxury": 225,
    }
    inter_city_cost = inter_city_rates.get(travel_style, 115)

    # Outbound: departure -> first destination
    first_dest = destinations[0]
    base_outbound = (
        city_cost_map.get(first_dest, {}).get(region_key, 150)
    )
    cost_outbound = round(base_outbound * month_multiplier)
    legs.append({
        "from": departure_city,
        "to": first_dest,
        "cost_eur": cost_outbound,
        "type": "outbound",
    })
    total_cost += cost_outbound

    # Inter-city hops
    for i in range(len(destinations) - 1):
        city_a = destinations[i]
        city_b = destinations[i + 1]
        legs.append({
            "from": city_a,
            "to": city_b,
            "cost_eur": inter_city_cost,
            "type": "inter_city",
        })
        total_cost += inter_city_cost

    # Inbound: last destination -> return city
    last_dest = destinations[-1]
    base_inbound = (
        city_cost_map.get(last_dest, {}).get(region_key, 150)
    )
    cost_inbound = round(base_inbound * month_multiplier)
    legs.append({
        "from": last_dest,
        "to": return_city,
        "cost_eur": cost_inbound,
        "type": "inbound",
    })
    total_cost += cost_inbound

    logger.info(f"Total estimated flight cost: €{total_cost}")
    return {"flight_legs": legs, "total_flights_cost": total_cost}
