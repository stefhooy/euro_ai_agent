import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Mapping of known cities to their respective country for flag emojis
CITY_TO_COUNTRY = {
    "Barcelona": "Spain",
    "Paris": "France",
    "Rome": "Italy",
    "Amsterdam": "Netherlands",
    "Prague": "Czech Republic",
    "Lisbon": "Portugal",
    "Vienna": "Austria",
    "Budapest": "Hungary",
    "Berlin": "Germany",
    "Dubrovnik": "Croatia",
    "Athens": "Greece",
    "Porto": "Portugal"
}

FLAG_EMOJIS = {
    "Spain": "🇪🇸",
    "France": "🇫🇷",
    "Italy": "🇮🇹",
    "Netherlands": "🇳🇱",
    "Czech Republic": "🇨🇿",
    "Portugal": "🇵🇹",
    "Austria": "🇦🇹",
    "Hungary": "🇭🇺",
    "Germany": "🇩🇪",
    "Croatia": "🇭🇷",
    "Greece": "🇬🇷"
}

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
    
    destinations = trip_plan.get("destinations", [])
    cities_str = " → ".join(destinations)
    
    # Build the Overview
    itinerary = [
        "============================================",
        "🌍 YOUR EUROTRIP ITINERARY",
        "============================================",
        "",
        "Trip Overview:",
        f"- Duration: {duration} days",
        f"- Cities: {cities_str}",
        f"- Travel Style: {travel_style}",
        f"- Total Estimated Cost: €{grand_total:,.0f} / €{user_budget:,.0f} budget",
        f"- Remaining Buffer: €{buffer:,.0f}",
        ""
    ]
    
    # Build the City-by-City breakdown
    current_day_global = 1
    
    accommodation_data = trip_plan.get("accommodation", {}).get("city_breakdown", {})
    activities_data = trip_plan.get("activities", {}).get("city_activities", {})
    flight_legs = trip_plan.get("flights", {}).get("flight_legs", [])
    web_data = trip_plan.get("web_data", {})
    
    food_cost_total = budget_result.get("food_cost", 0)
    food_rate = food_cost_total / duration if duration > 0 else 0
    
    for city in destinations:
        country = CITY_TO_COUNTRY.get(city, "")
        flag = FLAG_EMOJIS.get(country, "🏳️")
        
        nights = accommodation_data.get(city, {}).get("nights", 0)
        end_day = current_day_global + nights - 1
        if nights == 0:
            end_day = current_day_global
        
        day_range = f"Day {current_day_global}" if nights <= 1 else f"Days {current_day_global}-{end_day}"
        
        itinerary.extend([
            "--------------------------------------------",
            f"📍 {city} {flag} ({day_range})",
            "--------------------------------------------"
        ])

        # Live Wikipedia description
        city_web = web_data.get(city, {})
        description = city_web.get("description", "")
        if description:
            itinerary.append(f"ℹ️  {description}")

        # Live weather from Open-Meteo
        weather = city_web.get("weather", {})
        if weather.get("avg_high_c") is not None:
            itinerary.append(
                f"🌡️  Weather in this month: {weather['emoji']} {weather['condition']} "
                f"— {weather['avg_low_c']}°C to {weather['avg_high_c']}°C"
            )
        
        accom = accommodation_data.get(city, {})
        if accom:
            area = accom.get('recommended_area', 'City Center')
            nightly = accom.get('nightly_cost', 0)
            tot_accom = accom.get('total_cost', 0)
            itinerary.append(f"Accommodation: {area} — €{nightly:,.0f}/night × {nights} nights = €{tot_accom:,.0f}")
        
        for leg in flight_legs:
            if leg["to"] == city:
                itinerary.append(f"Flights: {leg['from']} → {leg['to']} — €{leg['cost_eur']:,.0f}")
        
        if city == destinations[-1]:
            for leg in flight_legs:
                if leg["from"] == city and leg["type"] == "inbound":
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
                    cost_str = f"€{act['cost_eur']:,.0f}" if act['cost_eur'] > 0 else "free"
                    act_strings.append(f"{act['name']} ({cost_str})")
                itinerary.append(f"  - Day {global_d}: " + " + ".join(act_strings))
        
        food_city_total = food_rate * nights if nights > 0 else food_rate
        itinerary.append(f"\nFood Budget: €{food_rate:,.0f}/day × {max(nights, 1)} days = €{food_city_total:,.0f}")
        
        city_subtotal = (accom.get('total_cost', 0) + 
                         sum(leg['cost_eur'] for leg in flight_legs if leg['to'] == city) + 
                         activities_data.get(city, {}).get("city_total_cost", 0) + 
                         food_city_total)
                         
        if city == destinations[-1]:
             city_subtotal += sum(leg['cost_eur'] for leg in flight_legs if leg['from'] == city and leg["type"] == "inbound")
        
        itinerary.append(f"City Subtotal: €{city_subtotal:,.0f}\n")
        
        current_day_global += max(nights, 1)
        
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
        "============================================"
    ])
    
    return "\n".join(itinerary)