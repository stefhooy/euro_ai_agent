import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_activities(cities: list, preferences: list, nights_per_city: dict = None) -> dict:
    """
    Selects and schedules activities for a list of cities based on user preferences.
    
    Args:
        cities (list): A list of city names to visit.
        preferences (list): A list of user activity preferences (e.g., "museums", "food").
        nights_per_city (dict, optional): Mapping of city to number of nights. 
                                          Defaults to 2 nights if not provided.
        
    Returns:
        dict: A dictionary containing the itinerary of activities per city and total activity costs.
    """
    logger.info(f"Selecting activities for {cities} matching preferences: {preferences}.")
    
    if nights_per_city is None:
        nights_per_city = {}
        
    base_dir = Path(__file__).parent.parent
    activities_path = base_dir / "data" / "activity_costs.json"
    
    try:
        with open(activities_path, "r", encoding="utf-8") as f:
            all_activities = json.load(f)
    except FileNotFoundError:
        logger.error(f"Database not found: Could not load activity_costs.json at {activities_path}")
        return {"city_activities": {}, "total_activities_cost": 0}
        
    city_activities_result = {}
    total_activities_cost = 0.0
    
    for city in cities:
        city_data = all_activities.get(city, [])
        if not city_data:
            logger.warning(f"No activities found for city: {city}")
            city_activities_result[city] = {"activities": [], "city_total_cost": 0}
            continue
            
        # Filter matching activities based on user preferences
        matched_activities = [act for act in city_data if act["category"] in preferences]
        
        # Fallback: if fewer than 3 match, add top free activities
        if len(matched_activities) < 3:
            free_activities = [act for act in city_data if act["cost_eur"] == 0 and act not in matched_activities]
            needed = 3 - len(matched_activities)
            matched_activities.extend(free_activities[:needed])
            
        # If STILL fewer than 3 (e.g., no free activities left), just grab whatever is available
        if len(matched_activities) < 3:
            remaining = [act for act in city_data if act not in matched_activities]
            needed = 3 - len(matched_activities)
            matched_activities.extend(remaining[:needed])
            
        # Assign to days
        days = nights_per_city.get(city, 2)  # Default to 2 days for scheduling if missing
        if days < 1:
            days = 1
            
        scheduled_activities = []
        city_cost = 0
        
        current_day = 1
        daily_paid_count = 0
        
        for act in matched_activities:
            # Basic scheduling logic: max 2-3 paid activities per day
            is_paid = act["cost_eur"] > 0
            if is_paid:
                if daily_paid_count >= 2:
                    current_day = min(current_day + 1, days)
                    daily_paid_count = 0
                daily_paid_count += 1
            
            scheduled_activities.append({
                "name": act["name"],
                "cost_eur": act["cost_eur"],
                "day": current_day,
                "category": act["category"],
                "description": act.get("description", "")
            })
            city_cost += act["cost_eur"]
            
        city_activities_result[city] = {
            "activities": scheduled_activities,
            "city_total_cost": city_cost
        }
        total_activities_cost += city_cost
        
    logger.info(f"Total estimated activities cost: €{total_activities_cost}")
    
    return {
        "city_activities": city_activities_result,
        "total_activities_cost": total_activities_cost
    }