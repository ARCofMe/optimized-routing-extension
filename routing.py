import os
import googlemaps
import logging
from dotenv import load_dotenv
from config import RouteConfig
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def get_optimized_route(addresses, config: RouteConfig = RouteConfig()):
    if len(addresses) < 1:
        raise ValueError("Need at least one job address to optimize.")

    origin = config.start_location or addresses[0]
    destination = config.end_location or addresses[-1]
    waypoints = (
        addresses[1:-1]
        if not config.start_location and not config.end_location
        else addresses
    )

    logger.info(f"Origin: {origin}, Destination: {destination}")
    logger.info(f"Waypoints: {waypoints}")

    directions_result = gmaps.directions(
        origin, destination, waypoints=waypoints, optimize_waypoints=True
    )

    if not directions_result:
        logger.error("No directions returned by API")
        raise RuntimeError("No directions found.")

    waypoint_order = directions_result[0]["waypoint_order"]
    sorted_waypoints = [waypoints[i] for i in waypoint_order]

    return {
        "origin": origin,
        "destination": destination,
        "waypoints": sorted_waypoints,
        "order": waypoint_order,
    }


def build_google_maps_url(origin, destination, sorted_waypoints):
    full_route = [origin] + sorted_waypoints + [destination]
    encoded = [addr.replace(" ", "+") for addr in full_route]
    return "https://www.google.com/maps/dir/" + "/".join(encoded)
