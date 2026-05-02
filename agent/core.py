import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Tuple

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


def _get_travel_year(preferences: dict) -> int:
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
            logger.warning(f"Could not parse travel_start_date '{start_date}', using 2025 weather reference.")
    return 2025


def _llm_decide_cities(top_cities: list, preferences: dict) -> Tuple[list, dict]:
    """Ask the LLM to pick cities and distribute nights, then parse the result.

    When num_countries is specified the deterministic Python fallback is used
    directly — small LLMs reliably ignore multi-constraint prompts, so we don't
    waste an LLM call on something Python handles correctly every time.
    """
    num_countries = preferences.get("num_countries", 4)

    # Bypass the LLM entirely when a specific country count is requested.
    # The Python fallback enforces the constraint deterministically.
    if num_countries < 99:
        logger.info(
            f"num_countries={num_countries} — using Python fallback for "
            "guaranteed country diversity (LLM ignored for city selection)."
        )
        return _fallback_city_distribution(top_cities, preferences)

    duration = preferences["duration"]
    pace = preferences.get("pace", "moderate")
    city_names = [c["name"] for c in top_cities]

    prompt = f"""You are a travel planner. Given a {duration}-day trip at a '{pace}' pace,
choose how many cities to visit and how many nights to spend in each.

Top scored cities (in order): {city_names}

Rules:
- slow pace: pick 2 cities
- moderate pace: pick 3 cities
- fast pace: pick 4 cities
- Total nights must add up to exactly {duration}
- Minimum 1 night per city
- Choose cities from different countries where possible

Reply ONLY with valid JSON like this example (no explanation, no markdown):
{{"cities": ["Barcelona", "Paris"], "nights": {{"Barcelona": 5, "Paris": 5}}}}"""

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
        logger.warning(f"LLM response could not be parsed ({e}), using fallback distribution.")
        return _fallback_city_distribution(top_cities, preferences)


def _fallback_city_distribution(top_cities: list, preferences: dict) -> Tuple[list, dict]:
    """Pure Python fallback — always respects the country-count constraint."""
    duration = preferences["duration"]
    pace = preferences.get("pace", "moderate")
    num_countries = preferences.get("num_countries", 4)
    pace_map = {"slow": 2, "moderate": 3, "fast": 4}
    pace_target = pace_map.get(pace, 3)

    # City count must be at least num_countries (one city per requested country).
    # e.g. 4 countries + moderate pace (3 cities) → need 4 cities, not 3.
    if num_countries < 99:
        target = min(max(pace_target, num_countries), len(top_cities))
    else:
        target = min(pace_target, len(top_cities))

    if num_countries < 99:
        # Phase 1: pick exactly one city per unique country up to num_countries.
        selected, countries_seen = [], set()
        for city in top_cities:
            if len(countries_seen) >= num_countries:
                break
            country = city.get("country", "?")
            if country not in countries_seen:
                selected.append(city["name"])
                countries_seen.add(country)
        # Phase 2: fill remaining slots with more cities from those same countries.
        for city in top_cities:
            if len(selected) >= target:
                break
            if city["name"] not in selected and city.get("country") in countries_seen:
                selected.append(city["name"])
    else:
        selected = [c["name"] for c in top_cities[:target]]

    if not selected:
        selected = [top_cities[0]["name"]] if top_cities else ["Barcelona"]

    base = duration // len(selected)
    extra = duration % len(selected)
    nights = {c: base + (1 if i < extra else 0) for i, c in enumerate(selected)}
    return selected, nights


