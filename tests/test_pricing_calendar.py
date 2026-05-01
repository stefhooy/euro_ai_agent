from tools.pricing_calendar import get_pricing_calendar


def test_pricing_calendar_returns_12_months():
    result = get_pricing_calendar(["Barcelona", "Paris"], "mid_range", "Sofia")
    costs = [month["estimated_cost"] for month in result["monthly_costs"]]

    assert len(result["monthly_costs"]) == 12
    assert result["cheapest_month"]["estimated_cost"] == min(costs)
    assert result["most_expensive_month"]["estimated_cost"] == max(costs)


def test_pricing_calendar_includes_weather_months():
    result = get_pricing_calendar(["Barcelona", "Paris"], "mid_range", "Sofia")
    assert "best_weather_months" in result
    assert result["best_weather_months"]


def test_pricing_calendar_uses_trip_nights_and_fixed_costs():
    base = get_pricing_calendar(["Barcelona"], "mid_range", "Sofia")
    custom = get_pricing_calendar(
        ["Barcelona"],
        "mid_range",
        "Sofia",
        nights_per_city={"Barcelona": 5},
        fixed_costs=300,
    )

    assert custom["monthly_costs"][0]["estimated_cost"] > base["monthly_costs"][0]["estimated_cost"]
