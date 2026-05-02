import calendar as _cal

import streamlit as st


def render_agent_thinking(trip_plan: dict, budget_result: dict, preferences: dict) -> None:
    """Structured breakdown of every decision the agent made."""
    destinations = trip_plan.get("destinations", [])
    nights_per_city = trip_plan.get("nights_per_city", {})
    dest_scores = trip_plan.get("destination_scores", {})
    flight_legs = (
        trip_plan.get("flights", {}).get("transport_legs")
        or trip_plan.get("flights", {}).get("flight_legs", [])
    )
    accom_data = trip_plan.get("accommodation", {}).get("city_breakdown", {})

    pace = preferences.get("pace", "moderate")
    num_countries = preferences.get("num_countries", 2)
    travel_month = preferences.get("travel_month", 6)
    style = preferences.get("travel_style", "mid_range").replace("_", "-").title()
    dep = preferences.get("departure_city", "?")
    ret = preferences.get("return_city", dep)
    activity_prefs = preferences.get("activity_preferences", [])
    transport_modes = preferences.get("transport_modes", [])
    route_priority = preferences.get("route_priority", "best_balance").replace("_", " ")
    directness = preferences.get("directness", "allow_connections").replace("_", " ")
    duration = preferences.get("duration", 0)
    month_name = _cal.month_name[travel_month]

    # ── 1. Planning decisions ──────────────────────────────────────────────────
    st.markdown("#### 📋 Planning decisions")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Departure", dep)
    d2.metric("Return", ret)
    d3.metric("Duration", f"{duration} days")
    d4.metric("Travel month", month_name)

    d5, d6, d7, d8 = st.columns(4)
    d5.metric("Travel style", style)
    d6.metric("Pace", pace.title())
    d7.metric("Countries", str(num_countries))
    d8.metric("Cities chosen", str(len(destinations)))

    st.caption(
        f"Transport considered: **{', '.join(m.title() for m in transport_modes)}** · "
        f"Route priority: **{route_priority}** · Directness: **{directness}**"
    )

    # ── 2. Why these cities? ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🏙️ Why these cities?")
    st.caption(
        "Cities are scored 0-100 across three criteria: "
        "activity match (40 pts), budget fit (40 pts), and season (20 pts)."
    )

    for city in destinations:
        score_data = dest_scores.get(city, {})
        score = score_data.get("score", 0)
        reasons = score_data.get("reasons", [])
        city_tags = score_data.get("activity_tags", [])
        matched = [t for t in city_tags if t in activity_prefs]
        nights = nights_per_city.get(city, 0)
        country = score_data.get("country", "")

        with st.container():
            ca, cb = st.columns([3, 1])
            with ca:
                st.markdown(
                    f"**{city}**"
                    + (f", {country}" if country else "")
                    + f" - {nights} night{'s' if nights != 1 else ''}"
                )
                st.progress(int(score), text=f"Score: {score}/100")
                for r in reasons:
                    st.markdown(f"  - {r}")
                if matched:
                    st.caption(f"Matched your interests: {', '.join(matched)}")
                elif city_tags:
                    st.caption(f"Activities available: {', '.join(city_tags[:4])}")
            with cb:
                accom = accom_data.get(city, {})
                if accom:
                    st.metric("Hotel / night", f"€{accom.get('nightly_cost', 0):,.0f}")
                    st.caption(accom.get("recommended_area", ""))

    # ── 3. Transport decisions ─────────────────────────────────────────────────
    if flight_legs:
        st.markdown("---")
        st.markdown("#### ✈️ Transport decisions")
        st.caption(
            "Each leg compares all available modes (flight, train, bus) on "
            "cost, duration, and your route preference, then picks the best fit."
        )
        for leg in flight_legs:
            mode = leg.get("mode", "flight").title()
            direct_label = (
                "direct" if leg.get("direct", True) else f"{leg.get('changes', 1)} change(s)"
            )
            dist = leg.get("distance_km")
            dist_label = f" · {dist:,} km" if dist else ""
            dur = leg.get("duration_hours")
            dur_label = f" · {dur:g}h" if isinstance(dur, (int, float)) else ""
            leg_type = leg.get("type", "").replace("_", " ").title()
            alts = leg.get("alternatives", [])

            with st.container():
                lc1, lc2 = st.columns([3, 1])
                with lc1:
                    st.markdown(
                        f"**{leg['from']} → {leg['to']}** "
                        f"<span style='color:#94a3b8;font-size:0.85rem;'>"
                        f"{leg_type}{dist_label}{dur_label}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"Chosen: **{mode}** ({direct_label})")
                    if alts:
                        alt_parts = [
                            f"{a['mode'].title()} €{a['cost_eur']:,.0f} / {a['duration_hours']:g}h"
                            for a in alts
                        ]
                        st.caption("Alternatives considered: " + " · ".join(alt_parts))
                with lc2:
                    st.metric("Cost", f"€{leg.get('cost_eur', 0):,.0f}")

    # ── 4. Budget allocation ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💶 Budget allocation")

    grand = budget_result.get("grand_total", 1) or 1
    user_budget = budget_result.get("user_budget", 0)
    categories = [
        ("✈️ Transport",     budget_result.get("flights_cost", 0)),
        ("🏨 Accommodation", budget_result.get("accommodation_cost", 0)),
        ("🎭 Activities",    budget_result.get("activities_cost", 0)),
        ("🍽️ Food",          budget_result.get("food_cost", 0)),
    ]
    for label, cost in categories:
        pct = cost / grand * 100
        pct_of_budget = cost / user_budget * 100 if user_budget else 0
        st.markdown(
            f"**{label}** - €{cost:,.0f} "
            f"<span style='color:#94a3b8;font-size:0.85rem;'>"
            f"({pct:.0f}% of total · {pct_of_budget:.0f}% of your budget)</span>",
            unsafe_allow_html=True,
        )
        st.progress(min(int(pct), 100))
