import json
import logging
from pathlib import Path
from tools.seasonality import get_month_multiplier

logger = logging.getLogger(__name__)

def _get_departure_region(city: str) -> str:
    """Helper function to map a departure city to a broader region."""
    eastern_europe = ["sofia", "bucharest", "warsaw", "budapest", "prague", "krakow", "riga", "tallinn", "vilnius"]
    western_europe = ["madrid", "barcelona", "paris", "amsterdam", "berlin", "rome", "milan", "vienna", "zurich", "brussels"]
    
    city_lower = city.lower()
    if city_lower in eastern_europe:
        return "from_eastern_europe"
    elif city_lower in western_europe:
        return "from_western_europe"
    # We can infer some typical non-EU cities for robustness
    elif city_lower in ["london", "manchester", "edinburgh", "dublin"]:
        return "from_uk"
    elif city_lower in ["new york", "toronto", "chicago", "los angeles", "miami"]:
        return "from_north_america"
        
    # Default fallback as specified in edge cases
    logger.warning(f"Departure city '{city}' not recognized. Defaulting to western_europe.")
    return "from_western_europe"


def estimate_flights(
    departure_city: str,
    destinations: list,
    travel_month: int,
    travel_style: str = "mid_range",
    return_city: str = None,
) -> dict:
    """
    Estimates flight costs from a departure city to a list of destinations,
    including inter-city European flights.
    
    Args:
        departure_city (str): The city where the trip starts and ends.
        destinations (list): A list of city names to visit.
        travel_month (int): The month of travel (1-12) for seasonal multipliers.
        travel_style (str): The travel style to determine inter-city flight costs.
        return_city (str): Optional city where the trip ends. Defaults to departure_city.
        
    Returns:
        dict: A breakdown of flight legs, their estimated costs, and the total cost.
    """
    return_city = return_city or departure_city
    logger.info(f"Estimating flights from {departure_city} to {destinations}, ending in {return_city}, for month {travel_month}.")
    
    base_dir = Path(__file__).parent.parent
    cities_path = base_dir / "data" / "cities.json"
    
    try:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Database not found: Could not load cities.json at {cities_path}")
        return {"flight_legs": [], "total_flights_cost": 0}
        
    # Map city names to their flight cost data
    city_cost_map = {city["name"]: city.get("avg_flight_cost", {}) for city in cities_data}
    
    region_key = _get_departure_region(departure_city)
    
    month_multiplier = get_month_multiplier(travel_month)
        
    legs = []
    total_cost = 0.0
    
    if not destinations:
        return {"flight_legs": legs, "total_flights_cost": total_cost}

    # Determine flat inter-city rates based on travel style
    inter_city_rates = {
        "backpacker": 60,
        "mid_range": 115,
        "luxury": 225
    }
    inter_city_cost = inter_city_rates.get(travel_style, 115)

    # 1. Outbound Leg: Departure City -> First Destination
    first_dest = destinations[0]
    base_outbound = city_cost_map.get(first_dest, {}).get(region_key, 150) # Fallback cost if missing
    cost_outbound = round(base_outbound * month_multiplier)
    
    legs.append({"from": departure_city, "to": first_dest, "cost_eur": cost_outbound, "type": "outbound"})
    total_cost += cost_outbound
    
    # 2. Inter-city Legs: Hop between destinations
    for i in range(len(destinations) - 1):
        city_a = destinations[i]
        city_b = destinations[i+1]
        legs.append({"from": city_a, "to": city_b, "cost_eur": inter_city_cost, "type": "inter_city"})
        total_cost += inter_city_cost
        
    # 3. Inbound Leg: Last Destination -> Departure City
    last_dest = destinations[-1]
    base_inbound = city_cost_map.get(last_dest, {}).get(region_key, 150)
    cost_inbound = round(base_inbound * month_multiplier)
    
    legs.append({"from": last_dest, "to": return_city, "cost_eur": cost_inbound, "type": "inbound"})
    total_cost += cost_inbound
    
    logger.info(f"Total estimated flight cost calculated: €{total_cost}")
    return {"flight_legs": legs, "total_flights_cost": total_cost}
