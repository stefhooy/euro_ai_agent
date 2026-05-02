import importlib
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

import agent.core as _agent_core
import agent.planner as _agent_planner
importlib.reload(_agent_core)
importlib.reload(_agent_planner)

from agent.core import run_agent
from agent.planner import CITY_TO_COUNTRY, FLAG_EMOJIS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EuroTrip Agent",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap');

.stApp {
    background: linear-gradient(150deg, #0b1437 0%, #0f2255 45%, #0c2f52 75%, #091e3a 100%);
    background-attachment: fixed;
}
html, body, [data-testid="stAppViewContainer"], .stMarkdown p, div {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Playfair Display', Georgia, serif !important;
}
section[data-testid="stSidebar"] {
    background: rgba(8, 16, 50, 0.96) !important;
    border-right: 1px solid rgba(96, 165, 250, 0.18);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    border: none; border-radius: 8px;
    font-weight: 600; letter-spacing: 0.04em;
    box-shadow: 0 0 18px rgba(37,99,235,0.40);
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 24px rgba(37,99,235,0.55);
}
.stButton > button[kind="secondary"] { border-radius: 8px; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(6px);
}
</style>
""", unsafe_allow_html=True)

# ── Option maps ───────────────────────────────────────────────────────────────
STYLE_MAP = {"Backpacker": "backpacker", "Mid-range": "mid_range", "Luxury": "luxury"}
ACTIVITY_MAP = {
    "Museums": "museums", "Nightlife": "nightlife", "Nature": "nature",
    "Food & Gastronomy": "food", "History & Architecture": "history",
    "Shopping": "shopping", "Adventure Sports": "adventure",
}
PACE_MAP = {
    "Slow — fewer cities, more depth": "slow",
    "Moderate": "moderate",
    "Fast — more cities, less time each": "fast",
}
TRANSPORT_MODE_MAP = {"Flight": "flight", "Train": "train", "Bus": "bus"}
ROUTE_PRIORITY_MAP = {"Best balance": "best_balance", "Cheapest": "cheapest", "Fastest": "fastest"}
DIRECTNESS_MAP = {"Allow connections": "allow_connections", "Direct only": "direct_only"}
COUNTRY_COUNT_MAP = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6}

# Minimum all-in daily cost (accommodation + food + activities) and flat transport
# used to warn users when their budget is unrealistic for the chosen travel style.
MIN_DAILY = {"backpacker": 55, "mid_range": 130, "luxury": 320}
MIN_TRANSPORT = {"backpacker": 200, "mid_range": 450, "luxury": 950}

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("itinerary", None), ("budget_result", None), ("preferences", None),
    ("trip_plan", None),
    ("travel_start_date", date.today()),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def reset_app():
    for key in ("itinerary", "budget_result", "preferences", "trip_plan"):
        st.session_state[key] = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='font-family:Playfair Display,serif;color:#93c5fd;margin-bottom:0;'>"
        "🌍 EuroTrip Agent</h2>",
        unsafe_allow_html=True,
    )
    st.caption("AI-powered European travel planner")
    st.markdown("---")

    budget_input = st.number_input("Total Budget (€)", min_value=500, max_value=20_000, value=2500, step=100)
    duration_input = st.slider("Trip Duration (days)", min_value=3, max_value=30, value=10)
    departure_input = st.text_input("Departure City", value="London")
    return_input = st.text_input("Return / Ending City", value=departure_input)
    style_input = st.selectbox("Travel Style", options=list(STYLE_MAP.keys()), index=1)

    # ── Real-time budget feasibility check ────────────────────────────────
    _style_key = STYLE_MAP[style_input]
    _min_budget = MIN_DAILY[_style_key] * duration_input + MIN_TRANSPORT[_style_key]
    if budget_input < _min_budget * 0.55:
        st.error(
            f"⛔ Budget too low — a {duration_input}-day **{style_input.lower()}** trip "
            f"typically costs at least **€{_min_budget:,.0f}**. "
            f"Either increase your budget or switch to a cheaper travel style."
        )
    elif budget_input < _min_budget * 0.80:
        st.warning(
            f"⚠️ Tight budget — a {duration_input}-day **{style_input.lower()}** trip "
            f"usually needs around **€{_min_budget:,.0f}**. "
            f"The agent will try to replan, but options will be limited."
        )

    travel_start_input = st.date_input(
        "Travel Start Date",
        value=st.session_state.travel_start_date,
        min_value=date.today(),
    )
    travel_end_date = travel_start_input + timedelta(days=int(duration_input))
    st.session_state.travel_start_date = travel_start_input
    st.caption(f"Trip ends: **{travel_end_date.strftime('%d %b %Y')}**")

    st.markdown("---")
    num_countries_display = st.select_slider(
        "Countries to visit",
        options=["1", "2", "3", "4", "5", "6"],
        value="2",
    )
    num_countries_raw = COUNTRY_COUNT_MAP[num_countries_display]
    # Realism guard: need at least 3 days per country to see anything meaningful.
    # Maximum is capped at 6 regardless of duration.
    max_realistic = min(6, max(1, duration_input // 3))
    if num_countries_raw > max_realistic:
        st.warning(
            f"⚠️ {num_countries_display} countries in {duration_input} days "
            f"is less than 3 days per country — very rushed. "
            f"Capping at **{max_realistic}** for a realistic trip."
        )
        num_countries_final = max_realistic
    else:
        num_countries_final = num_countries_raw
    trip_type_final = "international"

    st.markdown("---")
    activities_input = st.multiselect(
        "Activity Preferences",
        options=list(ACTIVITY_MAP.keys()),
        default=["History & Architecture", "Food & Gastronomy", "Museums"],
    )
    pace_input = st.selectbox("Pace", options=list(PACE_MAP.keys()), index=1)
    transport_modes_input = st.multiselect(
        "Transport Options",
        options=list(TRANSPORT_MODE_MAP.keys()),
        default=["Flight", "Train", "Bus"],
    )
    route_priority_input = st.selectbox("Route Preference", options=list(ROUTE_PRIORITY_MAP.keys()), index=0)
    directness_input = st.selectbox("Directness", options=list(DIRECTNESS_MAP.keys()), index=0)

    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        plan_button = st.button("Plan My Trip", use_container_width=True, type="primary")
    with col2:
        st.button("Reset", on_click=reset_app, use_container_width=True)
    st.caption("Estimates only. Always verify prices on Skyscanner, Booking.com, or Airbnb before booking.")

# ── Plan button ───────────────────────────────────────────────────────────────
if plan_button:
    if not activities_input:
        st.warning("Please select at least one activity preference.")
    elif not transport_modes_input:
        st.warning("Please select at least one transport option.")
    else:
        preferences = {
            "budget": float(budget_input),
            "duration": int(duration_input),
            "departure_city": departure_input.strip(),
            "return_city": return_input.strip() or departure_input.strip(),
            "travel_style": STYLE_MAP[style_input],
            "activity_preferences": [ACTIVITY_MAP[a] for a in activities_input],
            "pace": PACE_MAP[pace_input],
            "travel_month": travel_start_input.month,
            "travel_start_date": travel_start_input.isoformat(),
            "travel_end_date": travel_end_date.isoformat(),
            "transport_modes": [TRANSPORT_MODE_MAP[m] for m in transport_modes_input],
            "route_priority": ROUTE_PRIORITY_MAP[route_priority_input],
            "directness": DIRECTNESS_MAP[directness_input],
            "trip_type": trip_type_final,
            "num_countries": num_countries_final,
        }

        progress_box = st.empty()

        def update_progress(msg: str):
            progress_box.info(msg)

        try:
            itinerary, budget_result, trip_plan = run_agent(
                preferences, progress_callback=update_progress
            )
            progress_box.empty()
            st.session_state.itinerary = itinerary
            st.session_state.budget_result = budget_result
            st.session_state.preferences = preferences
            st.session_state.trip_plan = trip_plan
        except Exception as e:
            progress_box.empty()
            st.error(f"An error occurred while planning the trip: {e}")
            st.code(traceback.format_exc(), language="python")


# ── Agent thinking display ────────────────────────────────────────────────────
def _render_agent_thinking(trip_plan: dict, budget_result: dict, preferences: dict):
    """Structured breakdown of every decision the agent made."""
    import calendar as _cal

    destinations = trip_plan.get("destinations", [])
    nights_per_city = trip_plan.get("nights_per_city", {})
    dest_scores = trip_plan.get("destination_scores", {})
    flight_legs = trip_plan.get("flights", {}).get("transport_legs") or \
                  trip_plan.get("flights", {}).get("flight_legs", [])
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

    # ── 1. Planning decisions ──────────────────────────────────────────────
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

    # ── 2. Why these cities? ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🏙️ Why these cities?")
    st.caption(
        "Cities are scored 0–100 across three criteria: "
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
                    + f" — {nights} night{'s' if nights != 1 else ''}"
                )
                st.progress(int(score), text=f"Score: {score}/100")
                if reasons:
                    for r in reasons:
                        st.markdown(f"  - {r}")
                if matched:
                    st.caption(
                        f"✅ Matched your interests: {', '.join(matched)}"
                    )
                elif city_tags:
                    st.caption(
                        f"Activities available: {', '.join(city_tags[:4])}"
                    )
            with cb:
                accom = accom_data.get(city, {})
                if accom:
                    st.metric(
                        "Hotel / night",
                        f"€{accom.get('nightly_cost', 0):,.0f}",
                    )
                    st.caption(accom.get("recommended_area", ""))

    # ── 3. Transport decisions ─────────────────────────────────────────────
    if flight_legs:
        st.markdown("---")
        st.markdown("#### ✈️ Transport decisions")
        st.caption(
            "Each leg compares all available modes (flight, train, bus) on "
            "cost, duration, and your route preference, then picks the best fit."
        )
        for leg in flight_legs:
            mode = leg.get("mode", "flight").title()
            direct_label = "direct" if leg.get("direct", True) \
                           else f"{leg.get('changes', 1)} change(s)"
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
                    st.markdown(
                        f"Chosen: **{mode}** ({direct_label})"
                    )
                    if alts:
                        alt_parts = []
                        for a in alts:
                            alt_parts.append(
                                f"{a['mode'].title()} €{a['cost_eur']:,.0f}"
                                f" / {a['duration_hours']:g}h"
                            )
                        st.caption("Alternatives considered: " + " · ".join(alt_parts))
                with lc2:
                    st.metric("Cost", f"€{leg.get('cost_eur', 0):,.0f}")

    # ── 4. Budget allocation ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 💶 Budget allocation")

    grand = budget_result.get("grand_total", 1) or 1
    user_budget = budget_result.get("user_budget", 0)
    categories = [
        ("✈️ Transport",      budget_result.get("flights_cost", 0)),
        ("🏨 Accommodation",  budget_result.get("accommodation_cost", 0)),
        ("🎭 Activities",     budget_result.get("activities_cost", 0)),
        ("🍽️ Food",           budget_result.get("food_cost", 0)),
    ]
    for label, cost in categories:
        pct = cost / grand * 100
        pct_of_budget = cost / user_budget * 100 if user_budget else 0
        st.markdown(
            f"**{label}** — €{cost:,.0f} "
            f"<span style='color:#94a3b8;font-size:0.85rem;'>"
            f"({pct:.0f}% of total · {pct_of_budget:.0f}% of your budget)</span>",
            unsafe_allow_html=True,
        )
        st.progress(min(int(pct), 100))


# ── Rich results UI ───────────────────────────────────────────────────────────
def render_trip_cards(trip_plan: dict, budget_result: dict, preferences: dict):
    """Render the itinerary as structured Streamlit cards instead of plain text."""
    destinations = trip_plan.get("destinations", [])
    accommodation_data = trip_plan.get("accommodation", {}).get("city_breakdown", {})
    activities_data = trip_plan.get("activities", {}).get("city_activities", {})
    flight_legs = trip_plan.get("flights", {}).get("flight_legs", [])
    web_data = trip_plan.get("web_data", {})
    nights_per_city = trip_plan.get("nights_per_city", {})

    duration = preferences.get("duration", 1)
    food_total = budget_result.get("food_cost", 0)
    food_rate = food_total / duration if duration > 0 else 0
    departure_city = preferences.get("departure_city", "Home")
    return_city = preferences.get("return_city", departure_city)

    # ── Outbound flight banner ─────────────────────────────────────────────
    outbound = next((l for l in flight_legs if l.get("type") == "outbound"), None)
    if outbound:
        mode = outbound.get("mode", "flight").title()
        st.info(
            f"✈️ **Outbound:** {outbound['from']} → {outbound['to']} "
            f"by {mode} — €{outbound['cost_eur']:,.0f}"
        )

    current_day = 1

    for city in destinations:
        nights = nights_per_city.get(city, 0)
        country = CITY_TO_COUNTRY.get(city, "")
        flag = FLAG_EMOJIS.get(country, "🏳️")
        end_day = current_day + nights - 1
        day_range = f"Day {current_day}" if nights <= 1 else f"Days {current_day}–{end_day}"

        city_web = web_data.get(city, {})
        image_url = city_web.get("image_url", "")
        description = city_web.get("description", "")
        weather = city_web.get("weather", {})
        accom = accommodation_data.get(city, {})
        city_acts_data = activities_data.get(city, {})
        city_acts = city_acts_data.get("activities", [])
        city_act_cost = city_acts_data.get("city_total_cost", 0)
        food_city = food_rate * max(nights, 1)

        # Inter-city transport leg into this city
        inter_leg = next(
            (l for l in flight_legs if l["to"] == city and l.get("type") == "inter_city"),
            None,
        )

        with st.container(border=True):
            if inter_leg:
                mode = inter_leg.get("mode", "flight").title()
                st.caption(
                    f"🔀 {inter_leg['from']} → {inter_leg['to']} by {mode} — €{inter_leg['cost_eur']:,.0f}"
                )

            # City header + image
            if image_url:
                img_col, info_col = st.columns([1, 2])
            else:
                img_col, info_col = None, st.columns([1])[0]

            if image_url and img_col is not None:
                with img_col:
                    st.image(image_url, use_container_width=True)

            with info_col:
                st.markdown(
                    f"### 📍 {city} {flag} "
                    f"<span style='font-size:0.85rem;color:#94a3b8;font-family:Inter,sans-serif;'>"
                    f"{day_range}</span>",
                    unsafe_allow_html=True,
                )
                if description:
                    st.caption(description)
                if weather.get("avg_high_c") is not None:
                    st.write(
                        f"{weather['emoji']} **{weather['condition']}** "
                        f"— {weather['avg_low_c']}°C to {weather['avg_high_c']}°C"
                    )

            # Cost metrics
            m1, m2, m3, m4 = st.columns(4)
            hotel_total = accom.get("total_cost", 0)
            nightly = accom.get("nightly_cost", 0)
            area = accom.get("recommended_area", "City Centre")
            city_subtotal = hotel_total + city_act_cost + food_city
            m1.metric("🏨 Hotel", f"€{hotel_total:,.0f}", f"€{nightly:,.0f}/night · {area}")
            m2.metric("🎭 Activities", f"€{city_act_cost:,.0f}")
            m3.metric("🍽️ Food", f"€{food_city:,.0f}", f"€{food_rate:,.0f}/day")
            m4.metric("📍 City Total", f"€{city_subtotal:,.0f}")

            # Activities by day
            if city_acts:
                acts_by_day: dict = {}
                for act in city_acts:
                    acts_by_day.setdefault(act.get("day", 1), []).append(act)

                st.markdown("**Activities:**")
                for d in sorted(acts_by_day.keys()):
                    global_d = current_day + d - 1
                    parts = []
                    for act in acts_by_day[d]:
                        cost_str = f"€{act['cost_eur']:,.0f}" if act["cost_eur"] > 0 else "free"
                        parts.append(f"{act['name']} ({cost_str})")
                    st.write(f"**Day {global_d}:** " + " · ".join(parts))

        current_day += max(nights, 1)

    # ── Return flight banner ───────────────────────────────────────────────
    inbound = next((l for l in flight_legs if l.get("type") == "inbound"), None)
    if inbound:
        mode = inbound.get("mode", "flight").title()
        st.info(
            f"✈️ **Return:** {inbound['from']} → {return_city} "
            f"by {mode} — €{inbound['cost_eur']:,.0f}"
        )


if st.session_state.itinerary and st.session_state.budget_result:
    budget_res = st.session_state.budget_result
    trip_plan = st.session_state.trip_plan
    prefs = st.session_state.preferences

    # ── Status banner ──────────────────────────────────────────────────────
    if budget_res.get("is_over_budget"):
        st.warning(
            f"Even after replanning, the trip is €{-budget_res['buffer']:.0f} over budget. "
            "Consider increasing your budget or reducing the duration."
        )
    else:
        st.success(
            f"Trip planned! You are **€{budget_res['buffer']:.0f} under** your "
            f"€{budget_res['user_budget']:.0f} budget."
        )

    # ── Top metrics row ────────────────────────────────────────────────────
    destinations = trip_plan.get("destinations", []) if trip_plan else []
    dep = prefs.get("departure_city", "?")
    ret = prefs.get("return_city", dep)
    route_str = " → ".join([dep] + destinations + [ret])

    st.markdown(
        f"<p style='text-align:center;color:#93c5fd;font-size:1rem;letter-spacing:0.05em;'>"
        f"{route_str}</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cost", f"€{budget_res.get('grand_total', 0):,.0f}")
    c2.metric("Budget", f"€{budget_res.get('user_budget', 0):,.0f}")
    c3.metric("Buffer", f"€{budget_res.get('buffer', 0):,.0f}")
    c4.metric("Destinations", str(len(destinations)))

    # ── Disclaimer ────────────────────────────────────────────────────────
    with st.expander("ℹ️ About these estimates — please read before booking"):
        st.markdown("""
**These are planning estimates, not real prices.**

All costs shown are computer-generated approximations based on historical
averages and seasonal patterns. They are designed to help you plan a
realistic budget, not to replace live booking platforms.

**Before booking anything, always verify on:**
- ✈️ **Flights** — [Skyscanner](https://www.skyscanner.net), [Google Flights](https://flights.google.com), or directly with the airline
- 🏨 **Hotels & rentals** — [Booking.com](https://www.booking.com), [Airbnb](https://www.airbnb.com), or [Hotels.com](https://www.hotels.com)
- 🚆 **Trains & buses** — [Trainline](https://www.thetrainline.com), [Omio](https://www.omio.com), or [FlixBus](https://www.flixbus.com)
- 🎭 **Activities** — official attraction websites or [GetYourGuide](https://www.getyourguide.com)

**Where the data comes from:**

| What | Source | Type |
|---|---|---|
| City descriptions | Wikipedia REST API | Live |
| Weather forecasts | Open-Meteo historical archive | Live (2025 data) |
| Transport costs | Distance-based model + seasonal multipliers | Estimated |
| Accommodation costs | Regional averages by travel style + season | Estimated |
| Activity suggestions | Local AI (llama3.1:8b) | AI-generated |
| City scoring | Curated dataset of 40 European cities | Static |
| Pricing calendar | Same transport + accommodation model, all 12 months | Estimated |

Prices can vary significantly depending on how far in advance you book,
airline sales, hotel availability, and local events. Budget an extra
10–15% as a safety buffer beyond what is shown here.
""")

    st.markdown("---")

    # ── Main layout: cards | charts ────────────────────────────────────────
    col_cards, col_charts = st.columns([3, 2])

    with col_cards:
        if trip_plan:
            render_trip_cards(trip_plan, budget_res, prefs)
        else:
            # Fallback: show the raw text itinerary if trip_plan not in session
            st.code(st.session_state.itinerary, language=None)

    with col_charts:
        # ── Cost breakdown pie ─────────────────────────────────────────────
        st.subheader("Cost Breakdown")
        costs_data = {
            "Category": ["Transport", "Accommodation", "Activities", "Food"],
            "Amount (€)": [
                budget_res.get("flights_cost", 0),
                budget_res.get("accommodation_cost", 0),
                budget_res.get("activities_cost", 0),
                budget_res.get("food_cost", 0),
            ],
        }
        fig_pie = px.pie(
            costs_data,
            values="Amount (€)",
            names="Category",
            color_discrete_sequence=["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b"],
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # ── Pricing calendar bar chart ─────────────────────────────────────
        pricing_cal = trip_plan.get("pricing_calendar", {}) if trip_plan else {}
        monthly_costs = pricing_cal.get("monthly_costs", [])

        if monthly_costs:
            st.subheader("📅 Pricing Calendar")
            cheapest = pricing_cal.get("cheapest_month", {}).get("month_name", "")
            most_exp = pricing_cal.get("most_expensive_month", {}).get("month_name", "")
            best_wx = pricing_cal.get("best_weather_months", [])

            df = pd.DataFrame(monthly_costs)
            df["highlight"] = df["month_name"].apply(
                lambda m: "Cheapest ✅" if m == cheapest
                else ("Most Expensive ❌" if m == most_exp else "Normal")
            )
            fig_bar = px.bar(
                df,
                x="month_name",
                y="estimated_cost",
                color="highlight",
                color_discrete_map={
                    "Cheapest ✅": "#22c55e",
                    "Most Expensive ❌": "#ef4444",
                    "Normal": "#3b82f6",
                },
                labels={"estimated_cost": "Est. Cost (€)", "month_name": ""},
            )
            fig_bar.update_layout(
                showlegend=True,
                legend=dict(title="", orientation="h", y=-0.25),
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                xaxis=dict(tickangle=-45),
            )
            fig_bar.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
            st.plotly_chart(fig_bar, use_container_width=True)

            if best_wx:
                st.caption(f"🌤️ Best weather: {', '.join(best_wx)}")
            if cheapest:
                cheap_cost = pricing_cal.get("cheapest_month", {}).get("estimated_cost", 0)
                st.caption(f"✅ Cheapest month: **{cheapest}** (~€{cheap_cost:,.0f})")
            if most_exp:
                exp_cost = pricing_cal.get("most_expensive_month", {}).get("estimated_cost", 0)
                st.caption(f"❌ Most expensive: **{most_exp}** (~€{exp_cost:,.0f})")

        # ── Agent Thinking ─────────────────────────────────────────────────
        st.subheader("🧠 How the agent planned this trip")
        with st.expander("See the agent's reasoning", expanded=False):
            _render_agent_thinking(trip_plan, budget_res, prefs)

else:
    # ── Welcome / hero screen ──────────────────────────────────────────────
    st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;
            justify-content:center;padding:72px 24px 56px;text-align:center;">
    <p style="font-size:3.8rem;margin:0 0 10px;line-height:1;">🌍</p>
    <h1 style="font-family:'Playfair Display',Georgia,serif;
               font-size:clamp(2rem,4.5vw,3.2rem);
               background:linear-gradient(135deg,#93c5fd 0%,#e0f2fe 50%,#bfdbfe 100%);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;
               margin:0 0 16px;line-height:1.15;">
        EuroTrip Agent
    </h1>
    <p style="font-size:1.1rem;color:#94a3b8;max-width:560px;line-height:1.75;margin:0 0 36px;">
        Set your travel preferences in the sidebar and let the AI build a personalised
        multi-city European itinerary with live weather, cost estimates, and a pricing calendar.
        Visit <strong style="color:#93c5fd;">1 to 6 countries</strong> — the agent enforces
        a minimum of 3 days per country so every stop is worth the journey.
        Six countries is the cap: even on a 30-day trip, more than that becomes a rushed
        airport-to-airport sprint rather than actual travel.
    </p>
    <div style="display:flex;gap:18px;flex-wrap:wrap;justify-content:center;
                color:#60a5fa;font-size:0.92rem;font-weight:500;letter-spacing:0.02em;">
        <span>✈️&nbsp; 40+ European cities</span>
        <span>🗺️&nbsp; 1–6 countries per trip</span>
        <span>💶&nbsp; Budget-aware</span>
        <span>🌤️&nbsp; Live weather</span>
        <span>📅&nbsp; Pricing calendar</span>
        <span>🤖&nbsp; Local AI</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:0.8rem;'>"
    "Built with Python · Streamlit · Ollama (llama3.1:8b) · Wikipedia · Open-Meteo"
    "</p>",
    unsafe_allow_html=True,
)