def run_agent(preferences: Dict[str, Any], progress_callback=None) -> Tuple[str, Dict[str, Any]]:
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
    logger.info("EUROTRIP AGENT — Starting planning pipeline")
    logger.info("=" * 50)

    # ── Step 1: Score destinations ───────────────────────────────────────────
    _cb("🗺️ Scoring 40 European destinations...")
    logger.info("Step 1/6 — Scoring destinations...")
    destinations_result = score_destinations(preferences)
    top_cities = destinations_result.get("top_destinations", [])

    if not top_cities:
        raise RuntimeError("No destinations found. Check cities.json data file.")

    # Never recommend the departure city as a destination.
    departure_lower = preferences.get("departure_city", "").strip().lower()
    top_cities = [c for c in top_cities if c["name"].strip().lower() != departure_lower]

    if not top_cities:
        raise RuntimeError("All top destinations matched the departure city. Try a different departure.")

    # ── Step 2: LLM decides cities + nights ─────────────────────────────────
    _cb("🤖 AI selecting your cities and planning nights...")
    logger.info("Step 2/6 — LLM selecting cities and distributing nights...")
    selected_cities, nights_per_city = _llm_decide_cities(top_cities, preferences)

    # ── Step 2b: Fetch live Wikipedia + weather data ─────────────────────────
    _cb(f"🌐 Fetching live data for {', '.join(selected_cities)}...")
    logger.info("Step 2b/6 — Fetching live Wikipedia & weather data...")
    web_data = enrich_cities(
        selected_cities,
        top_cities,
        preferences["travel_month"],
        year=_get_travel_year(preferences),
    )

    # ── Step 3: Estimate transport ───────────────────────────────────────────
    _cb(f"✈️ Estimating transport from {preferences['departure_city']}...")
    logger.info(f"Step 3/6 — Estimating transport: {preferences['departure_city']} → {selected_cities}")
    flights_result = estimate_transport(
        departure_city=preferences["departure_city"],
        destinations=selected_cities,
        travel_month=preferences["travel_month"],
        travel_style=preferences["travel_style"],
        return_city=preferences.get("return_city", preferences["departure_city"]),
        transport_modes=preferences.get("transport_modes"),
        route_priority=preferences.get("route_priority", "best_balance"),
        directness=preferences.get("directness", "allow_connections"),
    )

    # ── Step 4: Estimate accommodation ──────────────────────────────────────
    _cb("🏨 Estimating accommodation costs...")
    logger.info("Step 4/6 — Estimating accommodation...")
    accommodation_result = estimate_accommodation(
        cities=selected_cities,
        nights_per_city=nights_per_city,
        travel_style=preferences["travel_style"],
        travel_month=preferences["travel_month"],
    )

    # ── Step 5: Get activities ───────────────────────────────────────────────
    _cb("🎭 AI generating activities for each city...")
    logger.info("Step 5/6 — Selecting activities...")
    activities_result = get_activities(
        cities=selected_cities,
        preferences=preferences["activity_preferences"],
        nights_per_city=nights_per_city,
    )

    # ── Step 6: Calculate budget ─────────────────────────────────────────────
    _cb("💶 Calculating budget and pricing calendar...")
    logger.info("Step 6/6 — Calculating budget...")
    trip_plan = {
        "destinations": selected_cities,
        "nights_per_city": nights_per_city,
        "travel_style": preferences["travel_style"],
        "flights": flights_result,
        "accommodation": accommodation_result,
        "activities": activities_result,
        "web_data": web_data,
    }
    budget_result = calculate_budget(
        trip_plan=trip_plan,
        user_budget=preferences["budget"],
        travel_style=preferences["travel_style"],
        duration=preferences["duration"],
    )

    # ── Replan if over budget ────────────────────────────────────────────────
    if budget_result["is_over_budget"]:
        logger.warning("Over budget — triggering replanner...")
        replan_result = replan(trip_plan, budget_result, top_cities, preferences)
        trip_plan = replan_result["adjusted_trip_plan"]
        budget_result = replan_result["new_budget_result"]
        for change in replan_result["changes_made"]:
            logger.info(f"Replanning: {change}")

    trip_plan["pricing_calendar"] = get_pricing_calendar(
        cities=trip_plan["destinations"],
        travel_style=trip_plan["travel_style"],
        departure_city=preferences["departure_city"],
        nights_per_city=trip_plan["nights_per_city"],
        fixed_costs=budget_result.get("activities_cost", 0) + budget_result.get("food_cost", 0),
        return_city=preferences.get("return_city", preferences["departure_city"]),
        transport_modes=preferences.get("transport_modes"),
        route_priority=preferences.get("route_priority", "best_balance"),
        directness=preferences.get("directness", "allow_connections"),
    )

    _cb("✅ Assembling your itinerary...")
    logger.info("Pipeline complete. Assembling final itinerary...")
    final_itinerary = assemble_itinerary(trip_plan, budget_result, preferences)
    return final_itinerary, budget_result, trip_plan


def run_critic(itinerary: str, preferences: dict) -> str:
    """
    Runs a secondary LLM call to critique the finalized itinerary.

    Args:
        itinerary: The formatted itinerary string.
        preferences: The original user preferences.

    Returns:
        A short critique string with 1-2 improvement suggestions.
    """
    logger.info("Running critic agent...")
    prompt = f"""Review this European travel itinerary for a traveller with these preferences: {preferences}.

Itinerary:
{itinerary}

Check:
1. Is the budget allocation realistic for these cities?
2. Are the cities in a geographically logical order (no unnecessary backtracking)?
3. Are the activities well matched to the stated preferences?

Write a short review (3-5 sentences) with 1-2 specific improvement suggestions."""

    response = LLM.invoke([HumanMessage(content=prompt)])
    return response.content
