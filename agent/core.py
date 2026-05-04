import json
import logging
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from agent.memory import TripMemory
from agent.planner import assemble_itinerary
from tools.accommodation import estimate_accommodation
from tools.activities import get_activities
from tools.budget import calculate_budget
from tools.destination import score_destinations
from tools.pricing_calendar import get_pricing_calendar
from tools.replanner import replan
from tools.transport import estimate_transport
from tools.web_search import enrich_cities

logger = logging.getLogger(__name__)

LLM = ChatOllama(model="llama3.1:8b", temperature=0.3)

# ---------------------------------------------------------------------------
# Geographic helpers for route ordering
# ---------------------------------------------------------------------------

def _load_seed_coords() -> Dict[str, Tuple[float, float]]:
    seed = Path(__file__).parent.parent / "data" / "european_cities_seed.json"
    try:
        with open(seed, encoding="utf-8") as f:
            return {c["name"]: (c["lat"], c["lon"]) for c in json.load(f)}
    except Exception:
        return {}


_SEED_COORDS: Dict[str, Tuple[float, float]] = _load_seed_coords()

# Coordinates for departure cities that are not in the seed dataset.
_EXTRA_DEP_COORDS: Dict[str, Tuple[float, float]] = {
    "Glasgow":     (55.8642,   -4.2518),
    "Birmingham":  (52.4862,   -1.8904),
    "Bristol":     (51.4545,   -2.5879),
    "Liverpool":   (53.4084,   -2.9916),
    "Leeds":       (53.8008,   -1.5491),
    "Cardiff":     (51.4816,   -3.1791),
    "Marseille":   (43.2965,    5.3698),
    "Toulouse":    (43.6047,    1.4442),
    "Turin":       (45.0703,    7.6869),
    "Bilbao":      (43.2630,   -2.9350),
    "Malaga":      (36.7213,   -4.4214),
    "The Hague":   (52.0705,    4.3007),
    "Dusseldorf":  (51.2217,    6.7762),
    "Stuttgart":   (48.7758,    9.1829),
    "New York":    (40.7128,  -74.0060),
    "Los Angeles": (34.0522,  -118.2437),
    "Toronto":     (43.6532,  -79.3832),
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


def _nearest_neighbor_order(
    departure_city: str,
    selected_cities: List[str],
) -> List[str]:
    """Reorder cities by nearest-neighbour traversal from departure.

    Prevents zigzag routes like Tirana->Paris->Sofia->London by always
    stepping to the geographically closest unvisited city next.
    Falls back to original order if departure coords are unknown.
    """
    if len(selected_cities) <= 1:
        return selected_cities

    dep_lower = departure_city.strip().lower()
    dep_coords: Optional[Tuple[float, float]] = None
    for name, coords in _SEED_COORDS.items():
        if name.lower() == dep_lower:
            dep_coords = coords
            break
    if dep_coords is None:
        for name, coords in _EXTRA_DEP_COORDS.items():
            if name.lower() == dep_lower:
                dep_coords = coords
                break
    if dep_coords is None:
        return selected_cities

    remaining = list(selected_cities)
    ordered: List[str] = []
    cur_lat, cur_lon = dep_coords

    while remaining:
        nearest = min(
            remaining,
            key=lambda n: _haversine_km(
                cur_lat, cur_lon,
                *_SEED_COORDS.get(n, (cur_lat, cur_lon)),
            ),
        )
        ordered.append(nearest)
        remaining.remove(nearest)
        cur_lat, cur_lon = _SEED_COORDS.get(nearest, (cur_lat, cur_lon))

    logger.info(f"Route ordered by proximity: {ordered}")
    return ordered


def _get_travel_year(preferences: Dict[str, Any]) -> int:
    """Return an archive year for weather lookups, capped at 2024.

    Open-Meteo archive only holds completed past data, so we never request
    a year beyond 2025 regardless of the user's chosen travel date.
    """
    start_date = preferences.get("travel_start_date")
    if isinstance(start_date, date):
        return min(start_date.year, 2025)
    if isinstance(start_date, str):
        try:
            return min(datetime.fromisoformat(start_date).year, 2025)
        except ValueError:
            logger.warning(
                f"Could not parse travel_start_date '{start_date}', "
                "using 2025 weather reference."
            )
    return 2025


def _llm_decide_cities(
    top_cities: List[Dict[str, Any]],
    preferences: Dict[str, Any],
) -> Tuple[List[str], Dict[str, int]]:
    """Ask the LLM to pick cities and distribute nights, then parse the result.

    When num_countries is specified the deterministic Python fallback is used
    directly - small LLMs reliably ignore multi-constraint prompts, so we
    don't waste an LLM call on something Python handles correctly every time.
    """
    num_countries = preferences.get("num_countries", 4)

    # Bypass the LLM entirely when a specific country count is requested.
    # The Python fallback enforces the constraint deterministically.
    if num_countries < 99:
        logger.info(
            f"num_countries={num_countries} - using Python fallback for "
            "guaranteed country diversity "
            "(LLM ignored for city selection)."
        )
        return _fallback_city_distribution(top_cities, preferences)

    duration = preferences["duration"]
    pace = preferences.get("pace", "moderate")
    city_names = [c["name"] for c in top_cities]

    prompt = (
        f"You are a travel planner. Given a {duration}-day trip at a "
        f"'{pace}' pace,\n"
        "choose how many cities to visit and how many nights to spend "
        "in each.\n\n"
        f"Top scored cities (in order): {city_names}\n\n"
        "Rules:\n"
        "- slow pace: pick 2 cities\n"
        "- moderate pace: pick 3 cities\n"
        "- fast pace: pick 4 cities\n"
        f"- Total nights must add up to exactly {duration}\n"
        "- Minimum 1 night per city\n"
        "- Choose cities from different countries where possible\n\n"
        "Reply ONLY with valid JSON like this example "
        "(no explanation, no markdown):\n"
        '{"cities": ["Barcelona", "Paris"], '
        '"nights": {"Barcelona": 5, "Paris": 5}}'
    )

    logger.info("LLM deciding city selection and night distribution...")
    response = LLM.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()

    if "```" in raw:
        raw = raw.split("```")[1].replace("json", "").strip()

    try:
        data = json.loads(raw)
        cities = data["cities"]
        nights = data["nights"]
        total = sum(nights.values())
        if total != duration:
            diff = duration - total
            nights[cities[0]] += diff
        logger.info(f"LLM chose: {cities} with nights {nights}")
        return cities, nights
    except Exception as e:
        logger.warning(
            f"LLM response could not be parsed ({e}), "
            "using fallback distribution."
        )
        return _fallback_city_distribution(top_cities, preferences)


def _fallback_city_distribution(
    top_cities: List[Dict[str, Any]],
    preferences: Dict[str, Any],
) -> Tuple[List[str], Dict[str, int]]:
    """Pure Python fallback for country and regional diversity."""
    duration = preferences["duration"]
    pace = preferences.get("pace", "moderate")
    num_countries = preferences.get("num_countries", 4)
    pace_map = {"slow": 2, "moderate": 3, "fast": 4}
    pace_target = pace_map.get(pace, 3)

    # City count must be at least num_countries (one city per requested
    # country). e.g. 4 countries + moderate pace (3 cities) -> need 4
    # cities, not 3.
    if num_countries < 99:
        target = min(max(pace_target, num_countries), len(top_cities))
    else:
        target = min(pace_target, len(top_cities))

    if num_countries < 99:
        # Phase 1: pick exactly one city per unique country up to
        # num_countries, preferring new European regions first. This keeps
        # the requested country count while avoiding overly clustered routes.
        selected, countries_seen, regions_seen = [], set(), set()
        for prefer_new_region in (True, False):
            for city in top_cities:
                if len(countries_seen) >= num_countries:
                    break
                country = city.get("country", "?")
                region = city.get("region", "")
                if country in countries_seen:
                    continue
                if (
                    prefer_new_region
                    and region
                    and region in regions_seen
                ):
                    continue
                selected.append(city["name"])
                countries_seen.add(country)
                if region:
                    regions_seen.add(region)
            if len(countries_seen) >= num_countries:
                break

        # Phase 2: fill remaining slots with more cities from those same
        # countries. Prefer a new region if the chosen country set allows it.
        for prefer_new_region in (True, False):
            for city in top_cities:
                if len(selected) >= target:
                    break
                region = city.get("region", "")
                if (
                    city["name"] in selected
                    or city.get("country") not in countries_seen
                ):
                    continue
                if (
                    prefer_new_region
                    and region
                    and region in regions_seen
                ):
                    continue
                selected.append(city["name"])
                if region:
                    regions_seen.add(region)
            if len(selected) >= target:
                break
    else:
        selected = [c["name"] for c in top_cities[:target]]

    if not selected:
        selected = [top_cities[0]["name"]] if top_cities else ["Barcelona"]

    base = duration // len(selected)
    extra = duration % len(selected)
    nights = {
        c: base + (1 if i < extra else 0)
        for i, c in enumerate(selected)
    }
    return selected, nights


def run_agent(
    preferences: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Runs the EuroTrip planning pipeline.

    Python orchestrates the tool sequence reliably. The LLM is used for
    reasoning decisions (city selection, night distribution, critique).

    Args:
        preferences: User travel preferences dict.

    Returns:
        Tuple of formatted itinerary string and budget breakdown dict.
    """
    def _cb(msg):
        if progress_callback:
            progress_callback(msg)

    memory = TripMemory()
    memory.save_preferences(preferences)

    logger.info("=" * 50)
    logger.info("EUROTRIP AGENT - Starting planning pipeline")
    logger.info("=" * 50)

    # Step 1: Score destinations
    _cb("Scoring 80 European destinations...")
    logger.info("Step 1/6 - Scoring destinations...")
    destinations_result = score_destinations(preferences)
    top_cities = destinations_result.get("top_destinations", [])

    if not top_cities:
        raise RuntimeError(
            "No destinations found. Check cities.json data file."
        )

    # Never recommend the departure city as a destination.
    departure_lower = (
        preferences.get("departure_city", "").strip().lower()
    )
    top_cities = [
        c for c in top_cities
        if c["name"].strip().lower() != departure_lower
    ]

    if not top_cities:
        raise RuntimeError(
            "All top destinations matched the departure city. "
            "Try a different departure."
        )

    # Step 2: LLM decides cities + nights
    _cb("AI selecting your cities and planning nights...")
    logger.info(
        "Step 2/6 - LLM selecting cities and distributing nights..."
    )
    selected_cities, nights_per_city = _llm_decide_cities(
        top_cities, preferences
    )

    # Order cities by nearest-neighbour from departure so the route
    # flows geographically rather than jumping across the continent.
    selected_cities = _nearest_neighbor_order(
        preferences.get("departure_city", ""), selected_cities
    )
    # Re-sync nights dict key order to match the new city order.
    nights_per_city = {c: nights_per_city[c] for c in selected_cities}

    # Step 2b: Fetch live Wikipedia + weather data
    _cb(f"Fetching live data for {', '.join(selected_cities)}...")
    logger.info(
        "Step 2b/6 - Fetching live Wikipedia & weather data..."
    )
    web_data = enrich_cities(
        selected_cities,
        top_cities,
        preferences["travel_month"],
        year=_get_travel_year(preferences),
    )

    # Step 3: Estimate transport
    _cb(
        f"Estimating transport from "
        f"{preferences['departure_city']}..."
    )
    logger.info(
        f"Step 3/6 - Estimating transport: "
        f"{preferences['departure_city']} -> {selected_cities}"
    )
    flights_result = estimate_transport(
        departure_city=preferences["departure_city"],
        destinations=selected_cities,
        travel_month=preferences["travel_month"],
        travel_style=preferences["travel_style"],
        return_city=preferences.get(
            "return_city", preferences["departure_city"]
        ),
        transport_modes=preferences.get("transport_modes"),
        route_priority=preferences.get(
            "route_priority", "best_balance"
        ),
        directness=preferences.get(
            "directness", "allow_connections"
        ),
    )

    # Step 4: Estimate accommodation
    _cb("Estimating accommodation costs...")
    logger.info("Step 4/6 - Estimating accommodation...")
    accommodation_result = estimate_accommodation(
        cities=selected_cities,
        nights_per_city=nights_per_city,
        travel_style=preferences["travel_style"],
        travel_month=preferences["travel_month"],
    )

    # Step 5: Get activities
    _cb("AI generating activities for each city...")
    logger.info("Step 5/6 - Selecting activities...")
    activities_result = get_activities(
        cities=selected_cities,
        preferences=preferences["activity_preferences"],
        nights_per_city=nights_per_city,
    )

    # Step 6: Calculate budget
    _cb("Calculating budget and pricing calendar...")
    logger.info("Step 6/6 - Calculating budget...")
    # Index scored city data by name so we can display agent reasoning
    # in the UI.
    score_map = {c["name"]: c for c in top_cities}
    destination_scores = {
        city: score_map[city]
        for city in selected_cities
        if city in score_map
    }

    trip_plan = {
        "destinations": selected_cities,
        "nights_per_city": nights_per_city,
        "travel_style": preferences["travel_style"],
        "flights": flights_result,
        "accommodation": accommodation_result,
        "activities": activities_result,
        "web_data": web_data,
        "destination_scores": destination_scores,
    }
    budget_result = calculate_budget(
        trip_plan=trip_plan,
        user_budget=preferences["budget"],
        travel_style=preferences["travel_style"],
        duration=preferences["duration"],
    )

    # Replan if over budget
    if budget_result["is_over_budget"]:
        logger.warning("Over budget - triggering replanner...")
        replan_result = replan(
            trip_plan, budget_result, top_cities, preferences
        )
        trip_plan = replan_result["adjusted_trip_plan"]
        budget_result = replan_result["new_budget_result"]
        for change in replan_result["changes_made"]:
            logger.info(f"Replanning: {change}")

    trip_plan["pricing_calendar"] = get_pricing_calendar(
        cities=trip_plan["destinations"],
        travel_style=trip_plan["travel_style"],
        departure_city=preferences["departure_city"],
        nights_per_city=trip_plan["nights_per_city"],
        fixed_costs=(
            budget_result.get("activities_cost", 0)
            + budget_result.get("food_cost", 0)
        ),
        return_city=preferences.get(
            "return_city", preferences["departure_city"]
        ),
        transport_modes=preferences.get("transport_modes"),
        route_priority=preferences.get(
            "route_priority", "best_balance"
        ),
        directness=preferences.get(
            "directness", "allow_connections"
        ),
    )

    _cb("Assembling your itinerary...")
    logger.info("Pipeline complete. Assembling final itinerary...")
    final_itinerary = assemble_itinerary(
        trip_plan, budget_result, preferences
    )
    return final_itinerary, budget_result, trip_plan


def run_critic(itinerary: str, preferences: Dict[str, Any]) -> str:
    """
    Runs a secondary LLM call to critique the finalized itinerary.

    Args:
        itinerary: The formatted itinerary string.
        preferences: The original user preferences.

    Returns:
        A short critique string with 1-2 improvement suggestions.
    """
    logger.info("Running critic agent...")
    prompt = (
        "Review this European travel itinerary for a traveller with "
        f"these preferences: {preferences}.\n\n"
        "Itinerary:\n"
        f"{itinerary}\n\n"
        "Check:\n"
        "1. Is the budget allocation realistic for these cities?\n"
        "2. Are the cities in a geographically logical order "
        "(no unnecessary backtracking)?\n"
        "3. Are the activities well matched to the stated preferences?"
        "\n\n"
        "Write a short review (3-5 sentences) with 1-2 specific "
        "improvement suggestions."
    )

    response = LLM.invoke([HumanMessage(content=prompt)])
    return response.content
