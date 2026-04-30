import json
import logging
from pathlib import Path
from tools.seasonality import get_month_multiplier

logger = logging.getLogger(__name__)

# Hardcoded recommended areas per city for a nice personalized touch
RECOMMENDED_AREAS = {
    "Barcelona": "Eixample",
    "Paris": "Le Marais",
    "Rome": "Trastevere",
    "Amsterdam": "Jordaan",
    "Prague": "Old Town (Staré Město)",
    "Lisbon": "Alfama",
    "Vienna": "Innere Stadt",
    "Budapest": "District VII (Erzsébetváros)",
    "Berlin": "Mitte / Prenzlauer Berg",
    "Dubrovnik": "Old Town",
    "Athens": "Plaka",
    "Porto": "Ribeira"
}

def estimate_accommodation(cities: list, nights_per_city: dict, travel_style: str, travel_month: int = 4) -> dict:
    """
    Estimates accommodation costs for a list of cities based on travel style and duration.
    
    Args:
        cities (list): A list of city names to visit.
        nights_per_city (dict): A dictionary mapping city names to the number of nights staying there.
        travel_style (str): The user's travel style (backpacker, mid_range, luxury).
        travel_month (int): The month of travel (1-12) for seasonal multipliers.
        
    Returns:
        dict: A breakdown of accommodation costs per city and the total estimated cost.
    """
    logger.info(f"Estimating accommodation for {cities} with style '{travel_style}' in month {travel_month}.")
    month_multiplier = get_month_multiplier(travel_month)
    
    base_dir = Path(__file__).parent.parent
    cities_path = base_dir / "data" / "cities.json"
    
    try:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Database not found: Could not load cities.json at {cities_path}")
        return {"city_breakdown": {}, "total_accommodation_cost": 0}
        
    # Map city names to their daily cost data
    city_cost_map = {city["name"]: city.get("avg_daily_cost", {}) for city in cities_data}
    
    city_breakdown = {}
    total_accommodation_cost = 0.0
    
    for city in cities:
        nights = nights_per_city.get(city, 1)  # Default to 1 night if missing
        city_costs = city_cost_map.get(city, {})
        avg_daily_cost = city_costs.get(travel_style, 100)  # Fallback to 100 if missing
        
        # Calculate base nightly cost based on travel style percentage
        if travel_style == "luxury":
            base_nightly = avg_daily_cost * 0.50
        else:
            base_nightly = avg_daily_cost * 0.40
            
        # Clamp to realistic ranges
        if travel_style == "backpacker":
            nightly_cost = max(15, min(35, base_nightly))
        elif travel_style == "mid_range":
            nightly_cost = max(60, min(120, base_nightly))
        elif travel_style == "luxury":
            nightly_cost = max(150, min(400, base_nightly))
        else:
            nightly_cost = base_nightly
            
        nightly_cost = round(nightly_cost * month_multiplier)
        city_total = nightly_cost * nights
        total_accommodation_cost += city_total
        
        recommended_area = RECOMMENDED_AREAS.get(city, "City Center")
        
        city_breakdown[city] = {
            "nightly_cost": nightly_cost,
            "total_cost": city_total,
            "recommended_area": recommended_area,
            "nights": nights
        }
        
        logger.debug(f"Calculated accommodation for {city}: €{nightly_cost}/night for {nights} nights.")
        
    logger.info(f"Total estimated accommodation cost: €{total_accommodation_cost}")
    
    return {
        "city_breakdown": city_breakdown,
        "total_accommodation_cost": total_accommodation_cost
    }
