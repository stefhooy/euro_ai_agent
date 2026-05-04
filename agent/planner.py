import calendar
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CITY_TO_COUNTRY = {
    "Barcelona": "Spain",
    "Madrid": "Spain",
    "Seville": "Spain",
    "Valencia": "Spain",
    "Paris": "France",
    "Nice": "France",
    "Lyon": "France",
    "Bordeaux": "France",
    "Strasbourg": "France",
    "Rome": "Italy",
    "Florence": "Italy",
    "Venice": "Italy",
    "Milan": "Italy",
    "Naples": "Italy",
    "Amsterdam": "Netherlands",
    "Rotterdam": "Netherlands",
    "Brussels": "Belgium",
    "Bruges": "Belgium",
    "Ghent": "Belgium",
    "London": "United Kingdom",
    "Edinburgh": "United Kingdom",
    "Manchester": "United Kingdom",
    "Dublin": "Ireland",
    "Luxembourg City": "Luxembourg",
    "Lisbon": "Portugal",
    "Porto": "Portugal",
    "Vienna": "Austria",
    "Salzburg": "Austria",
    "Innsbruck": "Austria",
    "Graz": "Austria",
    "Prague": "Czech Republic",
    "Budapest": "Hungary",
    "Berlin": "Germany",
    "Munich": "Germany",
    "Hamburg": "Germany",
    "Cologne": "Germany",
    "Frankfurt": "Germany",
    "Dresden": "Germany",
    "Nuremberg": "Germany",
    "Copenhagen": "Denmark",
    "Aarhus": "Denmark",
    "Stockholm": "Sweden",
    "Gothenburg": "Sweden",
    "Malmö": "Sweden",
    "Oslo": "Norway",
    "Bergen": "Norway",
    "Tromsø": "Norway",
    "Stavanger": "Norway",
    "Helsinki": "Finland",
    "Tampere": "Finland",
    "Turku": "Finland",
    "Athens": "Greece",
    "Thessaloniki": "Greece",
    "Santorini": "Greece",
    "Dubrovnik": "Croatia",
    "Split": "Croatia",
    "Zagreb": "Croatia",
    "Warsaw": "Poland",
    "Krakow": "Poland",
    "Wroclaw": "Poland",
    "Gdansk": "Poland",
    "Tallinn": "Estonia",
    "Riga": "Latvia",
    "Vilnius": "Lithuania",
    "Bucharest": "Romania",
    "Cluj-Napoca": "Romania",
    "Sofia": "Bulgaria",
    "Plovdiv": "Bulgaria",
    "Belgrade": "Serbia",
    "Sarajevo": "Bosnia and Herzegovina",
    "Tirana": "Albania",
    "Ljubljana": "Slovenia",
    "Bratislava": "Slovakia",
    "Zurich": "Switzerland",
    "Geneva": "Switzerland",
    "Bern": "Switzerland",
    "Basel": "Switzerland",
    "Kotor": "Montenegro",
    "Valletta": "Malta",
    "Reykjavik": "Iceland",
}

FLAG_EMOJIS = {
    "Spain": "🇪🇸",
    "France": "🇫🇷",
    "Italy": "🇮🇹",
    "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪",
    "United Kingdom": "🇬🇧",
    "Ireland": "🇮🇪",
    "Luxembourg": "🇱🇺",
    "Portugal": "🇵🇹",
    "Austria": "🇦🇹",
    "Czech Republic": "🇨🇿",
    "Hungary": "🇭🇺",
    "Germany": "🇩🇪",
    "Denmark": "🇩🇰",
    "Sweden": "🇸🇪",
    "Norway": "🇳🇴",
    "Finland": "🇫🇮",
    "Greece": "🇬🇷",
    "Croatia": "🇭🇷",
    "Poland": "🇵🇱",
    "Estonia": "🇪🇪",
    "Latvia": "🇱🇻",
    "Lithuania": "🇱🇹",
    "Romania": "🇷🇴",
    "Bulgaria": "🇧🇬",
    "Serbia": "🇷🇸",
    "Bosnia and Herzegovina": "🇧🇦",
    "Albania": "🇦🇱",
    "Slovenia": "🇸🇮",
    "Slovakia": "🇸🇰",
    "Switzerland": "🇨🇭",
    "Montenegro": "🇲🇪",
    "Malta": "🇲🇹",
    "Iceland": "🇮🇸",
}


