from tools.budget import calculate_budget


def test_calculate_budget_under_budget():
    """Test budget math when the trip is perfectly under budget."""
    trip_plan = {
        "flights": {"total_flights_cost": 200},
        "accommodation": {"total_accommodation_cost": 300},
        "activities": {"total_activities_cost": 100},
    }
    # Food: mid_range = €45/day * 5 days = €225
    # Grand total = 200 + 300 + 100 + 225 = 825
    result = calculate_budget(
        trip_plan,
        user_budget=1000.0,
        travel_style="mid_range",
        duration=5,
    )
    assert result["grand_total"] == 825.0
    assert result["is_over_budget"] is False
    assert result["buffer"] == 175.0


def test_calculate_budget_over_budget():
    """Test budget math and flagging when the trip exceeds the budget."""
    trip_plan = {
        "flights": {"total_flights_cost": 500},
        "accommodation": {"total_accommodation_cost": 600},
        "activities": {"total_activities_cost": 200},
    }
    # Food: backpacker = €20/day * 10 days = €200
    # Grand total = 500 + 600 + 200 + 200 = 1500
    result = calculate_budget(
        trip_plan,
        user_budget=1000.0,
        travel_style="backpacker",
        duration=10,
    )
    assert result["grand_total"] == 1500.0
    assert result["is_over_budget"] is True
    assert result["buffer"] == -500.0
