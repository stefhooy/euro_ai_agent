import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

FOOD_DAILY_RATES = {
    "backpacker": 20,
    "mid_range": 45,
    "luxury": 100,
}


def calculate_budget(
    trip_plan: Dict[str, Any],
    user_budget: float,
    travel_style: str,
    duration: int,
) -> Dict[str, Any]:
    """Calculate total trip budget and compare against user's budget."""
    logger.info(
        f"Calculating budget for a {duration}-day, "
        f"{travel_style} trip."
    )

    total_flights = (
        trip_plan.get("flights", {}).get("total_flights_cost", 0.0)
    )
    total_accommodation = (
        trip_plan
        .get("accommodation", {})
        .get("total_accommodation_cost", 0.0)
    )
    total_activities = (
        trip_plan
        .get("activities", {})
        .get("total_activities_cost", 0.0)
    )

    food_rate = FOOD_DAILY_RATES.get(travel_style, 45)
    total_food = food_rate * duration
    logger.debug(
        f"Food: €{food_rate}/day x {duration} days = €{total_food}"
    )

    grand_total = (
        total_flights
        + total_accommodation
        + total_activities
        + total_food
    )

    buffer = user_budget - grand_total
    is_over_budget = grand_total > user_budget

    if is_over_budget:
        logger.warning(
            f"OVER budget by €{-buffer:.2f}. "
            f"Total: €{grand_total:.2f}, "
            f"Budget: €{user_budget:.2f}"
        )
    else:
        logger.info(
            f"UNDER budget by €{buffer:.2f}. "
            f"Total: €{grand_total:.2f}, "
            f"Budget: €{user_budget:.2f}"
        )

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
