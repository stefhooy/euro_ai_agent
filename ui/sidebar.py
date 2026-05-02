from datetime import date, timedelta
from typing import Callable, Tuple

import streamlit as st

from ui.config import (
    ACTIVITY_MAP,
    COUNTRY_COUNT_MAP,
    DIRECTNESS_MAP,
    MIN_DAILY,
    MIN_TRANSPORT,
    PACE_MAP,
    ROUTE_PRIORITY_MAP,
    STYLE_MAP,
    TRANSPORT_MODE_MAP,
)


def render_sidebar(reset_callback: Callable) -> Tuple[bool, dict]:
    """Render sidebar; return (plan_button_clicked, preferences)."""
    with st.sidebar:
        st.markdown(
            "<h2 style='font-family:Playfair Display,serif;"
            "color:#5eead4;margin-bottom:0;'>"
            "🪽 Hermes</h2>",
            unsafe_allow_html=True,
        )
        st.caption("AI-powered European travel planner")
        st.markdown("---")

        budget_input = st.number_input(
            "Total Budget (€)",
            min_value=500,
            max_value=20_000,
            value=2500,
            step=100,
        )
        duration_input = st.slider(
            "Trip Duration (days)", min_value=3, max_value=30, value=10
        )
        departure_input = st.text_input("Departure City", value="London")
        return_input = st.text_input(
            "Return / Ending City", value=departure_input
        )
        style_input = st.selectbox(
            "Travel Style", options=list(STYLE_MAP.keys()), index=1
        )

        # Real-time budget feasibility check
        _style_key = STYLE_MAP[style_input]
        _min = (
            MIN_DAILY[_style_key] * duration_input
            + MIN_TRANSPORT[_style_key]
        )
        if budget_input < _min * 0.55:
            st.error(
                f"⛔ Budget too low — a {duration_input}-day "
                f"**{style_input.lower()}** trip typically costs "
                f"at least **€{_min:,.0f}**. Increase your budget "
                "or switch to a cheaper travel style."
            )
        elif budget_input < _min * 0.80:
            st.warning(
                f"⚠️ Tight budget — a {duration_input}-day "
                f"**{style_input.lower()}** trip usually needs "
                f"around **€{_min:,.0f}**. Hermes will try to "
                "replan, but options will be limited."
            )

        travel_start_input = st.date_input(
            "Travel Start Date",
            value=st.session_state.travel_start_date,
            min_value=date.today(),
        )
        travel_end_date = travel_start_input + timedelta(
            days=int(duration_input)
        )
        st.session_state.travel_start_date = travel_start_input
        end_str = travel_end_date.strftime("%d %b %Y")
        st.caption(f"Trip ends: **{end_str}**")

        st.markdown("---")
        num_countries_display = st.select_slider(
            "Countries to visit",
            options=["1", "2", "3", "4", "5", "6"],
            value="2",
        )
        num_countries_raw = COUNTRY_COUNT_MAP[num_countries_display]
        max_realistic = min(6, max(1, duration_input // 3))
        if num_countries_raw > max_realistic:
            st.warning(
                f"⚠️ {num_countries_display} countries in "
                f"{duration_input} days is less than 3 days per "
                f"country — very rushed. Capping at "
                f"**{max_realistic}** for a realistic trip."
            )
            num_countries_final = max_realistic
        else:
            num_countries_final = num_countries_raw

        st.markdown("---")
        activities_input = st.multiselect(
            "Activity Preferences",
            options=list(ACTIVITY_MAP.keys()),
            default=[
                "History & Architecture",
                "Food & Gastronomy",
                "Museums",
            ],
        )
        pace_input = st.selectbox(
            "Pace", options=list(PACE_MAP.keys()), index=1
        )
        transport_modes_input = st.multiselect(
            "Transport Options",
            options=list(TRANSPORT_MODE_MAP.keys()),
            default=["Flight", "Train", "Bus"],
        )
        route_priority_input = st.selectbox(
            "Route Preference",
            options=list(ROUTE_PRIORITY_MAP.keys()),
            index=0,
        )
        directness_input = st.selectbox(
            "Directness",
            options=list(DIRECTNESS_MAP.keys()),
            index=0,
        )

        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            plan_button = st.button(
                "Plan My Trip",
                use_container_width=True,
                type="primary",
            )
        with col2:
            st.button(
                "Reset",
                on_click=reset_callback,
                use_container_width=True,
            )
        st.caption(
            "Estimates only. Always verify prices on "
            "Skyscanner, Booking.com, or Airbnb."
        )

    preferences = {
        "budget": float(budget_input),
        "duration": int(duration_input),
        "departure_city": departure_input.strip(),
        "return_city": (
            return_input.strip() or departure_input.strip()
        ),
        "travel_style": STYLE_MAP[style_input],
        "activity_preferences": [
            ACTIVITY_MAP[a] for a in activities_input
        ],
        "pace": PACE_MAP[pace_input],
        "travel_month": travel_start_input.month,
        "travel_start_date": travel_start_input.isoformat(),
        "travel_end_date": travel_end_date.isoformat(),
        "transport_modes": [
            TRANSPORT_MODE_MAP[m] for m in transport_modes_input
        ],
        "route_priority": ROUTE_PRIORITY_MAP[route_priority_input],
        "directness": DIRECTNESS_MAP[directness_input],
        "trip_type": "international",
        "num_countries": num_countries_final,
        "_activities_input": activities_input,
        "_transport_modes_input": transport_modes_input,
    }
    return plan_button, preferences
