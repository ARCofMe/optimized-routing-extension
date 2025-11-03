from __future__ import annotations

import urllib.parse

from .base import BaseRoutingManager


class OpenStreetMapRoutingManager(BaseRoutingManager):
    """Builds an OpenStreetMap directions URL.

    NOTE: This uses the public OSM directions frontend and assumes that
    addresses are resolvable by the OSM geocoder.
    """

    def build_route_url(self) -> str:
        ordered = self.ordered_stops()
        if not ordered:
            raise ValueError("No stops to route to")

        # OSM directions URLs typically look like:
        # https://www.openstreetmap.org/directions?from=...&to=...
        # but supporting many waypoints via URL alone is clunky.
        # Here we just encode origin + first/last; extend as needed.
        origin = self.origin
        destination = ordered[-1].address

        params = {
            "engine": "fossgis_osrm_car",
            "route": f"{origin} | {destination}",
        }
        query = urllib.parse.urlencode(params, safe="| ")
        return f"https://www.openstreetmap.org/directions?{query}"
