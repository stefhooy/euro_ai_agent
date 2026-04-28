import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def score_destinations(preferences: dict) -> dict:
    """
    Scores and selects the best European cities based on user preferences.
    
    Args:
        preferences (dict): A dictionary containing user trip preferences:
                            budget, duration, travel_style, activity_preferences,
                            and travel_month.
                            
    Returns:
        dict: A dictionary with the top 5 matching cities, sorted by score.
    """
    logger.info("Starting destination scoring process based on user preferences.")
    
    # Dynamically load the cities.json file from the data folder
    base_dir = Path(__file__).parent.parent
    cities_path = base_dir / "data" / "cities.json"
    
    try:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities = json.load(f)
    except FileNotFoundError:
        logger.error(f"Database not found: Could not load cities.json at {cities_path}")
        return {"top_destinations": []}

    budget = preferences.get("budget", 0)
    duration = preferences.get("duration", 1)
    budget_per_day = budget / duration if duration > 0 else 0
    travel_style = preferences.get("travel_style", "mid_range")
    activity_prefs = preferences.get("activity_preferences", [])
    travel_month = preferences.get("travel_month", 6)

    scored_cities = []

    for city in cities:
        reasons = []
        
        # 1. Activity match score (40 points)
        city_tags = city.get("activity_tags", [])
        if activity_prefs:
            matches = set(activity_prefs).intersection(set(city_tags))
            activity_score = (len(matches) / len(activity_prefs)) * 40
            if matches:
                reasons.append(f"Matches {len(matches)} of your activity preferences.")
        else:
            activity_score = 40
            
        # 2. Budget score (40 points)
        city_cost = city.get("avg_daily_cost", {}).get(travel_style, 0)
        if budget_per_day <= 0:
            budget_score = 0
        elif city_cost <= budget_per_day:
            budget_score = 40
            reasons.append("Fits perfectly within your daily budget.")
        elif city_cost <= budget_per_day * 1.5:
            # Scaled down if over by up to 50%
            overage_ratio = (city_cost - budget_per_day) / (budget_per_day * 0.5)
            budget_score = 40 * (1 - overage_ratio)
            reasons.append("Slightly over your daily budget but manageable.")
        else:
            budget_score = 0
            reasons.append("Significantly over your daily budget.")
            
        # 3. Season score (20 points)
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
        
    # Sort by top 5 highest scored cities
    top_cities = sorted(scored_cities, key=lambda x: x["score"], reverse=True)[:5]
    
    logger.info(f"Selected top {len(top_cities)} destinations.")
    return {"top_destinations": top_cities}