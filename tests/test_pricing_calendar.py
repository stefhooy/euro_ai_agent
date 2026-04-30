from tools.pricing_calendar import get_pricing_calendar


def test_pricing_calendar_returns_12_months():
    result = get_pricing_calendar(["Barcelona", "Paris"], "mid_range", "Sofia")
    assert len(result["monthly_costs"]) == 12
    assert result["cheapest_month"]["month_name"] == "January"
    assert result["most_expensive_month"]["month_name"] in ["July", "August"]


def test_pricing_calendar_includes_weather_months():
    result = get_pricing_calendar(["Barcelona", "Paris"], "mid_range", "Sofia")
    assert "best_weather_months" in result
    assert result["best_weather_months"]
