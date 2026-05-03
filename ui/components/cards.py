from typing import Any, Dict

import streamlit as st

from agent.planner import CITY_TO_COUNTRY, FLAG_EMOJIS


def render_trip_cards(
    trip_plan: Dict[str, Any],
    budget_result: Dict[str, Any],
    preferences: Dict[str, Any],
) -> None:
    """Render the itinerary as structured city cards."""
    destinations = trip_plan.get("destinations", [])
    accommodation_data = (
        trip_plan.get("accommodation", {}).get("city_breakdown", {})
    )
    activities_data = (
        trip_plan.get("activities", {}).get("city_activities", {})
    )
    flight_legs = trip_plan.get("flights", {}).get("flight_legs", [])
    web_data = trip_plan.get("web_data", {})
    nights_per_city = trip_plan.get("nights_per_city", {})

    duration = preferences.get("duration", 1)
    food_total = budget_result.get("food_cost", 0)
    food_rate = food_total / duration if duration > 0 else 0
    departure_city = preferences.get("departure_city", "Home")
    return_city = preferences.get("return_city", departure_city)

    outbound = next(
        (l for l in flight_legs if l.get("type") == "outbound"),
        None,
    )
    if outbound:
        mode = outbound.get("mode", "flight").title()
        st.info(
            f"✈️ **Outbound:** "
            f"{outbound['from']} → {outbound['to']} "
            f"by {mode} - €{outbound['cost_eur']:,.0f}"
        )

    current_day = 1

    for city in destinations:
        nights = nights_per_city.get(city, 0)
        country = CITY_TO_COUNTRY.get(city, "")
        flag = FLAG_EMOJIS.get(country, "\U0001f3f3️")
        end_day = current_day + nights - 1
        if nights <= 1:
            day_range = f"Day {current_day}"
        else:
            day_range = f"Days {current_day}-{end_day}"

        city_web = web_data.get(city, {})
        image_url = city_web.get("image_url", "")
        description = city_web.get("description", "")
        weather = city_web.get("weather", {})
        accom = accommodation_data.get(city, {})
        city_acts_data = activities_data.get(city, {})
        city_acts = city_acts_data.get("activities", [])
        city_act_cost = city_acts_data.get("city_total_cost", 0)
        food_city = food_rate * max(nights, 1)

        inter_leg = next(
            (
                l for l in flight_legs
                if l["to"] == city
                and l.get("type") == "inter_city"
            ),
            None,
        )

        with st.container(border=True):
            if inter_leg:
                mode = inter_leg.get("mode", "flight").title()
                st.caption(
                    f"\U0001f500 {inter_leg['from']} → "
                    f"{inter_leg['to']} "
                    f"by {mode} - €{inter_leg['cost_eur']:,.0f}"
                )

            if image_url:
                img_col, info_col = st.columns([1, 2])
            else:
                img_col, info_col = None, st.columns([1])[0]

            if image_url and img_col is not None:
                with img_col:
                    st.image(image_url, use_container_width=True)

            with info_col:
                st.markdown(
                    f"### \U0001f4cd {city} {flag} "
                    "<span style='"
                    "font-size:0.85rem;"
                    "color:#94a3b8;"
                    "font-family:Inter,sans-serif;'>"
                    f"{day_range}</span>",
                    unsafe_allow_html=True,
                )
                if description:
                    st.caption(description)
                if weather.get("avg_high_c") is not None:
                    st.write(
                        f"{weather['emoji']} "
                        f"**{weather['condition']}** "
                        f"- {weather['avg_low_c']}°C"
                        f" to {weather['avg_high_c']}°C"
                    )

            m1, m2, m3, m4 = st.columns(4)
            hotel_total = accom.get("total_cost", 0)
            nightly = accom.get("nightly_cost", 0)
            area = accom.get("recommended_area", "City Centre")
            city_subtotal = hotel_total + city_act_cost + food_city
            m1.metric(
                "\U0001f3e8 Hotel",
                f"€{hotel_total:,.0f}",
                f"€{nightly:,.0f}/night · {area}",
            )
            m2.metric(
                "\U0001f3ad Activities",
                f"€{city_act_cost:,.0f}",
            )
            m3.metric(
                "\U0001f37d️ Food",
                f"€{food_city:,.0f}",
                f"€{food_rate:,.0f}/day",
            )
            m4.metric(
                "\U0001f4cd City Total",
                f"€{city_subtotal:,.0f}",
            )

            if city_acts:
                acts_by_day: Dict[int, list] = {}
                for act in city_acts:
                    acts_by_day.setdefault(
                        act.get("day", 1), []
                    ).append(act)

                st.markdown("**Activities:**")
                for d in sorted(acts_by_day.keys()):
                    global_d = current_day + d - 1
                    parts = []
                    for act in acts_by_day[d]:
                        if act["cost_eur"] > 0:
                            cost_str = (
                                f"€{act['cost_eur']:,.0f}"
                            )
                        else:
                            cost_str = "free"
                        parts.append(
                            f"{act['name']} ({cost_str})"
                        )
                    st.write(
                        f"**Day {global_d}:** "
                        + " · ".join(parts)
                    )

        current_day += max(nights, 1)

    inbound = next(
        (l for l in flight_legs if l.get("type") == "inbound"),
        None,
    )
    if inbound:
        mode = inbound.get("mode", "flight").title()
        st.info(
            f"✈️ **Return:** "
            f"{inbound['from']} → {return_city} "
            f"by {mode} - €{inbound['cost_eur']:,.0f}"
        )
