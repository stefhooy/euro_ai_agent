from tools.flights import estimate_flights, _get_departure_region
from tools.seasonality import MONTHLY_MULTIPLIERS


def test_departure_region_eastern_europe():
    assert _get_departure_region("Sofia") == "from_eastern_europe"
    assert _get_departure_region("sofia") == "from_eastern_europe"


def test_departure_region_western_europe():
    assert _get_departure_region("Paris") == "from_western_europe"


def test_departure_region_uk():
    assert _get_departure_region("London") == "from_uk"


def test_departure_region_unknown_defaults_to_western():
    assert _get_departure_region("Timbuktu") == "from_western_europe"


def test_estimate_flights_returns_correct_structure():
    result = estimate_flights(
        "Sofia", ["Barcelona", "Paris"], travel_month=6
    )
    assert "flight_legs" in result
    assert "total_flights_cost" in result


def test_estimate_flights_leg_count():
    """3 destinations = outbound + 2 inter-city + inbound = 4 legs."""
    result = estimate_flights(
        "Sofia",
        ["Barcelona", "Paris", "Rome"],
        travel_month=6,
    )
    assert len(result["flight_legs"]) == 4


def test_estimate_flights_total_is_positive():
    result = estimate_flights("Sofia", ["Barcelona"], travel_month=6)
    assert result["total_flights_cost"] > 0


def test_estimate_flights_peak_more_expensive_than_offpeak():
    peak = estimate_flights("Sofia", ["Barcelona"], travel_month=7)
    offpeak = estimate_flights("Sofia", ["Barcelona"], travel_month=1)
    assert peak["total_flights_cost"] > offpeak["total_flights_cost"]


def test_estimate_flights_accepts_return_city():
    result = estimate_flights(
        "Sofia",
        ["Barcelona"],
        travel_month=6,
        return_city="London",
    )
    assert result["flight_legs"][-1]["to"] == "London"


def test_monthly_multiplier_table_covers_all_months():
    assert set(MONTHLY_MULTIPLIERS.keys()) == set(range(1, 13))
    assert MONTHLY_MULTIPLIERS[7] == 1.40
    assert MONTHLY_MULTIPLIERS[1] == 0.70
