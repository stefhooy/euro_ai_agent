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

from agent.core import run_agent, run_critic
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
COUNTRY_COUNT_MAP = {"1": 1, "2": 2, "3": 3, "4+": 99}

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("itinerary", None), ("budget_result", None), ("preferences", None),
    ("critic_review", None), ("trip_plan", None),
    ("travel_start_date", date.today()),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def reset_app():
    for key in ("itinerary", "budget_result", "preferences", "critic_review", "trip_plan"):
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
        options=["1", "2", "3", "4+"],
        value="2",
    )
    num_countries_raw = COUNTRY_COUNT_MAP[num_countries_display]
    # Realism guard: minimum 3 days per country
    max_realistic = max(1, duration_input // 3)
    if num_countries_raw < 99 and num_countries_raw > max_realistic:
        st.warning(
            f"⚠️ Visiting {num_countries_display} countries in {duration_input} days "
            f"would be very rushed (< 3 days per country). "
            f"We'll cap it at **{max_realistic}** for a realistic trip."
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
            st.session_state.critic_review = None
        except Exception as e:
            progress_box.empty()
            st.error(f"An error occurred while planning the trip: {e}")
            st.code(traceback.format_exc(), language="python")


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

        # ── AI Critique ────────────────────────────────────────────────────
        st.subheader("Agent's Self-Review")
        with st.expander("View AI critique"):
            if st.session_state.critic_review is None:
                with st.spinner("Generating review..."):
                    st.session_state.critic_review = run_critic(
                        st.session_state.itinerary,
                        st.session_state.preferences,
                    )
            st.write(st.session_state.critic_review)

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
    <p style="font-size:1.1rem;color:#94a3b8;max-width:500px;line-height:1.75;margin:0 0 36px;">
        Set your travel preferences in the sidebar and let the AI build a personalised
        multi-city European itinerary with live weather, cost estimates, and a pricing calendar.
    </p>
    <div style="display:flex;gap:18px;flex-wrap:wrap;justify-content:center;
                color:#60a5fa;font-size:0.92rem;font-weight:500;letter-spacing:0.02em;">
        <span>✈️&nbsp; 40+ cities</span>
        <span>🏳️&nbsp; Domestic or international</span>
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
