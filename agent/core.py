import json
import logging
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

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

class ScoreDestinationsInput(BaseModel):
    preferences: Dict[str, Any] = Field(description="User travel preferences.")

@tool("score_destinations_tool", args_schema=ScoreDestinationsInput)
def score_destinations_tool(preferences: Dict[str, Any]) -> dict:
    """Scores and selects the best European cities based on user preferences."""
    global _agent_run_state
    logger.info("Executing score_destinations_tool...")
    result = score_destinations(preferences)
    # Store the full list of cities for the replanner to use later
    _agent_run_state['all_scored_cities'] = result.get("top_destinations", [])
    return result

class EstimateFlightsInput(BaseModel):
    departure_city: str = Field(description="The city where the trip starts.")
    destinations: List[str] = Field(description="List of city names to visit.")
    travel_month: int = Field(description="Month of travel (1-12).")
    travel_style: str = Field(default="mid_range", description="The travel style.")

@tool("estimate_flights_tool", args_schema=EstimateFlightsInput)
def estimate_flights_tool(departure_city: str, destinations: List[str], travel_month: int, travel_style: str = "mid_range") -> dict:
    """Estimates flight costs from departure_city to a list of destinations."""
    logger.info("Executing estimate_flights_tool...")
    return estimate_flights(departure_city, destinations, travel_month, travel_style)

class EstimateAccommodationInput(BaseModel):
    cities: List[str] = Field(description="List of city names to visit.")
    nights_per_city: Dict[str, int] = Field(description="Dictionary mapping each city name to the number of nights.")
    travel_style: str = Field(description="The user's travel style.")

@tool("estimate_accommodation_tool", args_schema=EstimateAccommodationInput)
def estimate_accommodation_tool(cities: List[str], nights_per_city: Dict[str, int], travel_style: str) -> dict:
    """
    Estimates accommodation costs for cities based on travel style and duration.
    nights_per_city is a dictionary mapping each city name to the number of nights.
    """
    logger.info("Executing estimate_accommodation_tool...")
    return estimate_accommodation(cities, nights_per_city, travel_style)

class GetActivitiesInput(BaseModel):
    cities: List[str] = Field(description="List of city names.")
    preferences: List[str] = Field(description="List of user activity preferences.")
    nights_per_city: Dict[str, int] = Field(description="Dictionary mapping each city name to the number of nights.")

@tool("get_activities_tool", args_schema=GetActivitiesInput)
def get_activities_tool(cities: List[str], preferences: List[str], nights_per_city: Dict[str, int]) -> dict:
    """Selects and schedules activities for cities based on preferences."""
    return get_activities(cities, preferences, nights_per_city)

class CalculateBudgetInput(BaseModel):
    trip_plan: Dict[str, Any] = Field(description="Current trip plan containing flights, accommodation, and activities.")
    user_budget: float = Field(description="Total user budget.")
    travel_style: str = Field(description="Travel style.")
    duration: int = Field(description="Total duration of the trip in days.")

@tool("calculate_budget_tool", args_schema=CalculateBudgetInput)
def calculate_budget_tool(trip_plan: Dict[str, Any], user_budget: float, travel_style: str, duration: int) -> dict:
    """
    Calculates total trip budget and compares against the user budget.
    trip_plan must be a dictionary containing 'flights', 'accommodation', and 'activities'
    which are the exact outputs of the previous tools.
    """
    logger.info("Executing calculate_budget_tool...")
    return calculate_budget(trip_plan, user_budget, travel_style, duration)

class ReplannerInput(BaseModel):
    trip_plan: Dict[str, Any] = Field(description="Current trip plan.")
    budget_result: Dict[str, Any] = Field(description="Current budget result.")

@tool("replanner_tool", args_schema=ReplannerInput)
def replanner_tool(trip_plan: Dict[str, Any], budget_result: Dict[str, Any]) -> dict:
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

    logger.info("Initializing Ollama ReAct Agent...")

    # Initialize Memory
    memory = TripMemory()
    memory.save_preferences(preferences)

    # Initialize LLM (runs locally via Ollama — no API key needed)
    llm = ChatOllama(
        model="llama3.1:8b",
        temperature=0.3,
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
        # Use .stream() with stream_mode="values" to get the full state at each step
        for chunk in agent.stream({"messages": messages}, stream_mode="values"):
            messages_list = chunk.get("messages", [])
            if messages_list:
                # We can inspect the latest message to see the agent's thought.
                last_message = messages_list[-1]
                if getattr(last_message, "type", None) == "ai" and getattr(last_message, "content", None):
                    # Log the thought in real-time
                    content = last_message.content
                    log_text = content.strip() if isinstance(content, str) else str(content)
                    logger.info(f"Agent Thought: {log_text}")
            
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
    llm = ChatOllama(model="mistral", temperature=0.3)
    
    prompt = f"""Please review the following European travel itinerary based on the user's preferences: {preferences}.
Itinerary:\n{itinerary}
Review this plan based on: 1) Is the budget allocation realistic? 2) Are cities geographically logical? 3) Are activities well matched?
Return a short critique (3-5 sentences) with 1-2 specific improvement suggestions."""
    return llm.invoke(prompt).content