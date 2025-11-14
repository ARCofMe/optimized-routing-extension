"""
manager/osm_manager.py

Implements a lightweight OpenStreetMap routing manager.

This manager builds simple shareable OpenStreetMap URLs
using origin and destination data. Currently, this does not
perform optimization — it’s mainly for basic route visualization.
"""

from __future__ import annotations
import urllib.parse
import logging

from optimized_routing.manager.base import BaseRoutingManager

logger = logging.getLogger(__name__)


class OpenStreetMapRoutingManager(BaseRoutingManager):
    """
    Build a basic OpenStreetMap directions URL.

    Notes:
        - Uses the public OSM frontend.
        - Best for visual debugging or open-source-friendly integrations.
        - Does not optimize waypoint order.
    """

    def build_route_url(self) -> str:
        """
        Construct a basic OSM directions URL from the origin to the last stop.

        Example:
            https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=Origin|Destination

        Returns:
            str: The OSM directions URL.

        Raises:
            ValueError: If no stops are available to route.
        """
        ordered = self.ordered_stops()
        if not ordered:
            raise ValueError("No stops to route to")

        origin = self.origin
        destination = ordered[-1].address

        params = {
            "engine": "fossgis_osrm_car",
            "route": f"{origin} | {destination}",
        }

        query = urllib.parse.urlencode(params, safe="| ")
        url = f"https://www.openstreetmap.org/directions?{query}"

        logger.info(f"[OSM] Generated route URL: {url}")
        return url
