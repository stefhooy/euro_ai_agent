import calendar
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

CITY_TO_COUNTRY = {
    "Barcelona": "Spain",       "Madrid": "Spain",         "Seville": "Spain",
    "Paris": "France",          "Nice": "France",
    "Rome": "Italy",            "Florence": "Italy",       "Venice": "Italy",       "Milan": "Italy",
    "Amsterdam": "Netherlands",
    "Brussels": "Belgium",      "Bruges": "Belgium",
    "Lisbon": "Portugal",       "Porto": "Portugal",
    "Vienna": "Austria",        "Salzburg": "Austria",
    "Prague": "Czech Republic",
    "Budapest": "Hungary",
    "Berlin": "Germany",        "Munich": "Germany",       "Hamburg": "Germany",
    "Copenhagen": "Denmark",
    "Stockholm": "Sweden",
    "Oslo": "Norway",
    "Helsinki": "Finland",
    "Athens": "Greece",         "Santorini": "Greece",
    "Dubrovnik": "Croatia",     "Split": "Croatia",
    "Warsaw": "Poland",         "Krakow": "Poland",
    "Tallinn": "Estonia",
    "Riga": "Latvia",
    "Vilnius": "Lithuania",
    "Ljubljana": "Slovenia",
    "Bratislava": "Slovakia",
    "Zurich": "Switzerland",    "Geneva": "Switzerland",
    "Valletta": "Malta",
    "Reykjavik": "Iceland",
}

FLAG_EMOJIS = {
    "Spain": "🇪🇸",       "France": "🇫🇷",       "Italy": "🇮🇹",
    "Netherlands": "🇳🇱", "Belgium": "🇧🇪",      "Portugal": "🇵🇹",
    "Austria": "🇦🇹",     "Czech Republic": "🇨🇿", "Hungary": "🇭🇺",
    "Germany": "🇩🇪",     "Denmark": "🇩🇰",      "Sweden": "🇸🇪",
    "Norway": "🇳🇴",      "Finland": "🇫🇮",      "Greece": "🇬🇷",
    "Croatia": "🇭🇷",     "Poland": "🇵🇱",       "Estonia": "🇪🇪",
    "Latvia": "🇱🇻",      "Lithuania": "🇱🇹",    "Slovenia": "🇸🇮",
    "Slovakia": "🇸🇰",    "Switzerland": "🇨🇭",  "Malta": "🇲🇹",
    "Iceland": "🇮🇸",
}


def _format_pricing_calendar(pricing_calendar: dict) -> list:
    """Format pricing calendar data as a compact text chart."""
    monthly_costs = pricing_calendar.get("monthly_costs", [])
    if not monthly_costs:
        return []

    max_cost = max((item.get("estimated_cost", 0) for item in monthly_costs), default=0)
    cheapest = pricing_calendar.get("cheapest_month", {})
    most_expensive = pricing_calendar.get("most_expensive_month", {})
    best_weather = pricing_calendar.get("best_weather_months", [])

    lines = [
        "============================================",
        "PRICING CALENDAR - BEST TIME TO VISIT",
        "============================================",
    ]

    for item in monthly_costs:
        cost = item.get("estimated_cost", 0)
        filled = round((cost / max_cost) * 20) if max_cost else 0
        bar = "#" * filled + "." * (20 - filled)
        month_label = calendar.month_abbr[item.get("month", 1)]
        note = ""
        if item.get("month") == cheapest.get("month"):
            note = " (cheapest)"
        elif item.get("month") == most_expensive.get("month"):
            note = " (most expensive)"
        lines.append(f"{month_label:<3}  {bar}  â‚¬{cost:,.0f}{note}")

    if best_weather:
        lines.extend([
            "============================================",
            f"Best weather months: {', '.join(best_weather)}",
            "============================================",
        ])
    else:
        lines.append("============================================")

    return lines


