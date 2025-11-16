"""
manager/google_manager.py

Implements the Google Maps–based routing manager.

This class builds optimized routes and Google Maps URLs for technicians
based on their job stops and time windows.

Features:
    - Integration with the Google Maps Directions API
    - Stop deduplication (via BaseRoutingManager)
    - Cached route optimization to reduce API usage
    - Configurable travel mode and avoidance preferences
"""

from __future__ import annotations

import os
import urllib.parse
import logging
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv
import googlemaps
from tenacity import retry, stop_after_attempt, wait_exponential

from optimized_routing.utils.cache_manager import CacheManager
from optimized_routing.config import RouteConfig
from optimized_routing.manager.base import BaseRoutingManager, RouteStop

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()
logger = logging.getLogger(__name__)

# Cache route results for 1 hour by default
route_cache = CacheManager("routes", ttl_minutes=60)


# ---------------------------------------------------------------------------
# CLASS: GoogleMapsRoutingManager
# ---------------------------------------------------------------------------


class GoogleMapsRoutingManager(BaseRoutingManager):
    """
    Routing manager for Google Maps.

    Responsibilities:
        - Generate Google Maps URLs from structured route data
        - Optimize stop order using Google Maps Directions API
        - Cache optimization results to reduce API calls
    """

    def __init__(self, origin: str, **kwargs):
        """
        Initialize the routing manager.

        Args:
            origin (str): Starting address for the route.
            **kwargs: Additional options like `end_at_origin`.
        """
        super().__init__(origin, **kwargs)

        self.GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.GOOGLE_MAPS_API_KEY:
            raise ValueError("Missing GOOGLE_MAPS_API_KEY in environment.")

        self.gmaps = googlemaps.Client(key=self.GOOGLE_MAPS_API_KEY)

        self.mode: str = "driving"
        self.avoid: str | None = None
        self.use_query_string: bool = False

    # -----------------------------------------------------------------------
    # Optimization
    # -----------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    def get_optimized_route(
        self, addresses: list[str], config: RouteConfig = RouteConfig()
    ) -> dict:
        """
        Generate an optimized stop order using the Google Maps Directions API,
        caching results to avoid repeated API calls.

        Args:
            addresses (list[str]): List of addresses to optimize.
            config (RouteConfig): Route settings (start, end, etc.).

        Returns:
            dict: Ordered route data with origin, destination, and sorted waypoints.
        """
        if len(addresses) < 1:
            raise ValueError("Need at least one job address to optimize.")

        cache_key = f"optimized_{hash(tuple(addresses))}"
        cached = route_cache.get(cache_key)
        if cached:
            logger.info(
                f"[CACHE] Using cached optimized route ({len(addresses)} stops)"
            )
            return cached

        origin = config.start_location or addresses[0]
        destination = config.end_location or addresses[-1]
        waypoints = (
            addresses[1:-1]
            if not config.start_location and not config.end_location
            else addresses
        )

        logger.info(
            f"[GMAPS] Optimizing route → Origin: {origin}, Destination: {destination}"
        )

        directions_result = self.gmaps.directions(
            origin,
            destination,
            waypoints=waypoints,
            optimize_waypoints=True,
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

    # -----------------------------------------------------------------------
    # Route URL Generation
    # -----------------------------------------------------------------------
    def build_route_url(self) -> str:
        """
        Build a shareable Google Maps Directions URL with the technician’s
        origin and an optimized job order.

        Notes:
        - If multiple service windows are present, segments are optimized per-window
          and concatenated in window order (AM → ALL_DAY → PM) to honor timing.
        - If only one window is present, full-route optimization is attempted.
        """
        # 1) De-duplicate the stops (removes any AM/PM duplicate SRs, etc.)
        unique_stops = self.deduplicate_stops()
        self.stops = unique_stops  # keep consistent for future calls

        if not self.stops:
            raise ValueError("No stops available to generate a route.")

        grouped = self.grouped_stops()

        # If we have multiple windows, optimize each window independently and concatenate
        if len(grouped) > 1:
            logger.info(
                f"[ROUTING] Enforcing service windows across {len(grouped)} segments."
            )
            addresses: list[str] = []
            for group in grouped:
                seg = [s.address for s in group]
                try:
                    seg = self.optimize_within_window(seg, start=seg[0])
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning(f"[ROUTING] Window optimize failed, using raw order: {e}")
                addresses.extend(seg)

            origin = self.origin or addresses[0]
            if self.destination_override:
                destination = self.destination_override
            else:
                destination = self.origin if self.end_at_origin else addresses[-1]
            waypoints = addresses

        else:
            # Single window → allow full-route optimization
            addresses = [s.address for s in self.stops]
            try:
                cfg = RouteConfig()
                cfg.start_location = self.origin
                if self.destination_override:
                    cfg.end_location = self.destination_override
                elif self.end_at_origin:
                    cfg.end_location = self.origin
                else:
                    cfg.end_location = addresses[-1]

                optimized = self.get_optimized_route(addresses, config=cfg)
                origin = optimized["origin"]
                destination = optimized["destination"]
                waypoints = optimized["waypoints"]
            except Exception as e:
                logger.warning(
                    f"[ROUTING] Optimization failed, using raw order instead: {e}"
                )
                origin = self.origin
                if self.destination_override:
                    destination = self.destination_override
                else:
                    destination = self.origin if self.end_at_origin else addresses[-1]
                waypoints = addresses

        # 3) Build the URL in either query-string or path style
        if self.use_query_string:
            params = {
                "origin": origin,
                "destination": destination,
                "travelmode": self.mode,
                "waypoints": "|".join(waypoints),
            }
            if self.avoid:
                params["avoid"] = self.avoid

            query_string = urlencode(params, quote_via=quote_plus)
            url = f"https://www.google.com/maps/dir/?{query_string}"
            logger.debug(f"[ROUTING] Generated route QS URL: {url}")
            return url

        # Default: path-style URL (/dir/ORIGIN/STOP1/.../DEST)
        full_route = [origin] + waypoints + [destination]
        encoded = [quote_plus(addr) for addr in full_route]
        url = "https://www.google.com/maps/dir/" + "/".join(encoded)
        logger.debug(f"[ROUTING] Generated route URL: {url}")
        return url

    # -----------------------------------------------------------------------
    # Config Accessors
    # -----------------------------------------------------------------------

    def setMode(self, mode: str = "driving"):
        """Set the route mode (e.g., driving, walking, bicycling)."""
        self.mode = mode

    def getMode(self) -> str:
        """Get the currently active travel mode."""
        return self.mode or "driving"

    def setAvoid(self, avoid: str = ""):
        """Set avoidance preferences (e.g., tolls, highways)."""
        self.avoid = avoid

    def getAvoid(self) -> str | None:
        """Return the avoid preference, if any."""
        return self.avoid or None

    def setUseQueryStringInURL(self, use_qs: bool = False):
        """Enable query-string-style URLs (for debugging or API sharing)."""
        self.use_query_string = use_qs

    def useQueryStringInURL(self) -> bool:
        """Check if query-string-style URLs are enabled."""
        return getattr(self, "use_query_string", False)

    # -----------------------------------------------------------------------
    # Window Optimization (Optional granular optimizer)
    # -----------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
    def optimize_within_window(
        self, stops: list[str], start: str | None = None
    ) -> list[str]:
        """
        Optimize a subset of stops (e.g., all AM or PM jobs) for better intra-window ordering.

        Args:
            stops (list[str]): Addresses to optimize.
            start (str | None): Optional override for start address.

        Returns:
            list[str]: Ordered list of optimized stop addresses.
        """
        if not stops or len(stops) <= 1:
            return stops

        cache_key = f"gmaps_window_{hash(tuple(stops))}"
        cached = route_cache.get(cache_key)
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
            logger.warning(
                "No route returned from optimization; preserving original order."
            )
            return stops

        order = directions[0]["waypoint_order"]
        sorted_waypoints = [waypoints[i] for i in order]
        result = [origin] + sorted_waypoints + [destination]

        route_cache.set(cache_key, result)
        logger.info(f"[CACHE] Saved optimized window with {len(stops)} stops")

        return result
