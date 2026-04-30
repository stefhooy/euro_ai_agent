import copy
import logging
from typing import Any, Dict, List

# Import functions from other tools for recalculation
from .accommodation import estimate_accommodation
from .activities import get_activities
from .budget import calculate_budget
from .flights import estimate_flights

logger = logging.getLogger(__name__)


def _recalculate_full_plan(
    trip_plan: Dict[str, Any], preferences: Dict[str, Any]
) -> (Dict[str, Any], Dict[str, Any]):
    """Helper to recalculate all costs based on a modified trip plan."""
    logger.debug("Recalculating full trip plan...")
    destinations = trip_plan["destinations"]
    nights_per_city = trip_plan["nights_per_city"]
    travel_style = trip_plan["travel_style"]

    # Recalculate each component
    trip_plan["flights"] = estimate_flights(
        departure_city=preferences["departure_city"],
        destinations=destinations,
        travel_month=preferences["travel_month"],
        travel_style=travel_style,
    )
    trip_plan["accommodation"] = estimate_accommodation(
        cities=destinations,
        nights_per_city=nights_per_city,
        travel_style=travel_style,
        travel_month=preferences["travel_month"],
    )
    trip_plan["activities"] = get_activities(
        cities=destinations,
        preferences=preferences["activity_preferences"],
        nights_per_city=nights_per_city,
    )

    # Recalculate the final budget
    budget_result = calculate_budget(
        trip_plan=trip_plan,
        user_budget=preferences["budget"],
        travel_style=travel_style,
        duration=preferences["duration"],
    )
    return trip_plan, budget_result


def replan(
    trip_plan: Dict[str, Any],
    budget_result: Dict[str, Any],
    all_scored_cities: List[Dict[str, Any]],
    preferences: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Autonomously adjusts a trip plan to fit within the user's budget.

    Tries a series of cost-saving strategies in a specific order until the plan
    is no longer over budget.

    Args:
        trip_plan (dict): The current, over-budget trip plan.
        budget_result (dict): The result from the budget calculator showing the deficit.
        all_scored_cities (list): The full list of top-scored cities from the destination tool.
        preferences (dict): The original user preferences.

    Returns:
        dict: A dictionary containing the adjusted trip plan, the new budget result,
              and a list of changes made.
    """
    logger.warning(
        f"Trip is over budget by €{-budget_result['buffer']:.2f}. Initiating replanning."
    )
    changes_made = []
    current_plan = copy.deepcopy(trip_plan)
    current_budget_result = budget_result.copy()

    # Strategy 1: Reduce nights in the most expensive city
    if current_budget_result["is_over_budget"]:
        accom_breakdown = current_plan.get("accommodation", {}).get("city_breakdown", {})
        if accom_breakdown:
            city_to_cut = max(accom_breakdown, key=lambda c: accom_breakdown[c]["total_cost"])
            if current_plan["nights_per_city"][city_to_cut] > 1:
                current_plan["nights_per_city"][city_to_cut] -= 1
                change = f"Reduced stay in {city_to_cut} by one night."
                logger.info(f"Replanning (Strategy 1): {change}")
                changes_made.append(change)
                current_plan, current_budget_result = _recalculate_full_plan(current_plan, preferences)
                if not current_budget_result["is_over_budget"]:
                    return {"adjusted_trip_plan": current_plan, "new_budget_result": current_budget_result, "changes_made": changes_made}

    # Strategy 2: Swap the most expensive city
    if current_budget_result["is_over_budget"]:
        accom_breakdown = current_plan.get("accommodation", {}).get("city_breakdown", {})
        if accom_breakdown and len(current_plan["destinations"]) > 1:
            city_to_swap = max(accom_breakdown, key=lambda c: accom_breakdown[c]["nightly_cost"])
            current_dest_names = set(current_plan["destinations"])
            replacement = next((c for c in all_scored_cities if c["name"] not in current_dest_names), None)
            if replacement:
                swap_index = current_plan["destinations"].index(city_to_swap)
                current_plan["destinations"][swap_index] = replacement["name"]
                nights = current_plan["nights_per_city"].pop(city_to_swap)
                current_plan["nights_per_city"][replacement["name"]] = nights
                change = f"Swapped most expensive city, {city_to_swap}, with a more affordable option: {replacement['name']}."
                logger.info(f"Replanning (Strategy 2): {change}")
                changes_made.append(change)
                current_plan, current_budget_result = _recalculate_full_plan(current_plan, preferences)
                if not current_budget_result["is_over_budget"]:
                    return {"adjusted_trip_plan": current_plan, "new_budget_result": current_budget_result, "changes_made": changes_made}

    # Strategy 3: Downgrade accommodation tier
    if current_budget_result["is_over_budget"]:
        style_map = {"luxury": "mid_range", "mid_range": "backpacker"}
        original_style = current_plan["travel_style"]
        if original_style in style_map:
            new_style = style_map[original_style]
            current_plan["travel_style"] = new_style
            change = f"Downgraded travel style from '{original_style}' to '{new_style}'."
            logger.info(f"Replanning (Strategy 3): {change}")
            changes_made.append(change)
            current_plan, current_budget_result = _recalculate_full_plan(current_plan, preferences)
            if not current_budget_result["is_over_budget"]:
                return {"adjusted_trip_plan": current_plan, "new_budget_result": current_budget_result, "changes_made": changes_made}

    # Strategy 4: Remove the most expensive activity from each city
    if current_budget_result["is_over_budget"]:
        change = "Removed the most expensive activity from each city."
        logger.info(f"Replanning (Strategy 4): {change}")
        changes_made.append(change)
        for city, details in current_plan["activities"]["city_activities"].items():
            if details["activities"]:
                expensive_act = max(details["activities"], key=lambda act: act["cost_eur"])
                if expensive_act["cost_eur"] > 0:
                    details["activities"].remove(expensive_act)
        current_plan, current_budget_result = _recalculate_full_plan(current_plan, preferences)

    logger.info("Replanning complete.")
    return {"adjusted_trip_plan": current_plan, "new_budget_result": current_budget_result, "changes_made": changes_made}
