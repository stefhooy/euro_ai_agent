import calendar
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.accommodation import estimate_accommodation
from tools.city_data import REGIONAL_BEST_MONTHS
from tools.seasonality import MONTHLY_MULTIPLIERS, get_season_label
from tools.transport import estimate_transport

logger = logging.getLogger(__name__)


def _load_city_regions() -> Dict[str, str]:
    """Load city -> region mapping from the seed file."""
    seed_path = (
        Path(__file__).parent.parent / "data" / "european_cities_seed.json"
    )
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_cities = json.load(f)
        return {
            city["name"]: city.get("region", "western_europe")
            for city in seed_cities
        }
    except Exception as e:
        logger.warning(
            f"Could not load city regions for pricing calendar: {e}"
        )
        return {}


def _best_weather_months(cities: List[str]) -> List[str]:
    """Infer good-weather months from regional best-month metadata."""
    city_regions = _load_city_regions()
    month_sets = []

    for city in cities:
        region = city_regions.get(city, "western_europe")
        month_sets.append(set(REGIONAL_BEST_MONTHS.get(region, [])))

    if not month_sets:
        return []

    common_months = set.intersection(*month_sets)
    best_months = sorted(common_months or set.union(*month_sets))
    return [calendar.month_abbr[m] for m in best_months]


def get_pricing_calendar(
    cities: List[str],
    travel_style: str,
    departure_city: str,
    nights_per_city: Optional[Dict[str, int]] = None,
    fixed_costs: float = 0.0,
    return_city: Optional[str] = None,
    transport_modes: Optional[List[str]] = None,
    route_priority: str = "best_balance",
    directness: str = "allow_connections",
) -> Dict[str, Any]:
    """Estimate route costs across all 12 months for a city list.

    Transport and accommodation are recalculated per month; fixed costs
    (food, activities) can be included for comparability with the itinerary.
    """
    monthly_costs: List[Dict[str, Any]] = []
    nights_per_city = nights_per_city or {city: 2 for city in cities}

    for month, multiplier in MONTHLY_MULTIPLIERS.items():
        flights = estimate_transport(
            departure_city=departure_city,
            destinations=cities,
            travel_month=month,
            travel_style=travel_style,
            return_city=return_city or departure_city,
            transport_modes=transport_modes,
            route_priority=route_priority,
            directness=directness,
        )
        accommodation = estimate_accommodation(
            cities=cities,
            nights_per_city=nights_per_city,
            travel_style=travel_style,
            travel_month=month,
        )
        estimated_cost = (
            flights.get("total_flights_cost", 0)
            + accommodation.get("total_accommodation_cost", 0)
            + fixed_costs
        )
        monthly_costs.append({
            "month": month,
            "month_name": calendar.month_name[month],
            "estimated_cost": round(estimated_cost, 2),
            "flight_multiplier": multiplier,
            "season_label": get_season_label(month),
        })

    cheapest = min(monthly_costs, key=lambda item: item["estimated_cost"])
    most_expensive = max(
        monthly_costs, key=lambda item: item["estimated_cost"]
    )

    return {
        "monthly_costs": monthly_costs,
        "cheapest_month": {
            "month": cheapest["month"],
            "month_name": cheapest["month_name"],
            "estimated_cost": cheapest["estimated_cost"],
        },
        "most_expensive_month": {
            "month": most_expensive["month"],
            "month_name": most_expensive["month_name"],
            "estimated_cost": most_expensive["estimated_cost"],
        },
        "best_weather_months": _best_weather_months(cities),
    }
