import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Define daily food rates based on travel style as per project spec
FOOD_DAILY_RATES = {
    "backpacker": 20,
    "mid_range": 45,
    "luxury": 100,
}

def calculate_budget(
    trip_plan: Dict[str, Any], user_budget: float, travel_style: str, duration: int
) -> Dict[str, Any]:
    """
    Calculates the total trip budget and compares it against the user's budget.

    This function aggregates costs from flights, accommodation, and activities,
    adds an estimated food cost, and provides a final breakdown.

    Args:
        trip_plan (dict): A dictionary containing the outputs from other tools.
                          It should have keys like 'flights', 'accommodation', 
                          and 'activities', which in turn contain their total costs.
        user_budget (float): The total budget provided by the user.
        travel_style (str): The user's travel style ('backpacker', 'mid_range', 'luxury').
        duration (int): The total duration of the trip in days.

    Returns:
        dict: A full breakdown of costs, the grand total, the user's budget,
              the remaining buffer, and a flag indicating if the budget is exceeded.
    """
    logger.info(f"Calculating final budget for a {duration}-day, {travel_style} trip.")

    # Safely extract costs from the aggregated trip_plan dictionary
    total_flights = trip_plan.get("flights", {}).get("total_flights_cost", 0.0)
    total_accommodation = trip_plan.get("accommodation", {}).get("total_accommodation_cost", 0.0)
    total_activities = trip_plan.get("activities", {}).get("total_activities_cost", 0.0)

    # Calculate estimated food cost
    food_rate = FOOD_DAILY_RATES.get(travel_style, 45)  # Default to mid_range if style is unknown
    total_food = food_rate * duration
    logger.debug(f"Food cost calculated: €{food_rate}/day * {duration} days = €{total_food}")

    # Sum up all cost components for the grand total
    grand_total = total_flights + total_accommodation + total_activities + total_food

    # Compare with user's budget and calculate the buffer
    buffer = user_budget - grand_total
    is_over_budget = grand_total > user_budget

    if is_over_budget:
        logger.warning(f"Trip is OVER budget by €{-buffer:.2f}. Grand Total: €{grand_total:.2f}, Budget: €{user_budget:.2f}")
    else:
        logger.info(f"Trip is UNDER budget by €{buffer:.2f}. Grand Total: €{grand_total:.2f}, Budget: €{user_budget:.2f}")

    return {
        "flights_cost": total_flights,
        "accommodation_cost": total_accommodation,
        "activities_cost": total_activities,
        "food_cost": total_food,
        "grand_total": grand_total,
        "user_budget": user_budget,
        "buffer": buffer,
        "is_over_budget": is_over_budget,
    }