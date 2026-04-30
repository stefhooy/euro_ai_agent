import pytest
from tools.activities import get_activities


def test_activities_returns_correct_structure():
    result = get_activities(["Barcelona"], ["history", "museums"], {"Barcelona": 3})
    assert "city_activities" in result
    assert "total_activities_cost" in result


def test_activities_minimum_three_per_city():
    """Even with no preference matches, should return at least 3 activities."""
    result = get_activities(["Barcelona"], ["adventure"], {"Barcelona": 3})
    activities = result["city_activities"]["Barcelona"]["activities"]
    assert len(activities) >= 3


def test_activities_cost_is_non_negative():
    result = get_activities(["Paris"], ["food", "museums"], {"Paris": 4})
    total = result["city_activities"]["Paris"]["city_total_cost"]
    assert total >= 0


def test_activities_total_matches_sum_of_cities():
    result = get_activities(
        ["Barcelona", "Rome"],
        ["history", "food"],
        {"Barcelona": 3, "Rome": 3}
    )
    expected = (
        result["city_activities"]["Barcelona"]["city_total_cost"]
        + result["city_activities"]["Rome"]["city_total_cost"]
    )
    assert result["total_activities_cost"] == expected


def test_activities_unknown_city_returns_empty():
    result = get_activities(["Atlantis"], ["history"], {"Atlantis": 2})
    assert result["city_activities"]["Atlantis"]["activities"] == []
