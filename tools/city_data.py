import concurrent.futures
import logging
import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TELEPORT_SEARCH = "https://api.teleport.org/api/cities/"
TIMEOUT = 8

# Regional baseline daily costs in EUR (backpacker / mid_range / luxury)
REGIONAL_COSTS = {
    "western_europe":  {"backpacker": 75,  "mid_range": 160, "luxury": 400},
    "eastern_europe":  {"backpacker": 35,  "mid_range": 80,  "luxury": 220},
    "southern_europe": {"backpacker": 55,  "mid_range": 130, "luxury": 320},
    "northern_europe": {"backpacker": 85,  "mid_range": 180, "luxury": 450},
    "central_europe":  {"backpacker": 55,  "mid_range": 120, "luxury": 300},
}

# Regional baseline flight costs in EUR
REGIONAL_FLIGHT_COSTS = {
    "western_europe":  {"from_western_europe": 70,  "from_eastern_europe": 130, "from_north_america": 600, "from_uk": 65},
    "eastern_europe":  {"from_western_europe": 130, "from_eastern_europe": 60,  "from_north_america": 700, "from_uk": 140},
    "southern_europe": {"from_western_europe": 80,  "from_eastern_europe": 120, "from_north_america": 620, "from_uk": 75},
    "northern_europe": {"from_western_europe": 90,  "from_eastern_europe": 150, "from_north_america": 580, "from_uk": 60},
    "central_europe":  {"from_western_europe": 85,  "from_eastern_europe": 90,  "from_north_america": 640, "from_uk": 100},
}

# Best travel months by region
REGIONAL_BEST_MONTHS = {
    "western_europe":  [4, 5, 6, 7, 8, 9],
    "eastern_europe":  [5, 6, 7, 8, 9],
    "southern_europe": [4, 5, 6, 9, 10],
    "northern_europe": [6, 7, 8],
    "central_europe":  [5, 6, 7, 8, 9],
}


def get_coordinates(city_name: str, country: str) -> dict:
    """
    Fetches latitude and longitude for a city using Nominatim (OpenStreetMap).
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
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json()
        if results:
            logger.info(f"Nominatim: coordinates found for {city_name}.")
            return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
    except Exception as e:
        logger.warning(f"Nominatim failed for {city_name}: {e}")
    return {"lat": 48.2082, "lon": 16.3738}  # Vienna as fallback


def get_teleport_cost_modifier(city_name: str) -> float | None:
    """
    Fetches a cost of living modifier from the Teleport API.
    Returns a multiplier (0.6 = very cheap, 1.6 = very expensive),
    or None if the city is not in Teleport's database.

    Args:
        city_name: Name of the city.

    Returns:
        Float multiplier or None on failure.
    """
    try:
        params = {
            "search": city_name,
            "embed": "city:search-results/city:item/city:urban_area",
        }
        r = requests.get(TELEPORT_SEARCH, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

        results = data.get("_embedded", {}).get("city:search-results", [])
        if not results:
            return None

        item = results[0].get("_embedded", {}).get("city:item", {})
        ua_link = item.get("_links", {}).get("city:urban_area")
        if not ua_link:
            return None

        scores_r = requests.get(f"{ua_link['href']}scores/", timeout=TIMEOUT)
        scores_r.raise_for_status()
        categories = scores_r.json().get("categories", [])

        for cat in categories:
            if cat.get("name") == "Cost of Living":
                score = cat["score_out_of_10"]
                # Higher score = cheaper city
                if score >= 8:   return 0.6
                elif score >= 6: return 0.8
                elif score >= 4: return 1.0
                elif score >= 2: return 1.3
                else:            return 1.6
    except Exception as e:
        logger.warning(f"Teleport failed for {city_name}: {e}")
    return None


def build_city_profile(seed_city: dict) -> dict:
    """
    Builds a full scoring profile for a city by combining the seed data
    with live Nominatim coordinates and Teleport cost modifiers.
    Both API calls run in parallel. Falls back gracefully on any failure.

    Args:
        seed_city: A dict from european_cities_seed.json with name, country, region, tags.

    Returns:
        A complete city profile dict compatible with destination.py scoring.
    """
    name = seed_city["name"]
    country = seed_city["country"]
    region = seed_city.get("region", "western_europe")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        coord_f = ex.submit(get_coordinates, name, country)
        cost_f = ex.submit(get_teleport_cost_modifier, name)
        geo = coord_f.result()
        cost_modifier = cost_f.result()

    base_costs = REGIONAL_COSTS[region].copy()
    if cost_modifier:
        base_costs = {k: round(v * cost_modifier) for k, v in base_costs.items()}
        logger.info(f"Teleport modifier {cost_modifier:.1f}x applied to {name} costs.")

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


def load_all_city_profiles(seed_path: str) -> list:
    """
    Loads all seed cities and builds live profiles for each in parallel.
    Uses up to 8 threads to keep total fetch time under ~10 seconds.

    Args:
        seed_path: Absolute path to european_cities_seed.json.

    Returns:
        List of complete city profile dicts ready for scoring.
    """
    import json
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_cities = json.load(f)

    logger.info(f"Building live profiles for {len(seed_cities)} cities in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        profiles = list(ex.map(build_city_profile, seed_cities))

    logger.info(f"All {len(profiles)} city profiles ready.")
    return profiles
