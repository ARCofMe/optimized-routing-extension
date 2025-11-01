import os
import googlemaps
from dotenv import load_dotenv


load_dotenv()


GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")


gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def get_optimized_route(addresses):
    if len(addresses) < 2:
        raise ValueError("Need at least an origin and destination.")


    origin = addresses[0]
    destination = addresses[-1]
    waypoints = addresses[1:-1]


    directions_result = gmaps.directions(
        origin,
        destination,
        waypoints=waypoints,
        optimize_waypoints=True
    )


    if not directions_result:
        raise RuntimeError("No directions found.")


    waypoint_order = directions_result[0]['waypoint_order']
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