def _format_pricing_calendar(
    pricing_calendar: Dict[str, Any],
) -> List[str]:
    """Format pricing calendar data as a compact text chart."""
    monthly_costs = pricing_calendar.get("monthly_costs", [])
    if not monthly_costs:
        return []

    max_cost = max(
        (item.get("estimated_cost", 0) for item in monthly_costs),
        default=0,
    )
    min_cost = min(
        (item.get("estimated_cost", 0) for item in monthly_costs),
        default=0,
    )
    cheapest = pricing_calendar.get("cheapest_month", {})
    most_expensive = pricing_calendar.get("most_expensive_month", {})
    best_weather = pricing_calendar.get("best_weather_months", [])

    lines = [
        "============================================",
        "PRICING CALENDAR - BEST TIME TO VISIT",
        "============================================",
        "Estimated full-trip cost by month, "
        "using the same route and nights.",
    ]

    for item in monthly_costs:
        cost = item.get("estimated_cost", 0)
        cost_range = max_cost - min_cost
        if cost_range:
            filled = 4 + round(
                ((cost - min_cost) / cost_range) * 16
            )
        else:
            filled = 12
        bar = "#" * filled + "." * (20 - filled)
        month_label = calendar.month_abbr[item.get("month", 1)]
        note = ""
        if item.get("month") == cheapest.get("month"):
            note = " (cheapest)"
        elif item.get("month") == most_expensive.get("month"):
            note = " (most expensive)"
        lines.append(
            f"{month_label:<3}  {bar}  EUR {cost:,.0f}{note}"
        )

    if best_weather:
        lines.extend([
            "============================================",
            f"Best weather months: {', '.join(best_weather)}",
            "============================================",
        ])
    else:
        lines.append("============================================")

    return lines


def _format_transport_leg(leg: Dict[str, Any]) -> str:
    """Format one transport leg with mode, directness, duration, cost."""
    mode = leg.get("mode", "flight").title()
    if leg.get("direct", True):
        direct_label = "direct"
    else:
        direct_label = f"{leg.get('changes', 1)} change(s)"
    duration = leg.get("duration_hours")
    if isinstance(duration, (int, float)):
        duration_label = f", {duration:g}h"
    else:
        duration_label = ""
    return (
        f"{leg['from']} -> {leg['to']} by {mode} "
        f"({direct_label}{duration_label}) "
        f"- EUR {leg['cost_eur']:,.0f}"
    )


