import logging

from agent.core import run_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    sample_preferences = {
        "budget": 2500.0,
        "duration": 10,
        "departure_city": "Sofia",
        "travel_style": "mid_range",
        "activity_preferences": ["history", "food", "museums"],
        "pace": "moderate",
        "travel_month": 6,
    }

    logging.info("Starting EuroTrip Agent test run...")

    try:
        itinerary, budget_result, _ = run_agent(sample_preferences)
        print("\n\n" + "=" * 50)
        print(itinerary)
    except Exception as e:
        logging.error(f"Agent execution failed: {e}", exc_info=True)
        print(f"\nError: The agent encountered an issue: {e}")


if __name__ == "__main__":
    main()
