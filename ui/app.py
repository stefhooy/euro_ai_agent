import importlib
import sys
import traceback
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import agent.core as _agent_core
import agent.planner as _agent_planner
importlib.reload(_agent_core)
importlib.reload(_agent_planner)

from agent.core import run_agent

# Page config must be the first Streamlit call.
st.set_page_config(
    page_title="Hermes — AI Travel Planner",
    page_icon="🪽",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import inject_css
from ui.config import SESSION_DEFAULTS
from ui.sidebar import render_sidebar
from ui.components.hero import render_hero
from ui.components.results import render_results

inject_css()

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in SESSION_DEFAULTS:
    if key not in st.session_state:
        st.session_state[key] = default


def _reset_app() -> None:
    for key in ("itinerary", "budget_result", "preferences", "trip_plan"):
        st.session_state[key] = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
plan_button, preferences = render_sidebar(reset_callback=_reset_app)

# ── Plan button handler ───────────────────────────────────────────────────────
if plan_button:
    if not preferences["_activities_input"]:
        st.warning("Please select at least one activity preference.")
    elif not preferences["_transport_modes_input"]:
        st.warning("Please select at least one transport option.")
    else:
        # Remove UI-only sentinel keys before passing to the agent.
        agent_prefs = {k: v for k, v in preferences.items() if not k.startswith("_")}

        progress_box = st.empty()

        def _update_progress(msg: str) -> None:
            progress_box.info(msg)

        try:
            itinerary, budget_result, trip_plan = run_agent(
                agent_prefs, progress_callback=_update_progress
            )
            progress_box.empty()
            st.session_state.itinerary = itinerary
            st.session_state.budget_result = budget_result
            st.session_state.preferences = agent_prefs
            st.session_state.trip_plan = trip_plan
        except Exception as e:
            progress_box.empty()
            st.error(f"An error occurred while planning the trip: {e}")
            st.code(traceback.format_exc(), language="python")

# ── Main content ──────────────────────────────────────────────────────────────
if st.session_state.itinerary and st.session_state.budget_result:
    render_results(
        itinerary=st.session_state.itinerary,
        budget_result=st.session_state.budget_result,
        trip_plan=st.session_state.trip_plan,
        preferences=st.session_state.preferences,
    )
else:
    render_hero()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:0.8rem;'>"
    "Built with Python · Streamlit · Ollama (llama3.1:8b) · Wikipedia · Open-Meteo"
    "</p>",
    unsafe_allow_html=True,
)
