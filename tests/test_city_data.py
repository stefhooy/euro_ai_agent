from pathlib import Path

from tools.city_data import (
    REGIONAL_BEST_MONTHS,
    REGIONAL_COSTS,
    REGIONAL_FLIGHT_COSTS,
    build_city_profile,
    load_all_city_profiles,
)

_SEED_PATH = str(
    Path(__file__).parent.parent / "data" / "european_cities_seed.json"
)

_SAMPLE_SEED_CITY = {
    "name": "Vienna",
    "country": "Austria",
    "country_code": "AT",
    "region": "central_europe",
    "lat": 48.2082,
    "lon": 16.3738,
    "activity_tags": ["history", "museums", "food"],
}


# ── Regional lookup tables ────────────────────────────────────────────────────

def test_all_regions_have_cost_tiers():
    for region, costs in REGIONAL_COSTS.items():
        assert "backpacker" in costs
        assert "mid_range" in costs
        assert "luxury" in costs
        assert costs["backpacker"] < costs["mid_range"] < costs["luxury"], (
            f"{region}: costs are not ordered backpacker < mid_range < luxury"
        )


def test_all_regions_have_best_months():
    for region, months in REGIONAL_BEST_MONTHS.items():
        assert len(months) > 0
        assert all(1 <= m <= 12 for m in months), (
            f"{region}: contains invalid month numbers"
        )


def test_all_regions_covered_consistently():
    assert set(REGIONAL_COSTS.keys()) == set(REGIONAL_FLIGHT_COSTS.keys())
    assert set(REGIONAL_COSTS.keys()) == set(REGIONAL_BEST_MONTHS.keys())


# ── build_city_profile ────────────────────────────────────────────────────────

def test_build_city_profile_returns_required_keys():
    profile = build_city_profile(_SAMPLE_SEED_CITY)
    for key in (
        "name", "country", "avg_daily_cost",
        "avg_flight_cost", "activity_tags", "best_months", "geo",
    ):
        assert key in profile, f"Missing key: {key}"


def test_build_city_profile_uses_seed_coordinates():
    profile = build_city_profile(_SAMPLE_SEED_CITY)
    assert profile["geo"]["lat"] == _SAMPLE_SEED_CITY["lat"]
    assert profile["geo"]["lon"] == _SAMPLE_SEED_CITY["lon"]


def test_build_city_profile_cost_tiers_ordered():
    profile = build_city_profile(_SAMPLE_SEED_CITY)
    costs = profile["avg_daily_cost"]
    assert costs["backpacker"] < costs["mid_range"] < costs["luxury"]


def test_build_city_profile_preserves_activity_tags():
    profile = build_city_profile(_SAMPLE_SEED_CITY)
    assert profile["activity_tags"] == _SAMPLE_SEED_CITY["activity_tags"]


def test_build_city_profile_fallback_coordinates_when_missing():
    city_no_coords = {
        "name": "TestCity",
        "country": "TestLand",
        "region": "western_europe",
    }
    profile = build_city_profile(city_no_coords)
    # Should get the Vienna fallback (48.2082, 16.3738) or Nominatim result
    assert "lat" in profile["geo"]
    assert "lon" in profile["geo"]


# ── load_all_city_profiles ────────────────────────────────────────────────────

def test_load_all_city_profiles_returns_list():
    profiles = load_all_city_profiles(_SEED_PATH)
    assert isinstance(profiles, list)
    assert len(profiles) > 0


def test_load_all_city_profiles_each_has_name():
    profiles = load_all_city_profiles(_SEED_PATH)
    for p in profiles:
        assert "name" in p and p["name"]


def test_load_all_city_profiles_count_matches_seed():
    import json
    with open(_SEED_PATH, encoding="utf-8") as f:
        seed = json.load(f)
    profiles = load_all_city_profiles(_SEED_PATH)
    assert len(profiles) == len(seed)
