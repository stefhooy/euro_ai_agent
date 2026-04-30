import logging
from pathlib import Path

from tools.city_data import load_all_city_profiles

logger = logging.getLogger(__name__)


def score_destinations(preferences: dict) -> dict:
    """
    Scores and selects the best European cities based on user preferences.
    City profiles are built dynamically using Nominatim and Teleport APIs
    with regional cost fallbacks, so any of the 40 seed cities can be recommended.

    Args:
        preferences: Dict containing budget, duration, travel_style,
                     activity_preferences, and travel_month.

    Returns:
        Dict with 'top_destinations' — top 5 cities sorted by score.
    """
    logger.info("Starting destination scoring using live city profiles...")

    seed_path = str(Path(__file__).parent.parent / "data" / "european_cities_seed.json")
    cities = load_all_city_profiles(seed_path)

    budget = preferences.get("budget", 0)
    duration = preferences.get("duration", 1)
    budget_per_day = budget / duration if duration > 0 else 0
    travel_style = preferences.get("travel_style", "mid_range")
    activity_prefs = preferences.get("activity_preferences", [])
    travel_month = preferences.get("travel_month", 6)

    scored_cities = []

    for city in cities:
        reasons = []

        # ── Activity match score (40 points) ─────────────────────────────────
        city_tags = city.get("activity_tags", [])
        if activity_prefs:
            matches = set(activity_prefs).intersection(set(city_tags))
            activity_score = (len(matches) / len(activity_prefs)) * 40
            if matches:
                reasons.append(f"Matches {len(matches)} of your activity preferences.")
        else:
            activity_score = 40

        # ── Budget score (40 points) ─────────────────────────────────────────
        city_cost = city.get("avg_daily_cost", {}).get(travel_style, 0)
        if budget_per_day <= 0:
            budget_score = 0
        elif city_cost <= budget_per_day:
            budget_score = 40
            reasons.append("Fits perfectly within your daily budget.")
        elif city_cost <= budget_per_day * 1.5:
            overage_ratio = (city_cost - budget_per_day) / (budget_per_day * 0.5)
            budget_score = 40 * (1 - overage_ratio)
            reasons.append("Slightly over your daily budget but manageable.")
        else:
            budget_score = 0
            reasons.append("Significantly over your daily budget.")

        # ── Season score (20 points) ─────────────────────────────────────────
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

    top_cities = sorted(scored_cities, key=lambda x: x["score"], reverse=True)[:5]
    logger.info(f"Top {len(top_cities)} destinations selected from {len(cities)} cities.")
    return {"top_destinations": top_cities}
