import json
import logging
import math
from pathlib import Path

from tools.seasonality import get_month_multiplier

logger = logging.getLogger(__name__)

STYLE_MULTIPLIERS = {
    "backpacker": 0.85,
    "mid_range": 1.0,
    "luxury": 1.35,
}

PRIORITY_WEIGHTS = {
    "cheapest": {"price": 0.85, "time": 0.15, "changes": 0.0},
    "fastest": {"price": 0.15, "time": 0.85, "changes": 0.0},
    "best_balance": {"price": 0.50, "time": 0.35, "changes": 0.15},
}

DEFAULT_MODES = ["flight", "train", "bus"]

# ── Geographic constraints ─────────────────────────────────────────────────────

# Cities on islands with no surface link to mainland Europe — flights only.
FLIGHT_ONLY_CITIES = {"Reykjavik", "Valletta", "Santorini"}

# Cities in the British Isles, separated from continental Europe by the
# English Channel / Irish Sea. Buses cannot cross; trains only via Eurostar.
BRITISH_ISLES_CITIES = {"London", "Manchester", "Edinburgh", "Glasgow", "Dublin"}

# The only train routes that cross the Channel Tunnel (Eurostar service).
# All other British Isles ↔ mainland routes require a flight.
EUROSTAR_PAIRS = {
    frozenset({"London", "Paris"}),
    frozenset({"London", "Brussels"}),
    frozenset({"London", "Amsterdam"}),
}

# Cities north of the Alps (bus/train routes crossing to southern cities are
# slower due to mountain passes and tunnels — apply a time penalty).
_NORTH_OF_ALPS = {
    "Paris", "Munich", "Vienna", "Berlin", "Prague", "Zurich", "Geneva",
    "Brussels", "Amsterdam", "Copenhagen", "Stockholm", "Oslo", "Helsinki",
    "Warsaw", "Krakow", "Budapest", "Bratislava", "Tallinn", "Riga", "Vilnius",
    "Ljubljana", "Hamburg",
}
_SOUTH_OF_ALPS = {"Milan", "Venice", "Florence", "Rome", "Nice", "Dubrovnik", "Split"}

# Cities north of the Pyrenees (routes to/from Spain are longer due to mountain passes).
_NORTH_OF_PYRENEES = {"Paris", "Brussels", "Amsterdam", "Lyon"}
_SOUTH_OF_PYRENEES = {"Barcelona", "Madrid", "Seville", "Valencia", "Bilbao", "Malaga"}


def _feasible_modes(origin: str, destination: str, requested_modes: list) -> list:
    """Remove transport modes that are geographically impossible for this route.

    Rules:
    - Island cities (Iceland, Malta, Santorini): flight only.
    - British Isles ↔ mainland: no bus; train only if Eurostar route.
    - All other routes: all requested modes remain available.
    """
    if origin in FLIGHT_ONLY_CITIES or destination in FLIGHT_ONLY_CITIES:
        return ["flight"] if "flight" in requested_modes else ["flight"]

    origin_british = origin in BRITISH_ISLES_CITIES
    dest_british = destination in BRITISH_ISLES_CITIES
    if origin_british != dest_british:  # one side is British Isles, other is mainland
        modes = [m for m in requested_modes if m != "bus"]
        pair = frozenset({origin, destination})
        if pair not in EUROSTAR_PAIRS:
            modes = [m for m in modes if m != "train"]
        return modes or ["flight"]

    return requested_modes


def _mountain_time_multiplier(origin: str, destination: str) -> float:
    """Return a surface-travel time multiplier for routes crossing mountain ranges.

    Tunnels and passes exist, so these routes are possible — just slower.
    Applied only to bus and train, not flights.
    """
    multiplier = 1.0
    crosses_alps = (origin in _NORTH_OF_ALPS and destination in _SOUTH_OF_ALPS) or \
                   (origin in _SOUTH_OF_ALPS and destination in _NORTH_OF_ALPS)
    crosses_pyrenees = (origin in _NORTH_OF_PYRENEES and destination in _SOUTH_OF_PYRENEES) or \
                       (origin in _SOUTH_OF_PYRENEES and destination in _NORTH_OF_PYRENEES)
    if crosses_alps:
        multiplier *= 1.30  # alpine tunnels add ~30% to surface travel time
    if crosses_pyrenees:
        multiplier *= 1.20  # mountain passes add ~20%
    return multiplier

