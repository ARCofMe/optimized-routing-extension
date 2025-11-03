# manager/google_manager.py

from __future__ import annotations
import os
import urllib.parse
import logging
import googlemaps
from dotenv import load_dotenv
from urllib.parse import urlencode, quote_plus
from tenacity import retry, stop_after_attempt, wait_exponential
from config import RouteConfig
from .base import BaseRoutingManager, RouteStop

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleMapsRoutingManager(BaseRoutingManager):
    """Builds a Google Maps directions URL with ordered waypoints."""

    def init(self):
        self.GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.GOOGLE_MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY is not set in the environment.")

        self.gmaps = googlemaps.Client(key=self.GOOGLE_MAPS_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    def get_optimized_route(self, addresses, config: RouteConfig = RouteConfig()):
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

        directions_result = self.gmaps.directions(
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

    def build_route_url(self) -> str:
        ordered = self.ordered_stops()
        if not ordered:
            raise ValueError("No stops to route to")

        origin = self.origin
        destination = self.origin if self.end_at_origin else ordered[-1].address
        waypoints = [s.address for s in ordered]
        if not self.end_at_origin and waypoints:
            waypoints = waypoints[:-1]  # last is destination

        params = {
            #            "api": "1",
            "origin": origin,
            "destination": destination,
        }

        if self.useQueryStringInURL():
            params = {
                "origin": origin,
                "destination": destination,
                "travelmode": self.mode,
            }
            if waypoints:
                params["waypoints"] = "|".join(waypoints)
            if self.avoid:
                params["avoid"] = self.avoid
            query_string = urlencode(params, quote_via=quote_plus)
            return f"https://www.google.com/maps/dir/?{query_string}"
        else:
            # Path-based version for simplicity/sharing
            full_route = [origin] + waypoints + [destination]
            encoded = [quote_plus(addr) for addr in full_route]
            return f"https://www.google.com/maps/dir/" + "/".join(encoded)

    def setMode(self, mode: str = "driving"):
        self.mode = mode

    def getMode(self) -> str:
        return self.mode or "driving"

    def setAvoid(self, avoid: str = None):
        self.avoid = avoid

    def getAvoid(self) -> str:
        return self.avoid or None

    def setUseQueryStringInURL(self, use_qs: bool = False):
        self.use_query_string = use_qs

    def useQueryStringInURL(self) -> bool:
        return self.use_query_string or False
