"""Tests for the pure-Python logic in agent/core.py.

The LLM and external API calls are not tested here - only the
deterministic helper functions that can run without network access.
"""
from datetime import date

from agent.core import _fallback_city_distribution, _get_travel_year

# ── Shared fixtures ───────────────────────────────────────────────────────────

_CITIES = [
    {"name": "Barcelona", "country": "Spain"},
    {"name": "Paris",     "country": "France"},
    {"name": "Berlin",    "country": "Germany"},
    {"name": "Rome",      "country": "Italy"},
    {"name": "Vienna",    "country": "Austria"},
    {"name": "Amsterdam", "country": "Netherlands"},
    {"name": "Prague",    "country": "Czech Republic"},
    {"name": "Lisbon",    "country": "Portugal"},
]


def _prefs(duration=10, pace="moderate", num_countries=3):
    return {
        "duration": duration,
        "pace": pace,
        "num_countries": num_countries,
    }


# ── _fallback_city_distribution ───────────────────────────────────────────────

def test_nights_sum_to_duration():
    cities, nights = _fallback_city_distribution(_CITIES, _prefs())
    assert sum(nights.values()) == 10


def test_nights_sum_to_duration_slow_pace():
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=14, pace="slow", num_countries=2)
    )
    assert sum(nights.values()) == 14


def test_nights_sum_to_duration_fast_pace():
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=20, pace="fast", num_countries=4)
    )
    assert sum(nights.values()) == 20


def test_each_city_gets_at_least_one_night():
    cities, nights = _fallback_city_distribution(_CITIES, _prefs())
    for city in cities:
        assert nights[city] >= 1


def test_country_diversity_respected():
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(num_countries=4)
    )
    countries = {
        c["country"] for c in _CITIES if c["name"] in cities
    }
    assert len(countries) >= 4


def test_num_countries_one_gives_single_country():
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=5, pace="slow", num_countries=1)
    )
    countries = {
        c["country"] for c in _CITIES if c["name"] in cities
    }
    assert len(countries) == 1


def test_slow_pace_picks_two_cities():
    # slow pace target is 2 cities; num_countries=2 should still give 2
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=10, pace="slow", num_countries=2)
    )
    assert len(cities) == 2


def test_fast_pace_picks_more_cities():
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=20, pace="fast", num_countries=4)
    )
    assert len(cities) >= 4


def test_city_count_at_least_num_countries():
    # Even if pace says 3 cities, 5 countries means we need 5 cities minimum
    cities, nights = _fallback_city_distribution(
        _CITIES, _prefs(duration=20, pace="moderate", num_countries=5)
    )
    assert len(cities) >= 5


def test_all_returned_cities_have_night_entry():
    cities, nights = _fallback_city_distribution(_CITIES, _prefs())
    assert set(cities) == set(nights.keys())


def test_handles_single_city_pool():
    single = [{"name": "Paris", "country": "France"}]
    cities, nights = _fallback_city_distribution(
        single, _prefs(duration=5, pace="slow", num_countries=1)
    )
    assert cities == ["Paris"]
    assert nights["Paris"] == 5


# ── _get_travel_year ──────────────────────────────────────────────────────────

def test_travel_year_from_date_object():
    prefs = {"travel_start_date": date(2026, 7, 1)}
    assert _get_travel_year(prefs) == 2025  # capped at 2025


def test_travel_year_from_iso_string():
    prefs = {"travel_start_date": "2026-03-15"}
    assert _get_travel_year(prefs) == 2025


def test_travel_year_past_date_not_capped():
    prefs = {"travel_start_date": date(2024, 6, 1)}
    assert _get_travel_year(prefs) == 2024


def test_travel_year_defaults_when_missing():
    assert _get_travel_year({}) == 2025


def test_travel_year_invalid_string_falls_back():
    prefs = {"travel_start_date": "not-a-date"}
    assert _get_travel_year(prefs) == 2025