def _format_transport_leg(leg: dict) -> str:
    """Format one transport leg with mode, directness, duration, and cost."""
    mode = leg.get("mode", "flight").title()
    direct_label = "direct" if leg.get("direct", True) else f"{leg.get('changes', 1)} change(s)"
    duration = leg.get("duration_hours")
    duration_label = f", {duration:g}h" if isinstance(duration, (int, float)) else ""
    return (
        f"{leg['from']} â†’ {leg['to']} by {mode} "
        f"({direct_label}{duration_label}) â€” â‚¬{leg['cost_eur']:,.0f}"
    )


def assemble_itinerary(trip_plan: Dict[str, Any], budget_result: Dict[str, Any], preferences: Dict[str, Any]) -> str:
    """
    Assembles all tool outputs into a beautifully formatted string itinerary.

    Args:
        trip_plan (dict): The final dictionary containing destinations, flights,
                          accommodation, and activities details.
        budget_result (dict): The final budget calculation result.
        preferences (dict): The original user preferences.

    Returns:
        str: A formatted itinerary string ready to be displayed to the user.
    """
    logger.info("Assembling the final formatted itinerary.")

    duration = preferences.get("duration", 0)
    travel_style = preferences.get("travel_style", "Unknown").replace("_", "-").title()
    grand_total = budget_result.get("grand_total", 0)
    user_budget = budget_result.get("user_budget", 0)
    buffer = budget_result.get("buffer", 0)
    departure_city = preferences.get("departure_city", "Home")
    return_city = preferences.get("return_city", departure_city)
    travel_month = preferences.get("travel_month", 1)
    month_name = calendar.month_name[travel_month]
    travel_start_date = preferences.get("travel_start_date")
    travel_end_date = preferences.get("travel_end_date")

    destinations = trip_plan.get("destinations", [])
    route_cities = [departure_city] + destinations + [return_city]
    route_str = " → ".join(route_cities)

    itinerary = [
        "============================================",
        "🌍 YOUR EUROTRIP ITINERARY",
        "============================================",
        "",
        "Trip Overview:",
        f"- Departure City:    {departure_city}",
        f"- Ending City:       {return_city}",
        f"- Travel Month:      {month_name}",
        f"- Travel Dates:      {travel_start_date} to {travel_end_date}" if travel_start_date and travel_end_date else "",
        f"- Duration:          {duration} days",
        f"- Route:             {route_str}",
        f"- Travel Style:      {travel_style}",
        f"- Total Est. Cost:   €{grand_total:,.0f} / €{user_budget:,.0f} budget",
        f"- Remaining Buffer:  €{buffer:,.0f}",
        "",
    ]

    current_day_global = 1

    accommodation_data = trip_plan.get("accommodation", {}).get("city_breakdown", {})
    activities_data = trip_plan.get("activities", {}).get("city_activities", {})
    flight_legs = trip_plan.get("flights", {}).get("transport_legs") or trip_plan.get("flights", {}).get("flight_legs", [])
    web_data = trip_plan.get("web_data", {})

    food_cost_total = budget_result.get("food_cost", 0)
    food_rate = food_cost_total / duration if duration > 0 else 0

    # Show outbound flight before first city
    if flight_legs:
        outbound = next((leg for leg in flight_legs if leg["type"] == "outbound"), None)
        if outbound:
            itinerary.extend([
                "--------------------------------------------",
                f"✈️  OUTBOUND: {outbound['from']} → {outbound['to']} — €{outbound['cost_eur']:,.0f}",
                "--------------------------------------------",
                "",
            ])

    for city in destinations:
        country = CITY_TO_COUNTRY.get(city, "")
        flag = FLAG_EMOJIS.get(country, "🏳️")

        nights = accommodation_data.get(city, {}).get("nights", 0)
        end_day = current_day_global + nights - 1
        if nights == 0:
            end_day = current_day_global

        day_range = (f"Day {current_day_global}"
                     if nights <= 1
                     else f"Days {current_day_global}-{end_day}")

        itinerary.extend([
            "--------------------------------------------",
            f"📍 {city} {flag} ({day_range})",
            "--------------------------------------------",
        ])

        city_web = web_data.get(city, {})
        description = city_web.get("description", "")
        if description:
            itinerary.append(f"ℹ️  {description}")

        weather = city_web.get("weather", {})
        if weather.get("avg_high_c") is not None:
            itinerary.append(
                f"🌡️  Weather in {month_name}: {weather['emoji']} {weather['condition']} "
                f"— {weather['avg_low_c']}°C to {weather['avg_high_c']}°C"
            )

        accom = accommodation_data.get(city, {})
        if accom:
            area = accom.get("recommended_area", "City Center")
            nightly = accom.get("nightly_cost", 0)
            tot_accom = accom.get("total_cost", 0)
            itinerary.append(
                f"Accommodation: {area} — €{nightly:,.0f}/night × {nights} nights = €{tot_accom:,.0f}"
            )

        # Inter-city flights into this city (skip outbound — shown above)
        for leg in flight_legs:
            if leg["to"] == city and leg["type"] == "inter_city":
                itinerary.append(f"Flights: {leg['from']} → {leg['to']} — €{leg['cost_eur']:,.0f}")

        itinerary.append("\nActivities:")
        city_acts = activities_data.get(city, {}).get("activities", [])

        acts_by_day = {}
        for act in city_acts:
            d = act.get("day", 1)
            acts_by_day.setdefault(d, []).append(act)

        if not acts_by_day:
            itinerary.append("  - Free time to explore!")
        else:
            for d in sorted(acts_by_day.keys()):
                global_d = current_day_global + d - 1
                daily_acts = acts_by_day[d]
                act_strings = []
                for act in daily_acts:
                    cost_str = f"€{act['cost_eur']:,.0f}" if act["cost_eur"] > 0 else "free"
                    act_strings.append(f"{act['name']} ({cost_str})")
                itinerary.append(f"  - Day {global_d}: " + " + ".join(act_strings))

        food_city_total = food_rate * nights if nights > 0 else food_rate
        itinerary.append(f"\nFood Budget: €{food_rate:,.0f}/day × {max(nights, 1)} days = €{food_city_total:,.0f}")

        city_subtotal = (accom.get("total_cost", 0)
                         + sum(leg["cost_eur"] for leg in flight_legs
                               if leg["to"] == city and leg["type"] == "inter_city")
                         + activities_data.get(city, {}).get("city_total_cost", 0)
                         + food_city_total)

        itinerary.append(f"City Subtotal: €{city_subtotal:,.0f}\n")
        current_day_global += max(nights, 1)

    if flight_legs:
        itinerary.extend([
            "--------------------------------------------",
            "TRANSPORT SUMMARY",
            "--------------------------------------------",
        ])
        for leg in flight_legs:
            itinerary.append(f"- {_format_transport_leg(leg)}")
        itinerary.append("")

    # Show return flight after the last city
    if flight_legs:
        inbound = next((leg for leg in flight_legs if leg["type"] == "inbound"), None)
        if inbound:
            itinerary.extend([
                "--------------------------------------------",
                f"✈️  RETURN: {inbound['from']} → {inbound['to']} — €{inbound['cost_eur']:,.0f}",
                "--------------------------------------------",
                "",
            ])

    f_cost = budget_result.get("flights_cost", 0)
    a_cost = budget_result.get("accommodation_cost", 0)
    ac_cost = budget_result.get("activities_cost", 0)
    fd_cost = budget_result.get("food_cost", 0)

    status_icon = "❌" if budget_result.get("is_over_budget") else "✅"
    status_text = "over budget" if budget_result.get("is_over_budget") else "under budget"

    itinerary.extend([
        "============================================",
        "💶 FULL COST BREAKDOWN",
        "============================================",
        f"Flights:          €{f_cost:,.0f}",
        f"Accommodation:    €{a_cost:,.0f}",
        f"Activities:       €{ac_cost:,.0f}",
        f"Food:             €{fd_cost:,.0f}",
        "-----------------------------",
        f"TOTAL:            €{grand_total:,.0f}",
        f"BUDGET:           €{user_budget:,.0f}",
        f"BUFFER:           €{abs(buffer):,.0f} ({status_text} {status_icon})",
        "============================================",
    ])

    pricing_lines = _format_pricing_calendar(trip_plan.get("pricing_calendar", {}))
    if pricing_lines:
        itinerary.extend([""] + pricing_lines)

    return "\n".join(itinerary)
