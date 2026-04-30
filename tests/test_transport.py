from tools.transport import estimate_transport


def test_transport_returns_expected_structure():
    result = estimate_transport(
        departure_city="Sofia",
        destinations=["Vienna", "Prague"],
        return_city="London",
        travel_month=5,
        travel_style="mid_range",
    )

    assert "transport_legs" in result
    assert "total_transport_cost" in result
    assert "total_flights_cost" in result
    assert len(result["transport_legs"]) == 3


def test_transport_uses_different_return_city():
    result = estimate_transport(
        departure_city="Sofia",
        destinations=["Paris"],
        return_city="London",
        travel_month=5,
        travel_style="mid_range",
    )

    inbound = result["transport_legs"][-1]
    assert inbound["from"] == "Paris"
    assert inbound["to"] == "London"


def test_transport_direct_only_filters_connection_options():
    result = estimate_transport(
        departure_city="Sofia",
        destinations=["Paris"],
        travel_month=7,
        travel_style="mid_range",
        directness="direct_only",
    )

    assert all(leg["direct"] for leg in result["transport_legs"])


def test_cheapest_priority_can_choose_bus_for_short_route():
    result = estimate_transport(
        departure_city="Vienna",
        destinations=["Prague"],
        travel_month=4,
        travel_style="backpacker",
        transport_modes=["train", "bus"],
        route_priority="cheapest",
    )

    assert result["transport_legs"][0]["mode"] in ["bus", "train"]
    assert result["total_transport_cost"] > 0
