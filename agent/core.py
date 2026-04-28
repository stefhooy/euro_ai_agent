import json
import logging
import os
from typing import Any, Dict, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from agent.memory import TripMemory
from agent.planner import assemble_itinerary

# Import raw tool logic
from tools.accommodation import estimate_accommodation
from tools.activities import get_activities
from tools.budget import calculate_budget
from tools.destination import score_destinations
from tools.flights import estimate_flights
from tools.replanner import replan

logger = logging.getLogger(__name__)

# This will hold state within a single run_agent call
_agent_run_state = {}

# ==========================================
# TOOL WRAPPERS
# ==========================================

@tool
def score_destinations_tool(preferences: dict) -> dict:
    """Scores and selects the best European cities based on user preferences."""
    global _agent_run_state
    logger.info("Executing score_destinations_tool...")
    result = score_destinations(preferences)
    # Store the full list of cities for the replanner to use later
    _agent_run_state['all_scored_cities'] = result.get("top_destinations", [])
    return result

@tool
def estimate_flights_tool(departure_city: str, destinations: list, travel_month: int, travel_style: str = "mid_range") -> dict:
    """Estimates flight costs from departure_city to a list of destinations."""
    logger.info("Executing estimate_flights_tool...")
    return estimate_flights(departure_city, destinations, travel_month, travel_style)

@tool
def estimate_accommodation_tool(cities: list, nights_per_city: dict, travel_style: str) -> dict:
    """
    Estimates accommodation costs for cities based on travel style and duration.
    nights_per_city is a dictionary mapping each city name to the number of nights.
    """
    logger.info("Executing estimate_accommodation_tool...")
    return estimate_accommodation(cities, nights_per_city, travel_style)

@tool
def get_activities_tool(cities: list, preferences: list, nights_per_city: dict) -> dict:
    """Selects and schedules activities for cities based on preferences."""
    return get_activities(cities, preferences, nights_per_city)

@tool
def calculate_budget_tool(trip_plan: dict, user_budget: float, travel_style: str, duration: int) -> dict:
    """
    Calculates total trip budget and compares against the user budget.
    trip_plan must be a dictionary containing 'flights', 'accommodation', and 'activities'
    which are the exact outputs of the previous tools.
    """
    logger.info("Executing calculate_budget_tool...")
    return calculate_budget(trip_plan, user_budget, travel_style, duration)

@tool
def replanner_tool(trip_plan: dict, budget_result: dict) -> dict:
    """Autonomously adjusts the trip plan to fit within the budget if it is over budget."""
    global _agent_run_state
    logger.info("Executing replanner_tool...")
    # The agent doesn't know about these, so we fetch them from our run state
    all_scored_cities = _agent_run_state.get('all_scored_cities', [])
    preferences = _agent_run_state.get('preferences', {})
    
    if not all_scored_cities or not preferences:
        logger.error("Replanner called without prior state (scored cities or preferences).")
        return {"error": "Internal state missing for replanner."}
        
    return replan(trip_plan, budget_result, all_scored_cities, preferences)


# ==========================================
# MAIN AGENT LOGIC
# ==========================================

