# manager/google_manager.py

from __future__ import annotations
import os
import urllib.parse
import logging
import googlemaps
from dotenv import load_dotenv
from urllib.parse import urlencode, quote_plus
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.cache_manager import CacheManager
from config import RouteConfig
from .base import BaseRoutingManager, RouteStop

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

route_cache = CacheManager("routes", ttl_minutes=60)  # cache per day/hour

class GoogleMapsRoutingManager(BaseRoutingManager):
    """Builds a Google Maps directions URL with ordered waypoints."""

    def __init(self, origin: str, **kwargs):
        super().__init__(origin, **kwargs)
        self.GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.GOOGLE_MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")

        self.gmaps = googlemaps.Client(key=self.GOOGLE_MAPS_API_KEY)
        
        self.mode: str = "driving"
        self.avoid: str = None
        self.use_query_string: bool = False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    def get_optimized_route(self, addresses, config: RouteConfig = RouteConfig()):
        """
        Generate an optimized route order using Google Maps Directions API
        with caching to minimize API calls.
        """
        if len(addresses) < 1:
            raise ValueError("Need at least one job address to optimize.")

        cache_key = f"optimized_{hash(tuple(addresses))}"
        cached = route_cache.get(cache_key)
        if cached:
            logger.info(f"[CACHE] Using cached optimized route ({len(addresses)} stops)")
            return cached

        origin = config.start_location or addresses[0]
        destination = config.end_location or addresses[-1]
        waypoints = (
            addresses[1:-1]
            if not config.start_location and not config.end_location
            else addresses
        )

        logger.info(f"Origin: {origin}, Destination: {destination}")
        logger.info(f"Waypoints: {waypoints}")

        directions_result = self.gmaps.directions(
            origin, destination, waypoints=waypoints, optimize_waypoints=True
        )

        if not directions_result:
            raise RuntimeError("No directions found.")

        waypoint_order = directions_result[0]["waypoint_order"]
        sorted_waypoints = [waypoints[i] for i in waypoint_order]

        result = {
            "origin": origin,
            "destination": destination,
            "waypoints": sorted_waypoints,
            "order": waypoint_order,
        }

        route_cache.set(cache_key, result)
        logger.info(f"[CACHE] Saved optimized route with {len(addresses)} stops")

        return result



    def build_route_url(self) -> str:
        groups = self.grouped_stops()
        if not groups:
            raise ValueError("No stops to route to")

        # flatten sequence but link between groups
        all_stops = []
        for i, group in enumerate(groups):
            if i > 0:
                # start this window at the last stop from the previous window
                all_stops.append(groups[i-1][-1])
            all_stops.extend(group)

        origin = self.origin
        destination = self.origin if self.end_at_origin else all_stops[-1].address
        waypoints = [s.address for s in all_stops]

        params = {
            "origin": origin,
            "destination": destination,
        }

        if self.useQueryStringInURL():
            params["travelmode"] = self.getMode()
            params["waypoints"] = "|".join(waypoints)
            if self.getAvoid():
                params["avoid"] = self.getAvoid()
            query_string = urlencode(params, quote_via=quote_plus)
            return f"https://www.google.com/maps/dir/?{query_string}"

        full_route = [origin] + [s.address for s in all_stops] + [destination]
        encoded = [quote_plus(addr) for addr in full_route]
        return f"https://www.google.com/maps/dir/" + "/".join(encoded)


    def setMode(self, mode: str = "driving"):
        self.mode = mode

    def getMode(self) -> str:
        return self.mode or "driving"

    def setAvoid(self, avoid: str = ""):
        self.avoid = avoid

    def getAvoid(self) -> str|None:
        return self.avoid or None

    def setUseQueryStringInURL(self, use_qs: bool = False):
        self.use_query_string = use_qs

    def useQueryStringInURL(self) -> bool:
        return getattr(self, "use_query_string", False)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    def optimize_within_window(self, stops: list[str], start: str | None = None) -> list[str]:
        if not stops or len(stops) <= 1:
            return stops

        cache_key = ("gmaps_window", tuple(stops))
        cached = get_cached(*cache_key)
        if cached:
            logger.info("[CACHE] Using cached window optimization.")
            return cached

        origin = start or stops[0]
        destination = stops[-1]
        waypoints = [addr for addr in stops if addr not in {origin, destination}]

        directions = self.gmaps.directions(
            origin,
            destination,
            waypoints=waypoints,
            optimize_waypoints=True,
        )

        if not directions:
            logger.warning("No route returned from optimization, preserving given order.")
            return stops

        order = directions[0]["waypoint_order"]
        sorted_waypoints = [waypoints[i] for i in order]
        result = [origin] + sorted_waypoints + [destination]

        set_cached(*cache_key, data=result)
        return result
