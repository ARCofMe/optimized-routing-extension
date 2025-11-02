# routing.py

import os
import googlemaps
import logging
from dotenv import load_dotenv
from urllib.parse import urlencode, quote_plus
from tenacity import retry, stop_after_attempt, wait_exponential
from config import RouteConfig

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
def get_optimized_route(addresses, config: RouteConfig = RouteConfig()):
    """
    Generate an optimized route order using the Google Maps Directions API.

    This function determines the most efficient sequence of waypoints for
    a given list of addresses. It optionally includes a fixed start and/or
    end location based on the provided RouteConfig. The request is retried
    up to three times with exponential backoff if transient API errors occur.

    Args:
        addresses (List[str]):
            A list of address strings representing route stops to be optimized.
        config (RouteConfig, optional):
            A configuration object specifying a custom start and/or end
            location. If not provided, the first address is treated as the
            origin and the last as the destination.

    Returns:
        dict: A dictionary containing:
            - **origin** (str): The starting address.
            - **destination** (str): The final address.
            - **waypoints** (List[str]): Ordered list of intermediate addresses.
            - **order** (List[int]): The order indices of optimized waypoints
              relative to the input list.

    Raises:
        ValueError: If no addresses are provided.
        RuntimeError: If the Google Maps API returns no route results.

    Notes:
        - This method uses exponential backoff retry behavior via the
          `tenacity` library to handle transient network or API errors.
        - Waypoint optimization is handled by the Google Maps Directions API.
    """

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


def build_google_maps_url(
    origin: str,
    destination: str,
    sorted_waypoints: list[str],
    mode: str = "driving",
    avoid: str = None,
    use_query_string: bool = False,
) -> str:
    """
    Construct a Google Maps URL for a route with optional travel preferences.

    This function builds a Google Maps directions URL with support for
    specifying travel mode, avoidance preferences, and the format of the URL.

    Args:
        origin (str): Starting address.
        destination (str): Final address.
        sorted_waypoints (List[str]): Ordered list of intermediate stop addresses.
        mode (str, optional): Travel mode. One of 'driving', 'walking',
            'bicycling', or 'transit'. Defaults to 'driving'.
        avoid (str, optional): Comma-separated values to avoid on the route
            (e.g., 'tolls,highways'). Defaults to None.
        use_query_string (bool, optional): Whether to return a URL with query
            parameters instead of a /dir/ path. Defaults to False.

    Returns:
        str: A complete Google Maps URL for the specified route and preferences.
    """
    if use_query_string:
        params = {"origin": origin, "destination": destination, "travelmode": mode}
        if sorted_waypoints:
            params["waypoints"] = "|".join(sorted_waypoints)
        if avoid:
            params["avoid"] = avoid
        query_string = urlencode(params, quote_via=quote_plus)
        return f"https://www.google.com/maps/dir/?{query_string}"
    else:
        # Path-based version for simplicity/sharing
        full_route = [origin] + sorted_waypoints + [destination]
        encoded = [quote_plus(addr) for addr in full_route]
        return f"https://www.google.com/maps/dir/" + "/".join(encoded)
