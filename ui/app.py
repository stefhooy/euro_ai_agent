import sys
from pathlib import Path
from datetime import date, timedelta
import streamlit as st
import plotly.express as px

from dotenv import load_dotenv

# Ensure the root project directory is in the Python path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env file
load_dotenv()

from agent.core import run_agent, run_critic

# --- MAPPINGS ---
STYLE_MAP = {"Backpacker": "backpacker", "Mid-range": "mid_range", "Luxury": "luxury"}
ACTIVITY_MAP = {
    "Museums": "museums",
    "Nightlife": "nightlife",
    "Nature": "nature",
    "Food & Gastronomy": "food",
    "History & Architecture": "history",
    "Shopping": "shopping",
    "Adventure Sports": "adventure"
}
PACE_MAP = {
    "Slow - fewer cities": "slow",
    "Moderate": "moderate",
    "Fast - more cities": "fast"
}
MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

st.set_page_config(page_title="EuroTrip Agent", page_icon="🌍", layout="wide")

# --- INITIALIZE SESSION STATE ---
if "itinerary" not in st.session_state:
    st.session_state.itinerary = None
if "budget_result" not in st.session_state:
    st.session_state.budget_result = None
if "preferences" not in st.session_state:
    st.session_state.preferences = None
if "critic_review" not in st.session_state:
    st.session_state.critic_review = None
if "travel_start_date" not in st.session_state:
    st.session_state.travel_start_date = date.today()
if "travel_end_date" not in st.session_state:
    st.session_state.travel_end_date = st.session_state.travel_start_date + timedelta(days=10)

def reset_app():
    st.session_state.itinerary = None
    st.session_state.budget_result = None
    st.session_state.preferences = None
    st.session_state.critic_review = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌍 EuroTrip Agent")
    st.subheader("AI-Powered European Travel Planner")
    st.markdown("---")
    
    budget_input = st.number_input("Total Budget (€)", min_value=500, max_value=20000, value=2500, step=100)
    duration_input = st.slider("Trip Duration (Days)", min_value=3, max_value=30, value=10)
    departure_input = st.text_input("Departure City", value="Sofia")
    style_input = st.selectbox("Travel Style", options=list(STYLE_MAP.keys()), index=1)
    travel_start_input = st.date_input("Travel Start Date", value=st.session_state.travel_start_date)
    travel_end_date = travel_start_input + timedelta(days=int(duration_input))
    st.session_state.travel_start_date = travel_start_input
    st.session_state.travel_end_date = travel_end_date
    st.caption(f"Trip ends on {travel_end_date.isoformat()}")
    
    activities_input = st.multiselect(
        "Activity Preferences", 
        options=list(ACTIVITY_MAP.keys()),
        default=["History & Architecture", "Food & Gastronomy", "Museums"]
    )
    
    pace_input = st.selectbox("Pace", options=list(PACE_MAP.keys()), index=1)
    
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    with col1:
        plan_button = st.button("✈️ Plan My Trip", use_container_width=True, type="primary")
    with col2:
        st.button("🔄 Reset", on_click=reset_app, use_container_width=True)

# --- MAIN AREA ---
if plan_button:
    if budget_input < 500:
        st.error("❌ Budget is too low. Please enter a budget of at least €500.")
    elif not activities_input:
        st.warning("⚠️ Please select at least one activity preference.")
    else:
        # Map UI inputs to backend-friendly dictionary
        preferences = {
            "budget": float(budget_input),
            "duration": int(duration_input),
            "departure_city": departure_input.strip(),
            "travel_style": STYLE_MAP[style_input],
            "activity_preferences": [ACTIVITY_MAP[act] for act in activities_input],
            "pace": PACE_MAP[pace_input],
            "travel_month": travel_start_input.month,
            "travel_start_date": travel_start_input.isoformat(),
            "travel_end_date": travel_end_date.isoformat(),
        }
        
        with st.spinner("🤖 Agent is planning your trip. This takes about 15-30 seconds..."):
            try:
                # Call the LangGraph agent
                itinerary, budget_result = run_agent(preferences)
                
                # Save to session state
                st.session_state.itinerary = itinerary
                st.session_state.budget_result = budget_result
                st.session_state.preferences = preferences
                st.session_state.critic_review = None  # reset so critic reruns for new plan
            except Exception as e:
                st.error(f"An error occurred while planning the trip: {e}")

if st.session_state.itinerary and st.session_state.budget_result:
    budget_res = st.session_state.budget_result
    
    # Show Success or Warning depending on budget replanner results
    if budget_res.get("is_over_budget"):
        st.warning(f"⚠️ Even after replanning, the trip is slightly over budget by €{-budget_res['buffer']:.0f}. Consider increasing your budget or shortening the trip.")
    else:
        st.success(f"✅ Trip successfully planned! You are €{budget_res['buffer']:.0f} under your €{budget_res['user_budget']:.0f} budget.")
        
    # Create layout columns for the content
    col_itinerary, col_charts = st.columns([2, 1])
    
    with col_itinerary:
        with st.container(border=True):
            st.markdown(st.session_state.itinerary)
            
    with col_charts:
        # Plotly Pie Chart
        st.subheader("Cost Breakdown")
        costs_data = {
            "Category": ["Flights", "Accommodation", "Activities", "Food"],
            "Amount (€)": [
                budget_res.get("flights_cost", 0),
                budget_res.get("accommodation_cost", 0),
                budget_res.get("activities_cost", 0),
                budget_res.get("food_cost", 0)
            ]
        }
        fig = px.pie(costs_data, values="Amount (€)", names="Category", 
                     color_discrete_sequence=px.colors.sequential.Teal)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
        # Critic Agent Self-Review
        st.subheader("Agent's Self-Review")
        with st.expander("🤖 View Agent Critique"):
            if st.session_state.critic_review is None:
                with st.spinner("Generating review..."):
                    st.session_state.critic_review = run_critic(
                        st.session_state.itinerary, st.session_state.preferences
                    )
            st.write(st.session_state.critic_review)

else:
    # Hero section when empty
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>Welcome to the EuroTrip Agent 🌍</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Adjust your travel preferences in the sidebar and click <b>Plan My Trip</b> to unleash the AI agent!</p>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Built with LangGraph + Ollama (Mistral) | Master's AI Project</p>", unsafe_allow_html=True)
