import concurrent.futures
import logging
import requests

logger = logging.getLogger(__name__)

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WEATHER_API = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT = 8


def get_wiki_summary(city_name: str) -> str:
    """
    Fetches a short description of a city from the Wikipedia REST API.

    Args:
        city_name: Name of the city.

    Returns:
        A 1-2 sentence plain-text summary, or a fallback string on failure.
    """
    try:
        url = WIKI_API.format(city_name.replace(" ", "_"))
        headers = {"User-Agent": "EuroTripAgent/1.0 (student project; contact: eurotrip-agent@example.com)"}
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        extract = data.get("extract", "")
        sentences = extract.split(". ")
        summary = ". ".join(sentences[:2]).strip()
        if summary and not summary.endswith("."):
            summary += "."
        image_url = data.get("thumbnail", {}).get("source", "")
        logger.info(f"Wikipedia summary fetched for {city_name}.")
        return {"text": summary, "image_url": image_url}
    except Exception as e:
        logger.warning(f"Wikipedia fetch failed for {city_name}: {e}")
        return {"text": f"{city_name} is a popular European travel destination.", "image_url": ""}


def get_weather_summary(city_name: str, lat: float, lon: float, month: int, year: int = 2025) -> dict:
    """
    Fetches average temperature and precipitation for a city in a given month
    using the Open-Meteo historical weather archive (free, no API key).

    Args:
        city_name: Name of the city (for logging).
        lat: Latitude of the city.
        lon: Longitude of the city.
        month: Travel month as integer (1-12).
        year: Historical archive year to use.

    Returns:
        Dict with avg_high_c, avg_low_c, avg_precipitation_mm, condition, emoji.
    """
    try:
        month_str = f"{month:02d}"
        # Last day of month (use 28 to be safe across all months)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{year}-{month_str}-01",
            "end_date": f"{year}-{month_str}-28",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
        }
        response = requests.get(WEATHER_API, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json().get("daily", {})

        temps_max = [t for t in data.get("temperature_2m_max", []) if t is not None]
        temps_min = [t for t in data.get("temperature_2m_min", []) if t is not None]
        precip = [p for p in data.get("precipitation_sum", []) if p is not None]

        avg_high = round(sum(temps_max) / len(temps_max), 1) if temps_max else None
        avg_low = round(sum(temps_min) / len(temps_min), 1) if temps_min else None
        avg_precip = round(sum(precip) / len(precip), 1) if precip else None

        condition, emoji = _weather_condition(avg_high, avg_precip)

        logger.info(f"Weather fetched for {city_name}: {avg_high}°C high, {condition}.")
        return {
            "avg_high_c": avg_high,
            "avg_low_c": avg_low,
            "avg_precipitation_mm": avg_precip,
            "condition": condition,
            "emoji": emoji,
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed for {city_name}: {e}")
        return {
            "avg_high_c": None,
            "avg_low_c": None,
            "avg_precipitation_mm": None,
            "condition": "Unknown",
            "emoji": "🌍",
        }


def _weather_condition(avg_high: float, avg_precip: float) -> tuple:
    """Derives a human-readable condition and emoji from temperature and precipitation."""
    if avg_high is None:
        return "Unknown", "🌍"
    if avg_high >= 28:
        return ("Hot & Sunny", "☀️") if (avg_precip or 0) < 2 else ("Hot & Humid", "🌤️")
    elif avg_high >= 20:
        return ("Warm & Pleasant", "🌤️") if (avg_precip or 0) < 3 else ("Warm with showers", "🌦️")
    elif avg_high >= 12:
        return ("Mild", "⛅") if (avg_precip or 0) < 4 else ("Cool & Rainy", "🌧️")
    else:
        return ("Cold", "🧥") if (avg_precip or 0) < 3 else ("Cold & Wet", "🌨️")


def enrich_cities(selected_cities: list, cities_data: list, travel_month: int, year: int = 2025) -> dict:
    """
    Fetches live Wikipedia descriptions and Open-Meteo weather data for each
    selected city. All cities are fetched in parallel to reduce wait time.

    Args:
        selected_cities: List of city name strings to enrich.
        cities_data: Full list of city dicts (for lat/lon).
        travel_month: Travel month as integer (1-12).
        year: Historical archive year to use (capped at 2025).

    Returns:
        Dict mapping city name → {description, weather}.
    """
    geo_map = {city["name"]: city.get("geo", {}) for city in cities_data}

    def _fetch(city_name):
        logger.info(f"Fetching live data for {city_name}...")
        geo = geo_map.get(city_name, {})
        lat = geo.get("lat", 48.0)
        lon = geo.get("lon", 16.0)
        wiki = get_wiki_summary(city_name)
        return city_name, {
            "description": wiki["text"],
            "image_url": wiki["image_url"],
            "weather": get_weather_summary(city_name, lat, lon, travel_month, year=year),
        }

    workers = max(len(selected_cities), 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(_fetch, selected_cities))
