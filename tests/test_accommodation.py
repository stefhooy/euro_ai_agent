import pytest
from tools.accommodation import estimate_accommodation


def test_accommodation_returns_correct_structure():
    result = estimate_accommodation(["Barcelona"], {"Barcelona": 3}, "mid_range")
    assert "city_breakdown" in result
    assert "total_accommodation_cost" in result


def test_accommodation_nightly_cost_backpacker_range():
    """Backpacker nightly cost must be clamped between €15 and €35."""
    result = estimate_accommodation(["Barcelona"], {"Barcelona": 1}, "backpacker")
    nightly = result["city_breakdown"]["Barcelona"]["nightly_cost"]
    assert 15 <= nightly <= 35


def test_accommodation_nightly_cost_midrange_range():
    """Mid-range nightly cost must be clamped between €60 and €120."""
    result = estimate_accommodation(["Paris"], {"Paris": 1}, "mid_range")
    nightly = result["city_breakdown"]["Paris"]["nightly_cost"]
    assert 60 <= nightly <= 120


def test_accommodation_nightly_cost_luxury_range():
    """Luxury nightly cost must be clamped between €150 and €400."""
    result = estimate_accommodation(["Paris"], {"Paris": 1}, "luxury")
    nightly = result["city_breakdown"]["Paris"]["nightly_cost"]
    assert 150 <= nightly <= 400


def test_accommodation_total_cost_multiplies_correctly():
    result = estimate_accommodation(["Prague"], {"Prague": 4}, "mid_range")
    breakdown = result["city_breakdown"]["Prague"]
    assert breakdown["total_cost"] == breakdown["nightly_cost"] * 4


def test_accommodation_multiple_cities():
    result = estimate_accommodation(
        ["Barcelona", "Rome"], {"Barcelona": 3, "Rome": 2}, "mid_range"
    )
    assert "Barcelona" in result["city_breakdown"]
    assert "Rome" in result["city_breakdown"]
    total = (
        result["city_breakdown"]["Barcelona"]["total_cost"]
        + result["city_breakdown"]["Rome"]["total_cost"]
    )
    assert result["total_accommodation_cost"] == total
