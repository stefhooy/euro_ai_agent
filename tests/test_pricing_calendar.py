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