KNOWN_DEPARTURE_COORDS = {
    "london": {"lat": 51.5072, "lon": -0.1276},
    "dublin": {"lat": 53.3498, "lon": -6.2603},
    "manchester": {"lat": 53.4808, "lon": -2.2426},
    "edinburgh": {"lat": 55.9533, "lon": -3.1883},
    "new york": {"lat": 40.7128, "lon": -74.0060},
    "toronto": {"lat": 43.6532, "lon": -79.3832},
    "chicago": {"lat": 41.8781, "lon": -87.6298},
    "los angeles": {"lat": 34.0522, "lon": -118.2437},
    "miami": {"lat": 25.7617, "lon": -80.1918},
}


def _load_city_coordinates() -> dict:
    """Load known coordinates from the seed data with an empty fallback."""
    seed_path = Path(__file__).parent.parent / "data" / "european_cities_seed.json"
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            seed_cities = json.load(f)
        return {
            city["name"].lower(): {"lat": city["lat"], "lon": city["lon"]}
            for city in seed_cities
            if "lat" in city and "lon" in city
        }
    except Exception as e:
        logger.warning(f"Could not load coordinates for transport estimates: {e}")
        return {}


def _coordinates_for(city: str, coord_map: dict) -> dict:
    """Return coordinates for a city, falling back to central Europe."""
    city_key = city.lower().strip()
    return coord_map.get(city_key) or KNOWN_DEPARTURE_COORDS.get(city_key) or {"lat": 48.2082, "lon": 16.3738}


def _distance_km(origin: dict, destination: dict) -> float:
    """Calculate great-circle distance between two coordinate points."""
    radius_km = 6371.0
    lat1 = math.radians(origin["lat"])
    lon1 = math.radians(origin["lon"])
    lat2 = math.radians(destination["lat"])
    lon2 = math.radians(destination["lon"])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _mode_options(
    distance_km: float,
    travel_month: int,
    travel_style: str,
    modes: list,
    directness: str,
    mountain_multiplier: float = 1.0,
) -> list:
    """Generate feasible transport options for one route leg.

    mountain_multiplier is applied to bus and train travel times only,
    reflecting slower speeds through alpine tunnels and mountain passes.
    """
    multiplier = get_month_multiplier(travel_month)
    style_multiplier = STYLE_MULTIPLIERS.get(travel_style, 1.0)
    allow_connections = directness != "direct_only"
    options = []

    if "flight" in modes and distance_km >= 180:
        direct_cost = (45 + distance_km * 0.11) * multiplier * style_multiplier
        direct_hours = 3.0 + distance_km / 760
        options.append({
            "mode": "flight",
            "cost_eur": round(direct_cost),
            "duration_hours": round(direct_hours, 1),
            "direct": True,
            "changes": 0,
        })
        if allow_connections and distance_km >= 500:
            options.append({
                "mode": "flight",
                "cost_eur": round(direct_cost * 0.82),
                "duration_hours": round(direct_hours + 2.4, 1),
                "direct": False,
                "changes": 1,
            })

    if "train" in modes and distance_km <= 1400:
        direct_available = distance_km <= 650
        train_cost = (18 + distance_km * 0.16) * (0.80 + multiplier * 0.20) * style_multiplier
        train_hours = (0.6 + distance_km / 145) * mountain_multiplier
        if direct_available or allow_connections:
            options.append({
                "mode": "train",
                "cost_eur": round(train_cost if direct_available else train_cost * 0.92),
                "duration_hours": round(train_hours if direct_available else train_hours + 1.6, 1),
                "direct": direct_available,
                "changes": 0 if direct_available else 1,
            })

    if "bus" in modes and distance_km <= 1700:
        direct_available = distance_km <= 900
        bus_cost = (12 + distance_km * 0.07) * (0.90 + multiplier * 0.10) * max(0.75, style_multiplier - 0.15)
        bus_hours = (1.0 + distance_km / 78) * mountain_multiplier
        if direct_available or allow_connections:
            options.append({
                "mode": "bus",
                "cost_eur": round(bus_cost if direct_available else bus_cost * 0.88),
                "duration_hours": round(bus_hours if direct_available else bus_hours + 2.0, 1),
                "direct": direct_available,
                "changes": 0 if direct_available else 1,
            })

    return options


