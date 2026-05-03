from typing import Any, Dict

import streamlit as st

from ui.components.agent_thinking import render_agent_thinking
from ui.components.cards import render_trip_cards
from ui.components.charts import render_cost_pie, render_pricing_calendar

_DISCLAIMER_MD = """
**These are planning estimates, not real prices.**

All costs shown are computer-generated approximations based on historical
averages and seasonal patterns. They are designed to help you plan a
realistic budget, not to replace live booking platforms.

**Before booking anything, always verify on:**
- ✈️ **Flights** - [Skyscanner](https://www.skyscanner.net),
  [Google Flights](https://flights.google.com),
  or directly with the airline
- \U0001f3e8 **Hotels & rentals** -
  [Booking.com](https://www.booking.com),
  [Airbnb](https://www.airbnb.com), or
  [Hotels.com](https://www.hotels.com)
- \U0001f686 **Trains & buses** -
  [Trainline](https://www.thetrainline.com),
  [Omio](https://www.omio.com), or
  [FlixBus](https://www.flixbus.com)
- \U0001f3ad **Activities** - official attraction websites or
  [GetYourGuide](https://www.getyourguide.com)

**Where the data comes from:**

| What | Source | Type |
|---|---|---|
| City descriptions | Wikipedia REST API | Live |
| Weather forecasts | Open-Meteo historical archive | Live (2025 data) |
| Transport costs | Distance-based model + seasonal multipliers | Estimated |
| Accommodation costs | Regional averages by style + season | Estimated |
| Activity suggestions | Local AI (llama3.1:8b) | AI-generated |
| City scoring | Curated dataset of 40 European cities | Static |
| Pricing calendar | Transport + accommodation model, 12 months | Estimated |

Prices can vary significantly depending on how far in advance you book,
airline sales, hotel availability, and local events. Budget an extra
10-15% as a safety buffer beyond what is shown here.
"""


def render_results(
    itinerary: str,
    budget_result: Dict[str, Any],
    trip_plan: Dict[str, Any],
    preferences: Dict[str, Any],
) -> None:
    """Full results page: status, metrics, disclaimer, cards + charts."""
    dep = preferences.get("departure_city", "?")
    ret = preferences.get("return_city", dep)
    destinations = trip_plan.get("destinations", []) if trip_plan else []

    # Status banner
    if budget_result.get("is_over_budget"):
        st.warning(
            f"Even after replanning, the trip is "
            f"€{-budget_result['buffer']:.0f} over budget. "
            "Consider increasing your budget or reducing the duration."
        )
    else:
        st.success(
            f"Trip planned! You are "
            f"**€{budget_result['buffer']:.0f} under** your "
            f"€{budget_result['user_budget']:.0f} budget."
        )

    # Route string
    route_str = " → ".join([dep] + destinations + [ret])
    st.markdown(
        "<p style='text-align:center;"
        "color:#93c5fd;"
        "font-size:1rem;"
        "letter-spacing:0.05em;'>"
        f"{route_str}</p>",
        unsafe_allow_html=True,
    )

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cost", f"€{budget_result.get('grand_total', 0):,.0f}")
    c2.metric("Budget", f"€{budget_result.get('user_budget', 0):,.0f}")
    c3.metric("Buffer", f"€{budget_result.get('buffer', 0):,.0f}")
    c4.metric("Destinations", str(len(destinations)))

    # Disclaimer
    with st.expander(
        "ℹ️ About these estimates - please read before booking"
    ):
        st.markdown(_DISCLAIMER_MD)

    st.markdown("---")

    # Main layout
    col_cards, col_charts = st.columns([3, 2])

    with col_cards:
        if trip_plan:
            render_trip_cards(trip_plan, budget_result, preferences)
        else:
            st.code(itinerary, language=None)

    with col_charts:
        render_cost_pie(budget_result)

        pricing_cal = (
            trip_plan.get("pricing_calendar", {}) if trip_plan else {}
        )
        render_pricing_calendar(pricing_cal)

        st.subheader("\U0001f9e0 How Hermes planned this trip")
        with st.expander("See Hermes's reasoning", expanded=False):
            render_agent_thinking(trip_plan, budget_result, preferences)
