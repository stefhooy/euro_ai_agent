import json
import logging

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

LLM = ChatOllama(model="llama3.1:8b", temperature=0.4)

FALLBACK_ACTIVITIES = {
    "museums":   [("City Museum Visit", 12), ("Art Gallery", 8), ("National History Museum", 10)],
    "food":      [("Local Food Market Tour", 0), ("Traditional Restaurant Dinner", 30), ("Cooking Class", 45)],
    "history":   [("Old Town Walking Tour", 15), ("Historic Cathedral", 5), ("Archaeological Site", 12)],
    "nightlife": [("Evening Bar Crawl", 20), ("Rooftop Bar", 15), ("Live Music Venue", 10)],
    "nature":    [("City Park Walk", 0), ("Botanical Garden", 8), ("Riverside Stroll", 0)],
    "shopping":  [("Local Market Browse", 0), ("High Street Shopping", 0), ("Artisan Quarter", 0)],
    "adventure": [("Bike Tour", 25), ("Day Hike", 10), ("Kayaking Trip", 35)],
}


def _generate_activities_llm(city: str, country: str, preferences: list, days: int) -> list:
    """
    Asks the LLM to generate a list of activities for a city matching preferences.

    Args:
        city: City name.
        country: Country name.
        preferences: List of activity category strings.
        days: Number of days in the city.

    Returns:
        List of activity dicts with name, category, cost_eur, duration_hours, description.
    """
    num_activities = max(4, days * 2)
    categories_str = ", ".join(preferences) if preferences else "general sightseeing"

    prompt = f"""Generate exactly {num_activities} specific tourist activities for {city}, {country}.
Focus on these categories: {categories_str}.

Return ONLY a valid JSON array — no explanation, no markdown, no extra text.
Each item must have these exact keys:
- "name": specific activity name (e.g. "Acropolis Museum Visit", not just "museum")
- "category": one of {preferences if preferences else ["sightseeing"]}
- "cost_eur": integer cost in euros (0 if free)
- "duration_hours": integer 1 to 4
- "description": one sentence describing the activity

Example format:
[{{"name": "Acropolis Visit", "category": "history", "cost_eur": 20, "duration_hours": 3, "description": "Explore the ancient hilltop citadel of Athens."}}]"""

    try:
        response = LLM.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        # Find the JSON array in the response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON array found in LLM response.")

        activities = json.loads(raw[start:end])
        # Validate each activity has required fields
        valid = []
        for act in activities:
            if all(k in act for k in ("name", "category", "cost_eur")):
                act["cost_eur"] = int(act.get("cost_eur", 0))
                act["duration_hours"] = int(act.get("duration_hours", 2))
                act["description"] = act.get("description", "")
                valid.append(act)

        if len(valid) < 3:
            raise ValueError(f"Only {len(valid)} valid activities returned.")

        logger.info(f"LLM generated {len(valid)} activities for {city}.")
        return valid

    except Exception as e:
        logger.warning(f"LLM activity generation failed for {city}: {e}. Using fallback.")
        return None


def _fallback_activities(preferences: list, days: int) -> list:
    """Generates generic activities when the LLM fails."""
    activities = []
    used_prefs = preferences if preferences else list(FALLBACK_ACTIVITIES.keys())
    for pref in used_prefs:
        for name, cost in FALLBACK_ACTIVITIES.get(pref, []):
            activities.append({
                "name": name,
                "category": pref,
                "cost_eur": cost,
                "duration_hours": 2,
                "description": f"A popular {pref} experience.",
            })
    return activities[:max(4, days * 2)]


def get_activities(cities: list, preferences: list, nights_per_city: dict = None) -> dict:
    """
    Selects and schedules activities for each city using LLM generation.
    Works for any city in the world — not limited to a static dataset.
    Falls back to generic activities if LLM fails.

    Args:
        cities: List of city name strings.
        preferences: List of activity category preferences.
        nights_per_city: Dict mapping city name to number of nights.

    Returns:
        Dict with city_activities breakdown and total_activities_cost.
    """
    logger.info(f"Generating activities for {cities} via LLM...")

    if nights_per_city is None:
        nights_per_city = {}

    # We need country info for a better LLM prompt — derive from seed if possible
    from pathlib import Path
    import json as _json

    seed_path = Path(__file__).parent.parent / "data" / "european_cities_seed.json"
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            seed = {c["name"]: c.get("country", "Europe") for c in _json.load(f)}
    except Exception:
        seed = {}

    city_activities_result = {}
    total_activities_cost = 0.0

    for city in cities:
        days = nights_per_city.get(city, 2)
        country = seed.get(city)

        if country is None:
            city_activities_result[city] = {
                "activities": [],
                "city_total_cost": 0.0,
            }
            logger.warning(f"No seed data found for {city}; returning no activities.")
            continue

        raw_activities = _generate_activities_llm(city, country, preferences, days)
        if not raw_activities:
            raw_activities = _fallback_activities(preferences, days)

        # Schedule activities across days (max 2 paid per day)
        scheduled = []
        city_cost = 0.0
        current_day = 1
        daily_paid = 0

        for act in raw_activities:
            if act["cost_eur"] > 0:
                if daily_paid >= 2:
                    current_day = min(current_day + 1, max(days, 1))
                    daily_paid = 0
                daily_paid += 1
            scheduled.append({**act, "day": current_day})
            city_cost += act["cost_eur"]

        city_activities_result[city] = {
            "activities": scheduled,
            "city_total_cost": city_cost,
        }
        total_activities_cost += city_cost
        logger.info(f"Activities ready for {city}: {len(scheduled)} activities, €{city_cost:.0f} total.")

    return {
        "city_activities": city_activities_result,
        "total_activities_cost": total_activities_cost,
    }
