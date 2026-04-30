"""Shared seasonal pricing helpers."""

MONTHLY_MULTIPLIERS = {
    1: 0.70,
    2: 0.72,
    3: 0.85,
    4: 1.00,
    5: 1.10,
    6: 1.25,
    7: 1.40,
    8: 1.40,
    9: 1.05,
    10: 0.95,
    11: 0.78,
    12: 1.20,
}


def get_month_multiplier(month: int) -> float:
    """Return the seasonal cost multiplier for a month, defaulting to April."""
    return MONTHLY_MULTIPLIERS.get(int(month), MONTHLY_MULTIPLIERS[4])


def get_season_label(month: int) -> str:
    """Return a short user-facing label for the pricing season."""
    multiplier = get_month_multiplier(month)
    if multiplier >= 1.30:
        return "peak"
    if multiplier >= 1.10:
        return "high"
    if multiplier >= 0.95:
        return "shoulder"
    return "off_peak"
