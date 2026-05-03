import importlib
import sys
import traceback
from pathlib import Path

from PIL import Image
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
_icon_path = Path(__file__).parent / "assets" / "web_euro.png"
_hermes_path = Path(__file__).parent / "assets" / "hermes.png"
_page_icon = Image.open(_icon_path) if _icon_path.exists() else "\U0001fa75"
st.set_page_config(
    page_title="Hermes - Euro AI Travel Planner",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import inject_css
from ui.config import SESSION_DEFAULTS
from ui.sidebar import render_sidebar
from ui.components.hero import render_hero
from ui.components.results import render_results

inject_css()

# Session state
for key, default in SESSION_DEFAULTS:
    if key not in st.session_state:
        st.session_state[key] = default


def _reset_app() -> None:
    for key in (
        "itinerary", "budget_result", "preferences", "trip_plan"
    ):
        st.session_state[key] = None


def _render_hermes_progress(slot, message: str, width: int = 36) -> None:
    with slot.container():
        img_col, text_col = st.columns([1, 12])
        with img_col:
            if _hermes_path.exists():
                st.image(str(_hermes_path), width=width)
        with text_col:
            st.markdown(f"**{message}**")


# Sidebar
plan_button, preferences = render_sidebar(reset_callback=_reset_app)

# How many progress callbacks run_agent fires (one per _cb() call)
_TOTAL_STEPS = 8

# Plan button handler
if plan_button:
    if not preferences["_activities_input"]:
        st.warning("Please select at least one activity preference.")
    elif not preferences["_transport_modes_input"]:
        st.warning("Please select at least one transport option.")
    else:
        # Remove UI-only sentinel keys before passing to the agent.
        agent_prefs = {
            k: v for k, v in preferences.items()
            if not k.startswith("_")
        }

        with st.status(
            "Hermes is thinking and planning your trip...",
            expanded=True,
        ) as _status:
            _render_hermes_progress(
                st.empty(),
                "Hermes is thinking and planning your trip...",
            )
            st.markdown(
                "**Please remain patient** - Hermes is consulting "
                "a local AI model and fetching live data. "
                "This typically takes **30-60 seconds**."
            )
            _bar = st.progress(0.0)
            _msg = st.empty()
            _step = [0]

            def _update_progress(msg: str) -> None:
                _step[0] += 1
                pct = min(_step[0] / _TOTAL_STEPS, 1.0)
                _bar.progress(
                    pct,
                    text=(
                        f"Step {_step[0]} of {_TOTAL_STEPS}"
                    ),
                )
                _render_hermes_progress(_msg, msg, width=36)

            try:
                itinerary, budget_result, trip_plan = run_agent(
                    agent_prefs,
                    progress_callback=_update_progress,
                )
                _bar.progress(1.0, text="Done!")
                _status.update(
                    label=(
                        "✅  Trip planned! "
                        "Scroll down to see your itinerary."
                    ),
                    state="complete",
                    expanded=False,
                )
                st.session_state.itinerary = itinerary
                st.session_state.budget_result = budget_result
                st.session_state.preferences = agent_prefs
                st.session_state.trip_plan = trip_plan
            except Exception as e:
                _status.update(
                    label="❌  Planning failed - see error below.",
                    state="error",
                    expanded=True,
                )
                st.error(
                    "An error occurred while planning the trip: "
                    f"{e}"
                )
                st.code(traceback.format_exc(), language="python")

# Main content
if st.session_state.itinerary and st.session_state.budget_result:
    render_results(
        itinerary=st.session_state.itinerary,
        budget_result=st.session_state.budget_result,
        trip_plan=st.session_state.trip_plan,
        preferences=st.session_state.preferences,
    )
else:
    render_hero()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#475569;font-size:0.8rem;'>"
    "Built with Python · Streamlit · "
    "Ollama (llama3.1:8b) · Wikipedia · Open-Meteo"
    "</p>",
    unsafe_allow_html=True,
)