def run_agent(preferences: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Runs the LangGraph ReAct agent to plan the trip.
    
    Args:
        preferences (dict): The user's travel preferences.
        
    Returns:
        Tuple[str, dict]: The formatted itinerary string and the budget breakdown dict.
    """
    global _agent_run_state
    _agent_run_state = {'preferences': preferences} # Prime the state

    logger.info("Initializing Gemini ReAct Agent...")
    
    # Initialize Memory
    memory = TripMemory()
    memory.save_preferences(preferences)
    
    # Initialize LLM
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable is not set!")
        raise ValueError("Missing GOOGLE_API_KEY. Please add it to your .env file.")
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.3,
        api_key=api_key
    )
    
    # Load tools
    tools = [
        score_destinations_tool,
        estimate_flights_tool,
        estimate_accommodation_tool,
        get_activities_tool,
        calculate_budget_tool,
        replanner_tool
    ]
    
    agent = create_react_agent(llm, tools)
    
    # Define the system prompt
    system_content = (
        "You are an expert European travel planner. Use the tools available to you in this order: "
        "first select destinations, then estimate flights, then estimate accommodation, then get activities, "
        "then calculate budget. If the budget is exceeded, use the replanner tool. "
        "Finally assemble the itinerary. Always reason step by step before calling each tool. "
        "Once the budget is calculated (and replanned if necessary), reply with 'PLANNING_COMPLETE'."
    )
    
    # Build user prompt
    user_content = (
        f"Plan a {preferences.get('duration', 10)}-day trip starting from "
        f"{preferences.get('departure_city', 'Sofia')}. "
        f"Budget: €{preferences.get('budget', 2500)}. "
        f"Style: {preferences.get('travel_style', 'mid_range')}. "
        f"Activities: {preferences.get('activity_preferences', [])}. "
        f"Travel Month: {preferences.get('travel_month', 6)}. "
        f"Pace: {preferences.get('pace', 'moderate')}."
    )
    
    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content)
    ]
    
    logger.info("Running agent ReAct loop (streaming)...")
    
    last_chunk = None
    try:
        # Use .stream() instead of .invoke() to get real-time updates
        for chunk in agent.stream({"messages": messages}):
            # The chunk is the full state of the graph at that point.
            # We can inspect the latest message to see the agent's thought.
            last_message = chunk.get("messages", [])[-1]
            if last_message.type == "ai" and last_message.content:
                # Log the thought in real-time
                logger.info(f"Agent Thought: {last_message.content.strip()}")
            
            # Keep track of the last state chunk
            last_chunk = chunk

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise RuntimeError(f"Failed to run the agent: {e}")
        
    logger.info("Agent stream complete. Extracting tool outputs from final state...")
    
    if not last_chunk:
        raise RuntimeError("Agent stream did not produce any output.")

    # We will reconstruct the final plan from the agent's tool calls and outputs
    trip_plan = {
        "destinations": [],
        "nights_per_city": {},
        "travel_style": preferences.get("travel_style", "mid_range"),
        "flights": {},
        "accommodation": {},
        "activities": {}
    }
    budget_result = {}
    
    # The final state is the last chunk from the stream
    result = last_chunk
    
    # Iterate through the message history to capture the state
    for msg in result.get("messages", []):
        # Log the AI's internal reasoning process
        if msg.type == "ai" and msg.content:
            logger.info(f"Agent Thought: {msg.content}")
            
        # 1. Capture the exact arguments the AI decided to pass to tools
        if msg.type == "ai" and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                if tc["name"] == "estimate_accommodation_tool":
                    args = tc.get("args", {})
                    if "cities" in args:
                        trip_plan["destinations"] = args["cities"]
                    if "nights_per_city" in args:
                        trip_plan["nights_per_city"] = args["nights_per_city"]
                        
        # 2. Capture the actual outputs returned by the tools
        elif msg.type == "tool":
            try:
                content = msg.content
                data = json.loads(content) if isinstance(content, str) else content
                
                if msg.name == "estimate_flights_tool":
                    trip_plan["flights"] = data
                elif msg.name == "estimate_accommodation_tool":
                    trip_plan["accommodation"] = data
                elif msg.name == "get_activities_tool":
                    trip_plan["activities"] = data
                elif msg.name == "calculate_budget_tool":
                    budget_result = data
                elif msg.name == "replanner_tool":
                    trip_plan = data.get("adjusted_trip_plan", trip_plan)
                    budget_result = data.get("new_budget_result", budget_result)
            except Exception as e:
                logger.debug(f"Could not parse tool output for {msg.name}: {e}")
                
    # Failsafe in case agent didn't complete the budget calculation
    if not budget_result:
        logger.warning("Agent did not produce a budget result. Using fallback calculation.")
        budget_result = calculate_budget(trip_plan, preferences.get("budget", 0), trip_plan["travel_style"], preferences.get("duration", 1))
        
    logger.info("Data extracted successfully. Formatting final itinerary...")
    final_itinerary = assemble_itinerary(trip_plan, budget_result, preferences)
    
    return final_itinerary, budget_result


# ==========================================
# CRITIC AGENT
# ==========================================

def run_critic(itinerary: str, preferences: dict) -> str:
    """Runs a secondary Critic Agent to review the finalized itinerary."""
    logger.info("Initializing Critic Agent...")
    api_key = os.environ.get("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, api_key=api_key)
    
    prompt = f"""Please review the following European travel itinerary based on the user's preferences: {preferences}.
Itinerary:\n{itinerary}
Review this plan based on: 1) Is the budget allocation realistic? 2) Are cities geographically logical? 3) Are activities well matched?
Return a short critique (3-5 sentences) with 1-2 specific improvement suggestions."""
    return llm.invoke(prompt).content