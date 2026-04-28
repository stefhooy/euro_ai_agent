import logging
import os
import sys
from dotenv import load_dotenv

# Set up Python logging to show INFO level with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Import the agent execution function
from agent.core import run_agent

def main():
    # Load environment variables from the .env file
    load_dotenv()
    
    if not os.environ.get("GOOGLE_API_KEY"):
        logging.error("GOOGLE_API_KEY environment variable is missing.")
        print("❌ Error: Please add your GOOGLE_API_KEY to the .env file.")
        sys.exit(1)
        
    # Sample preferences dict for testing
    sample_preferences = {
        "budget": 2500.0,
        "duration": 10,
        "departure_city": "Sofia",
        "travel_style": "mid_range",
        "activity_preferences": ["history", "food", "museums"],
        "pace": "moderate",
        "travel_month": 6
    }
    
    logging.info("Starting EuroTrip Agent test run...")
    
    try:
        # Call the agent
        itinerary, budget_result = run_agent(sample_preferences)
        print("\n\n" + "="*50)
        print(itinerary)
    except Exception as e:
        logging.error(f"Agent execution failed: {e}", exc_info=True)
        print(f"\n❌ Error: The agent encountered an issue while planning: {e}")

if __name__ == "__main__":
    main()