import os
import googlemaps
from dotenv import load_dotenv
from config import RouteConfig

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_optimized_route(addresses, config: RouteConfig = RouteConfig()):
    """
    Generate an optimized route using Google Maps Directions API.

    This function accepts a list of job addresses and an optional RouteConfig
    object defining the technician’s start and/or end location. It returns a 
    dictionary containing the ordered route, based on Google’s optimized waypoint order.

    Args:
        addresses (list[str]):
            A list of address strings representing all jobs for the day.
            Must contain at least one address.
        config (RouteConfig, optional):
            A configuration object specifying start_location and/or end_location.
            If not provided, the first and last addresses in the list are used as
            the origin and destination respectively.

    Raises:
        ValueError: If fewer than one address is provided.
        RuntimeError: If no route data is returned by the Google Maps API.

    Returns:
        dict: A dictionary with the following keys:
            - "origin": str — the route’s starting address
            - "destination": str — the route’s ending address
            - "waypoints": list[str] — addresses in optimized order
            - "order": list[int] — numeric index order of optimized waypoints
    """
    if len(addresses) < 1:
        raise ValueError("Need at least one job address to optimize.")

    origin = config.start_location or addresses[0]
    destination = config.end_location or addresses[-1]

    # Determine which points to treat as waypoints (exclude start/end if configured)
    waypoints = addresses[:]
    if config.start_location:
        waypoints = addresses
    else:
        waypoints = waypoints[1:]
    if config.end_location:
        waypoints = waypoints
    else:
        waypoints = waypoints[:-1]

    directions_result = gmaps.directions(
        origin, destination, waypoints=waypoints, optimize_waypoints=True
    )

    if not directions_result:
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
    """
    Build a shareable Google Maps route URL based on an optimized route.

    This function takes an origin, destination, and list of optimized waypoints,
    then constructs a human-readable URL that opens the route directly in Google Maps.

    Args:
        origin (str): Starting address for the route.
        destination (str): Final address for the route.
        sorted_waypoints (list[str]): List of addresses in optimized order.

    Returns:
        str: A complete Google Maps Directions URL suitable for sharing or opening in a browser.
    """
    full_route = [origin] + sorted_waypoints + [destination]
    encoded = [addr.replace(" ", "+") for addr in full_route]
    return "https://www.google.com/maps/dir/" + "/".join(encoded)
