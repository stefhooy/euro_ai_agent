from tools.replanner import replan


def _make_over_budget_plan():
    """Helper: returns a minimal over-budget trip plan and budget result."""
    trip_plan = {
        "destinations": ["Paris", "Barcelona"],
        "nights_per_city": {"Paris": 5, "Barcelona": 3},
        "travel_style": "luxury",
        "flights": {"flight_legs": [], "total_flights_cost": 600},
        "accommodation": {
            "city_breakdown": {
                "Paris": {
                    "nightly_cost": 300,
                    "total_cost": 1500,
                    "recommended_area": "Le Marais",
                    "nights": 5,
                },
                "Barcelona": {
                    "nightly_cost": 200,
                    "total_cost": 600,
                    "recommended_area": "Eixample",
                    "nights": 3,
                },
            },
            "total_accommodation_cost": 2100,
        },
        "activities": {
            "city_activities": {
                "Paris": {
                    "activities": [
                        {
                            "name": "Louvre",
                            "cost_eur": 20,
                            "day": 1,
                            "category": "museums",
                            "description": "",
                        }
                    ],
                    "city_total_cost": 20,
                },
                "Barcelona": {
                    "activities": [
                        {
                            "name": "Sagrada Familia",
                            "cost_eur": 26,
                            "day": 1,
                            "category": "history",
                            "description": "",
                        }
                    ],
                    "city_total_cost": 26,
                },
            },
            "total_activities_cost": 46,
        },
    }
    budget_result = {
        "flights_cost": 600,
        "accommodation_cost": 2100,
        "activities_cost": 46,
        "food_cost": 800,
        "grand_total": 3546,
        "user_budget": 2000,
        "buffer": -1546,
        "is_over_budget": True,
    }
    return trip_plan, budget_result


def test_replan_returns_correct_structure():
    trip_plan, budget_result = _make_over_budget_plan()
    preferences = {
        "budget": 2000,
        "duration": 8,
        "departure_city": "Sofia",
        "travel_style": "luxury",
        "activity_preferences": ["history", "museums"],
        "travel_month": 6,
    }
    all_scored_cities = [
        {
            "name": "Prague",
            "avg_daily_cost": {"luxury": 150},
            "activity_tags": ["history"],
            "best_months": [5, 6],
            "avg_flight_cost": {"from_eastern_europe": 80},
        }
    ]
    result = replan(
        trip_plan, budget_result, all_scored_cities, preferences
    )
    assert "adjusted_trip_plan" in result
    assert "new_budget_result" in result
    assert "changes_made" in result


def test_replan_records_at_least_one_change():
    trip_plan, budget_result = _make_over_budget_plan()
    preferences = {
        "budget": 2000,
        "duration": 8,
        "departure_city": "Sofia",
        "travel_style": "luxury",
        "activity_preferences": ["history", "museums"],
        "travel_month": 6,
    }
    result = replan(trip_plan, budget_result, [], preferences)
    assert len(result["changes_made"]) >= 1
