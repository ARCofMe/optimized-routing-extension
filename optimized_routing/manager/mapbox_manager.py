"""
Mapbox Routing Manager
Provides a GoogleMapsRoutingManager-compatible interface
for generating optimized & clickable Mapbox routing URLs.
"""

import os
import logging
from typing import List
import requests
from .base import RouteStop, ServiceWindow

logger = logging.getLogger(__name__)

MAPBOX_TOKEN = os.getenv("MAPBOX_API_KEY")


class MapboxRoutingManager:
    BASE_URL = "https://api.mapbox.com/optimized-trips/v1/mapbox/driving"
    CLICK_URL = "https://www.mapbox.com/directions"

    def __init__(self, origin: str = None, destination_override: str = None):
        if not MAPBOX_TOKEN:
            raise ValueError("MAPBOX_API_KEY not set in environment")

        self.origin = origin
        self.destination_override = destination_override
        self.stops: List[RouteStop] = []

    # ----------------------------------------------------------------------
    def add_stops(self, stops: List[RouteStop]):
        """Append RouteStop objects into the route list."""
        self.stops.extend(stops)

    # ----------------------------------------------------------------------
    def _geocode(self, address: str) -> tuple:
        """
        Convert human-readable address → (lon, lat)
        """
        try:
            r = requests.get(
                "https://api.mapbox.com/search/geocode/v6/forward",
                params={"q": address, "access_token": MAPBOX_TOKEN},
                timeout=6,
            )
            r.raise_for_status()
            features = r.json().get("features")
            if not features:
                raise ValueError(f"No geocode result for '{address}'")

            coords = features[0]["geometry"]["coordinates"]
            return coords[0], coords[1]  # lon, lat
        except Exception as e:
            logger.error(f"[MAPBOX] Geocode failed for '{address}': {e}")
            return None, None

    # ----------------------------------------------------------------------
    def build_route_url(self) -> str:
        """Generate optimized route using Mapbox Optimization API."""

        if not self.stops:
            raise ValueError("No stops available to generate a route.")

        # Honor service windows: AM → ALL_DAY → PM
        ordered_stops = sorted(self.stops, key=lambda s: s.window.value)
        waypoints = []

        # 1️⃣ Add origin as the first stop
        if self.origin:
            lon, lat = self._geocode(self.origin)
            if lon is not None:
                waypoints.append(f"{lon},{lat}")
        else:
            # use first stop as origin if none given
            first = self.stops[0].address
            lon, lat = self._geocode(first)
            waypoints.append(f"{lon},{lat}")

        # 2️⃣ Add all job stops
        for stop in ordered_stops:
            lon, lat = self._geocode(stop.address)
            if lon is not None:
                waypoints.append(f"{lon},{lat}")

        # 3️⃣ Apply destination override
        if self.destination_override:
            lon, lat = self._geocode(self.destination_override)
            if lon is not None:
                waypoints.append(f"{lon},{lat}")
        else:
            # loop back to origin for round-trip consistency
            if self.origin:
                lon, lat = self._geocode(self.origin)
                if lon is not None:
                    waypoints.append(f"{lon},{lat}")

        coord_string = ";".join(waypoints)

        try:
            r = requests.get(
                f"{self.BASE_URL}/{coord_string}",
                params={
                    "access_token": MAPBOX_TOKEN,
                    "roundtrip": "true",
                    "source": "first",
                    "destination": "last",
                    "overview": "full",
                    "annotations": "distance,duration",
                },
                timeout=8,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error(f"[MAPBOX] Optimization failure: {e}")
            # return a static but still valid viewer link
            return f"{self.CLICK_URL}?coordinates={coord_string}"

        # Extract waypoint order
        waypoints_order = data.get("waypoints", [])
        coords_for_url = []

        # Mapbox returns re-sorted order — follow it
        for wp in waypoints_order:
            lon, lat = wp["location"]
            coords_for_url.append(f"{lon},{lat}")

        # Construct a sharable Mapbox click URL
        viewer_url = f"{self.CLICK_URL}?coordinates=" + ";".join(coords_for_url)
        return viewer_url
