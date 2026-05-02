from datetime import date

STYLE_MAP = {"Backpacker": "backpacker", "Mid-range": "mid_range", "Luxury": "luxury"}
ACTIVITY_MAP = {
    "Museums": "museums", "Nightlife": "nightlife", "Nature": "nature",
    "Food & Gastronomy": "food", "History & Architecture": "history",
    "Shopping": "shopping", "Adventure Sports": "adventure",
}
PACE_MAP = {
    "Slow - fewer cities, more depth": "slow",
    "Moderate": "moderate",
    "Fast - more cities, less time each": "fast",
}
TRANSPORT_MODE_MAP = {"Flight": "flight", "Train": "train", "Bus": "bus"}
ROUTE_PRIORITY_MAP = {"Best balance": "best_balance", "Cheapest": "cheapest", "Fastest": "fastest"}
DIRECTNESS_MAP = {"Allow connections": "allow_connections", "Direct only": "direct_only"}
COUNTRY_COUNT_MAP = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6}

# Minimum all-in daily cost (accommodation + food + activities) and flat transport
# floor used to warn when the budget is unrealistic for the chosen travel style.
MIN_DAILY = {"backpacker": 55, "mid_range": 130, "luxury": 320}
MIN_TRANSPORT = {"backpacker": 200, "mid_range": 450, "luxury": 950}

SESSION_DEFAULTS = [
    ("itinerary", None), ("budget_result", None), ("preferences", None),
    ("trip_plan", None), ("travel_start_date", date.today()),
]