def _score_options(options: list, route_priority: str) -> list:
    """Attach a normalized score to each option and return sorted choices."""
    if not options:
        return []

    weights = PRIORITY_WEIGHTS.get(route_priority, PRIORITY_WEIGHTS["best_balance"])
    min_cost = min(option["cost_eur"] for option in options)
    max_cost = max(option["cost_eur"] for option in options)
    min_hours = min(option["duration_hours"] for option in options)
    max_hours = max(option["duration_hours"] for option in options)
    max_changes = max(option["changes"] for option in options) or 1

    for option in options:
        cost_range = max_cost - min_cost or 1
        time_range = max_hours - min_hours or 1
        price_score = (option["cost_eur"] - min_cost) / cost_range
        time_score = (option["duration_hours"] - min_hours) / time_range
        changes_score = option["changes"] / max_changes
        option["score"] = round(
            weights["price"] * price_score
            + weights["time"] * time_score
            + weights["changes"] * changes_score,
            4,
        )

    return sorted(options, key=lambda option: (option["score"], option["cost_eur"], option["duration_hours"]))


def estimate_transport(
    departure_city: str,
    destinations: list,
    travel_month: int,
    travel_style: str = "mid_range",
    return_city: str = None,
    transport_modes: list = None,
    route_priority: str = "best_balance",
    directness: str = "allow_connections",
) -> dict:
    """
    Estimate the best transport option for each leg across flights, trains, and buses.

    This is a free, no-key estimator based on city distance, seasonality, travel
    style, directness preference, and route priority. It does not call live booking
    APIs.
    """
    return_city = return_city or departure_city
    modes = transport_modes or DEFAULT_MODES
    coord_map = _load_city_coordinates()
    route = [departure_city] + destinations + [return_city]

    selected_legs = []
    total_cost = 0.0
    total_hours = 0.0

    if len(route) < 2:
        return {
            "transport_legs": [],
            "flight_legs": [],
            "total_transport_cost": 0.0,
            "total_flights_cost": 0.0,
            "total_duration_hours": 0.0,
        }

    for index in range(len(route) - 1):
        origin = route[index]
        destination = route[index + 1]
        origin_geo = _coordinates_for(origin, coord_map)
        destination_geo = _coordinates_for(destination, coord_map)
        distance = _distance_km(origin_geo, destination_geo)
        viable_modes = _feasible_modes(origin, destination, modes)
        mt_mult = _mountain_time_multiplier(origin, destination)
        options = _score_options(
            _mode_options(distance, travel_month, travel_style, viable_modes, directness, mt_mult),
            route_priority,
        )

        if not options:
            logger.warning(f"No transport options for {origin} to {destination}; using fallback flight.")
            options = [{
                "mode": "flight",
                "cost_eur": round((80 + distance * 0.12) * get_month_multiplier(travel_month)),
                "duration_hours": round(3.0 + distance / 720, 1),
                "direct": True,
                "changes": 0,
                "score": 1.0,
            }]

        best = options[0]
        leg_type = "outbound" if index == 0 else "inbound" if index == len(route) - 2 else "inter_city"
        leg = {
            "from": origin,
            "to": destination,
            "type": leg_type,
            "mode": best["mode"],
            "cost_eur": best["cost_eur"],
            "duration_hours": best["duration_hours"],
            "direct": best["direct"],
            "changes": best["changes"],
            "distance_km": round(distance),
            "alternatives": options[1:3],
        }
        selected_legs.append(leg)
        total_cost += best["cost_eur"]
        total_hours += best["duration_hours"]

    return {
        "transport_legs": selected_legs,
        "flight_legs": selected_legs,
        "total_transport_cost": total_cost,
        "total_flights_cost": total_cost,
        "total_duration_hours": round(total_hours, 1),
        "route_priority": route_priority,
        "directness": directness,
        "transport_modes": modes,
        "return_city": return_city,
    }
