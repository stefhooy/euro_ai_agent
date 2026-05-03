import concurrent.futures
import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 8

# Regional baseline daily costs in EUR (backpacker / mid_range / luxury)
REGIONAL_COSTS: Dict[str, Dict[str, int]] = {
    "western_europe":  {"backpacker": 75,  "mid_range": 160, "luxury": 400},
    "eastern_europe":  {"backpacker": 35,  "mid_range": 80,  "luxury": 220},
    "southern_europe": {"backpacker": 55,  "mid_range": 130, "luxury": 320},
    "northern_europe": {"backpacker": 85,  "mid_range": 180, "luxury": 450},
    "central_europe":  {"backpacker": 55,  "mid_range": 120, "luxury": 300},
}

# Regional baseline flight costs in EUR
REGIONAL_FLIGHT_COSTS: Dict[str, Dict[str, int]] = {
    "western_europe": {
        "from_western_europe": 70,
        "from_eastern_europe": 130,
        "from_north_america": 600,
        "from_uk": 65,
    },
    "eastern_europe": {
        "from_western_europe": 130,
        "from_eastern_europe": 60,
        "from_north_america": 700,
        "from_uk": 140,
    },
    "southern_europe": {
        "from_western_europe": 80,
        "from_eastern_europe": 120,
        "from_north_america": 620,
        "from_uk": 75,
    },
    "northern_europe": {
        "from_western_europe": 90,
        "from_eastern_europe": 150,
        "from_north_america": 580,
        "from_uk": 60,
    },
    "central_europe": {
        "from_western_europe": 85,
        "from_eastern_europe": 90,
        "from_north_america": 640,
        "from_uk": 100,
    },
}

# Best travel months by region
REGIONAL_BEST_MONTHS: Dict[str, List[int]] = {
    "western_europe":  [4, 5, 6, 7, 8, 9],
    "eastern_europe":  [5, 6, 7, 8, 9],
    "southern_europe": [4, 5, 6, 9, 10],
    "northern_europe": [6, 7, 8],
    "central_europe":  [5, 6, 7, 8, 9],
}


def get_coordinates(city_name: str, country: str) -> Dict[str, float]:
    """Fetch latitude and longitude for a city using Nominatim.

    Free, no API key required. Falls back to central Europe if unavailable.

    Args:
        city_name: Name of the city.
        country: Country name to disambiguate.

    Returns:
        Dict with 'lat' and 'lon' as floats.
    """
    try:
        params = {"q": f"{city_name}, {country}", "format": "json", "limit": 1}
        headers = {"User-Agent": "EuroTripAgent/1.0 (student project)"}
        r = requests.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=TIMEOUT
        )
        r.raise_for_status()
        results = r.json()
        if results:
            logger.info(f"Nominatim: coordinates found for {city_name}.")
            return {
                "lat": float(results[0]["lat"]),
                "lon": float(results[0]["lon"]),
            }
    except Exception as e:
        logger.warning(f"Nominatim failed for {city_name}: {e}")
    return {"lat": 48.2082, "lon": 16.3738}  # Vienna as fallback


def build_city_profile(seed_city: Dict[str, Any]) -> Dict[str, Any]:
    """Build a full scoring profile for a city from seed data.

    Uses pre-computed coordinates from the seed JSON; only calls Nominatim
    as a last resort for any city missing lat/lon.

    Args:
        seed_city: A dict from european_cities_seed.json.

    Returns:
        A complete city profile dict compatible with destination.py scoring.
    """
    name = seed_city["name"]
    country = seed_city["country"]
    region = seed_city.get("region", "western_europe")

    if "lat" in seed_city and "lon" in seed_city:
        geo: Dict[str, float] = {
            "lat": seed_city["lat"],
            "lon": seed_city["lon"],
        }
    else:
        geo = get_coordinates(name, country)

    base_costs = REGIONAL_COSTS[region].copy()

    return {
        "name": name,
        "country": country,
        "country_code": seed_city.get("country_code", "EU"),
        "currency": "EUR",
        "avg_daily_cost": base_costs,
        "avg_flight_cost": REGIONAL_FLIGHT_COSTS[region],
        "activity_tags": seed_city.get("activity_tags", []),
        "highlights": [],
        "best_months": REGIONAL_BEST_MONTHS[region],
        "geo": geo,
    }


def load_all_city_profiles(seed_path: str) -> List[Dict[str, Any]]:
    """Load all seed cities and build live profiles for each in parallel.

    Uses up to 8 threads to keep total fetch time under ~10 seconds.

    Args:
        seed_path: Absolute path to european_cities_seed.json.

    Returns:
        List of complete city profile dicts ready for scoring.
    """
    import json
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_cities = json.load(f)

    logger.info(
        f"Building live profiles for {len(seed_cities)} cities in parallel..."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        profiles = list(ex.map(build_city_profile, seed_cities))

    logger.info(f"All {len(profiles)} city profiles ready.")
    return profiles