def assemble_itinerary(
    trip_plan: Dict[str, Any],
    budget_result: Dict[str, Any],
    preferences: Dict[str, Any],
) -> str:
    """
    Assembles all tool outputs into a beautifully formatted itinerary.

    Args:
        trip_plan (dict): The final dictionary containing destinations,
                          flights, accommodation, and activities details.
        budget_result (dict): The final budget calculation result.
        preferences (dict): The original user preferences.

    Returns:
        str: A formatted itinerary string ready to be displayed.
    """
    logger.info("Assembling the final formatted itinerary.")

    duration = preferences.get("duration", 0)
    travel_style = (
        preferences.get("travel_style", "Unknown")
        .replace("_", "-")
        .title()
    )
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
    route_str = " -> ".join(route_cities)

    itinerary = [
        "============================================",
        "YOUR EUROTRIP ITINERARY",
        "============================================",
        "",
        "Trip Overview:",
        f"- Departure City:    {departure_city}",
        f"- Ending City:       {return_city}",
        f"- Travel Month:      {month_name}",
    ]

    if travel_start_date and travel_end_date:
        itinerary.append(
            f"- Travel Dates:      "
            f"{travel_start_date} to {travel_end_date}"
        )
    else:
        itinerary.append("")

    itinerary.extend([
        f"- Duration:          {duration} days",
        f"- Route:             {route_str}",
        f"- Travel Style:      {travel_style}",
        f"- Total Est. Cost:   "
        f"EUR {grand_total:,.0f} / EUR {user_budget:,.0f} budget",
        f"- Remaining Buffer:  EUR {buffer:,.0f}",
        "",
    ])

    transport_modes = preferences.get(
        "transport_modes", ["flight", "train", "bus"]
    )
    route_priority = preferences.get(
        "route_priority", "best_balance"
    ).replace("_", " ")
    directness = preferences.get(
        "directness", "allow_connections"
    ).replace("_", " ")
    itinerary.extend([
        "How the agent chose this plan:",
        "- Destinations were selected from the highest-scoring cities "
        "for your interests, budget, pace, and travel month.",
        "- Transport compared these modes: "
        f"{', '.join(mode.title() for mode in transport_modes)}.",
        f"- Route preference was set to {route_priority}; "
        f"directness was set to {directness}.",
        "- The selected transport for each leg is an estimate based on "
        "distance, time, price, seasonality, and comfort.",
        "",
        "Important: This is a planning proposal, not a booking "
        "confirmation.",
        "Please verify live transport prices on sites like Skyscanner, "
        "Google Flights, Trainline, Omio, FlixBus, or airline/train/"
        "bus websites.",
        "Please also verify accommodation on Booking.com or similar "
        "sites, and check museum/activity opening times and ticket "
        "prices before booking.",
        "",
    ])

    current_day_global = 1

    accommodation_data = (
        trip_plan.get("accommodation", {}).get("city_breakdown", {})
    )
    activities_data = (
        trip_plan.get("activities", {}).get("city_activities", {})
    )
    flight_legs = (
        trip_plan.get("flights", {}).get("transport_legs")
        or trip_plan.get("flights", {}).get("flight_legs", [])
    )
    web_data = trip_plan.get("web_data", {})

    food_cost_total = budget_result.get("food_cost", 0)
    food_rate = food_cost_total / duration if duration > 0 else 0

    # Show outbound flight before first city
    if flight_legs:
        outbound = next(
            (
                leg for leg in flight_legs
                if leg["type"] == "outbound"
            ),
            None,
        )
        if outbound:
            itinerary.extend([
                "--------------------------------------------",
                f"OUTBOUND: {_format_transport_leg(outbound)}",
                "--------------------------------------------",
                "",
            ])

    for city in destinations:
        country = CITY_TO_COUNTRY.get(city, "")
        flag = FLAG_EMOJIS.get(country, "")

        nights = accommodation_data.get(city, {}).get("nights", 0)
        end_day = current_day_global + nights - 1
        if nights == 0:
            end_day = current_day_global

        if nights <= 1:
            day_range = f"Day {current_day_global}"
        else:
            day_range = f"Days {current_day_global}-{end_day}"

        itinerary.extend([
            "--------------------------------------------",
            f"{city} {flag} ({day_range})",
            "--------------------------------------------",
        ])

        city_web = web_data.get(city, {})
        description = city_web.get("description", "")
        if description:
            itinerary.append(f"  {description}")

        weather = city_web.get("weather", {})
        if weather.get("avg_high_c") is not None:
            itinerary.append(
                f"Weather in {month_name}: "
                f"{weather['emoji']} {weather['condition']} - "
                f"{weather['avg_low_c']}C to "
                f"{weather['avg_high_c']}C"
            )

        accom = accommodation_data.get(city, {})
        if accom:
            area = accom.get("recommended_area", "City Center")
            nightly = accom.get("nightly_cost", 0)
            tot_accom = accom.get("total_cost", 0)
            itinerary.append(
                f"Accommodation: {area} - "
                f"EUR {nightly:,.0f}/night x {nights} nights"
                f" = EUR {tot_accom:,.0f}"
            )

        # Inter-city flights into this city (skip outbound shown above)
        for leg in flight_legs:
            if (
                leg["to"] == city
                and leg["type"] == "inter_city"
            ):
                itinerary.append(
                    f"Transport: {_format_transport_leg(leg)}"
                )

        itinerary.append("\nActivities:")
        city_acts = (
            activities_data.get(city, {}).get("activities", [])
        )

        acts_by_day: Dict[int, list] = {}
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
                    if act["cost_eur"] > 0:
                        cost_str = f"EUR {act['cost_eur']:,.0f}"
                    else:
                        cost_str = "free"
                    act_strings.append(
                        f"{act['name']} ({cost_str})"
                    )
                itinerary.append(
                    f"  - Day {global_d}: "
                    + " + ".join(act_strings)
                )

        food_city_total = (
            food_rate * nights if nights > 0 else food_rate
        )
        itinerary.append(
            f"\nFood Budget: EUR {food_rate:,.0f}/day "
            f"x {max(nights, 1)} days"
            f" = EUR {food_city_total:,.0f}"
        )

        city_subtotal = (
            accom.get("total_cost", 0)
            + sum(
                leg["cost_eur"] for leg in flight_legs
                if leg["to"] == city
                and leg["type"] == "inter_city"
            )
            + activities_data.get(city, {}).get(
                "city_total_cost", 0
            )
            + food_city_total
        )

        itinerary.append(
            f"City Subtotal: EUR {city_subtotal:,.0f}\n"
        )
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
        inbound = next(
            (
                leg for leg in flight_legs
                if leg["type"] == "inbound"
            ),
            None,
        )
        if inbound:
            itinerary.extend([
                "--------------------------------------------",
                f"FINAL LEG: {_format_transport_leg(inbound)}",
                "--------------------------------------------",
                "",
            ])

    f_cost = budget_result.get("flights_cost", 0)
    a_cost = budget_result.get("accommodation_cost", 0)
    ac_cost = budget_result.get("activities_cost", 0)
    fd_cost = budget_result.get("food_cost", 0)

    if budget_result.get("is_over_budget"):
        status_icon = "X"
        status_text = "over budget"
    else:
        status_icon = "OK"
        status_text = "under budget"

    itinerary.extend([
        "============================================",
        "FULL COST BREAKDOWN",
        "============================================",
        f"Transport:        EUR {f_cost:,.0f}",
        f"Accommodation:    EUR {a_cost:,.0f}",
        f"Activities:       EUR {ac_cost:,.0f}",
        f"Food:             EUR {fd_cost:,.0f}",
        "-----------------------------",
        f"TOTAL:            EUR {grand_total:,.0f}",
        f"BUDGET:           EUR {user_budget:,.0f}",
        f"BUFFER:           EUR {abs(buffer):,.0f} "
        f"({status_text} {status_icon})",
        "============================================",
    ])

    pricing_lines = _format_pricing_calendar(
        trip_plan.get("pricing_calendar", {})
    )
    if pricing_lines:
        itinerary.extend([""] + pricing_lines)

    return "\n".join(itinerary)
