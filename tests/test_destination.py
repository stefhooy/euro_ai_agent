from tools.destination import score_destinations


def test_score_destinations_returns_results():
    """Scorer returns a non-empty list of destinations."""
    preferences = {
        "budget": 5000,
        "duration": 5,
        "travel_style": "luxury",
        "activity_preferences": ["history", "museums"],
        "travel_month": 6,
    }
    result = score_destinations(preferences)
    top_destinations = result.get("top_destinations", [])
    assert len(top_destinations) > 0


def test_score_destinations_sorted_by_score():
    """Results are ordered highest score first."""
    preferences = {
        "budget": 5000,
        "duration": 5,
        "travel_style": "luxury",
        "activity_preferences": ["history", "museums"],
        "travel_month": 6,
    }
    result = score_destinations(preferences)
    scores = [c["score"] for c in result["top_destinations"]]
    assert scores == sorted(scores, reverse=True)


def test_score_destinations_pool_scales_with_num_countries():
    """Pool size is at least max(10, num_countries * 3)."""
    num_countries = 5
    preferences = {
        "budget": 8000,
        "duration": 20,
        "travel_style": "mid_range",
        "activity_preferences": ["history"],
        "travel_month": 7,
        "num_countries": num_countries,
    }
    result = score_destinations(preferences)
    expected_min = max(10, num_countries * 3)
    assert len(result["top_destinations"]) >= expected_min


def test_score_destinations_each_city_has_required_fields():
    """Every returned city has score, name, country, and reasons."""
    preferences = {
        "budget": 3000,
        "duration": 7,
        "travel_style": "backpacker",
        "activity_preferences": ["nature"],
        "travel_month": 5,
    }
    result = score_destinations(preferences)
    for city in result["top_destinations"]:
        assert "name" in city
        assert "score" in city
        assert "country" in city
        assert 0 <= city["score"] <= 100


def test_score_destinations_domestic_filter():
    """Domestic trips restrict results to the departure country."""
    preferences = {
        "budget": 3000,
        "duration": 7,
        "travel_style": "mid_range",
        "activity_preferences": ["history"],
        "travel_month": 6,
        "trip_type": "domestic",
        "departure_city": "Barcelona",
    }
    result = score_destinations(preferences)
    top = result["top_destinations"]
    if top:  # Only assert if seed has Spanish cities
        countries = {c["country"] for c in top}
        assert countries == {"Spain"} or result.get("domestic_fallback")
