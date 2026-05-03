from agent.planner import assemble_itinerary


def _make_sample_inputs():
    trip_plan = {
        "destinations": ["Barcelona", "Paris"],
        "nights_per_city": {"Barcelona": 3, "Paris": 4},
        "travel_style": "mid_range",
        "flights": {
            "flight_legs": [
                {
                    "from": "Sofia",
                    "to": "Barcelona",
                    "cost_eur": 120,
                    "type": "outbound",
                },
                {
                    "from": "Barcelona",
                    "to": "Paris",
                    "cost_eur": 100,
                    "type": "inter_city",
                },
                {
                    "from": "Paris",
                    "to": "Sofia",
                    "cost_eur": 130,
                    "type": "inbound",
                },
            ],
            "total_flights_cost": 350,
        },
        "accommodation": {
            "city_breakdown": {
                "Barcelona": {
                    "nightly_cost": 85,
                    "total_cost": 255,
                    "recommended_area": "Eixample",
                    "nights": 3,
                },
                "Paris": {
                    "nightly_cost": 100,
                    "total_cost": 400,
                    "recommended_area": "Le Marais",
                    "nights": 4,
                },
            },
            "total_accommodation_cost": 655,
        },
        "activities": {
            "city_activities": {
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
            },
            "total_activities_cost": 46,
        },
    }
    budget_result = {
        "flights_cost": 350,
        "accommodation_cost": 655,
        "activities_cost": 46,
        "food_cost": 315,
        "grand_total": 1366,
        "user_budget": 2500,
        "buffer": 1134,
        "is_over_budget": False,
    }
    preferences = {"duration": 7, "travel_style": "mid_range"}
    return trip_plan, budget_result, preferences


def test_assemble_itinerary_returns_string():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert isinstance(result, str)


def test_assemble_itinerary_contains_cities():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert "Barcelona" in result
    assert "Paris" in result


def test_assemble_itinerary_contains_cost_breakdown():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert "FULL COST BREAKDOWN" in result
    assert "TOTAL" in result
    assert "BUDGET" in result


def test_assemble_itinerary_contains_transport_summary_and_return():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    preferences["departure_city"] = "Sofia"
    preferences["return_city"] = "London"
    trip_plan["flights"]["transport_legs"] = [
        {
            "from": "Sofia",
            "to": "Barcelona",
            "cost_eur": 120,
            "type": "outbound",
            "mode": "flight",
            "direct": True,
            "changes": 0,
            "duration_hours": 3.1,
        },
        {
            "from": "Barcelona",
            "to": "Paris",
            "cost_eur": 80,
            "type": "inter_city",
            "mode": "train",
            "direct": True,
            "changes": 0,
            "duration_hours": 6.5,
        },
        {
            "from": "Paris",
            "to": "London",
            "cost_eur": 130,
            "type": "inbound",
            "mode": "flight",
            "direct": True,
            "changes": 0,
            "duration_hours": 2.8,
        },
    ]

    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert "Ending City:       London" in result
    assert "TRANSPORT SUMMARY" in result
    assert "Barcelona" in result
    assert "Train" in result


def test_assemble_itinerary_under_budget_status():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert "under budget" in result


def test_assemble_itinerary_over_budget_status():
    trip_plan, budget_result, preferences = _make_sample_inputs()
    budget_result["is_over_budget"] = True
    budget_result["buffer"] = -200
    result = assemble_itinerary(trip_plan, budget_result, preferences)
    assert "over budget" in result
