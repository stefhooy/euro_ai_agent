from tools.seasonality import (
    MONTHLY_MULTIPLIERS,
    get_month_multiplier,
    get_season_label,
)


def test_all_12_months_have_a_multiplier():
    for month in range(1, 13):
        result = get_month_multiplier(month)
        assert isinstance(result, float)
        assert result > 0


def test_multipliers_cover_all_calendar_months():
    assert set(MONTHLY_MULTIPLIERS.keys()) == set(range(1, 13))


def test_peak_summer_higher_than_winter():
    july = get_month_multiplier(7)
    january = get_month_multiplier(1)
    assert july > january


def test_december_higher_than_november():
    # Christmas / New Year premium
    assert get_month_multiplier(12) > get_month_multiplier(11)


def test_invalid_month_falls_back_to_april():
    assert get_month_multiplier(0) == MONTHLY_MULTIPLIERS[4]
    assert get_month_multiplier(13) == MONTHLY_MULTIPLIERS[4]


def test_multipliers_within_realistic_range():
    for month, mult in MONTHLY_MULTIPLIERS.items():
        assert 0.5 <= mult <= 2.0, (
            f"Month {month} multiplier {mult} is outside realistic range"
        )


def test_season_label_peak_for_summer():
    assert get_season_label(7) == "peak"
    assert get_season_label(8) == "peak"


def test_season_label_off_peak_for_january():
    assert get_season_label(1) == "off_peak"


def test_season_label_shoulder_for_october():
    assert get_season_label(10) == "shoulder"


def test_season_label_returns_string():
    for month in range(1, 13):
        label = get_season_label(month)
        assert isinstance(label, str)
        assert label in ("peak", "high", "shoulder", "off_peak")
