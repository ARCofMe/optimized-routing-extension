"""Mapbox routing manager with deduplication and fallback viewer URLs."""

from __future__ import annotations

import logging
from typing import List
import requests
from .base import BaseRoutingManager, RouteStop

logger = logging.getLogger(__name__)


class MapboxRoutingManager(BaseRoutingManager):
    BASE_URL = "https://api.mapbox.com/optimized-trips/v1/mapbox/driving"
    CLICK_URL = "https://www.mapbox.com/directions"

    def __init__(self, origin: str = None, destination_override: str = None):
        super().__init__(origin or "", destination_override=destination_override)
        from optimized_routing.config import settings

        self.api_token = settings.mapbox_api_key
        if not self.api_token:
            raise ValueError("MAPBOX_API_KEY not set in environment")

    # ----------------------------------------------------------------------
    def _geocode(self, address: str) -> tuple[float | None, float | None]:
        """Convert human-readable address to `(lon, lat)`."""
        try:
            r = requests.get(
                "https://api.mapbox.com/search/geocode/v6/forward",
                params={"q": address, "access_token": self.api_token},
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
        """Generate optimized route using Mapbox optimization with stable fallbacks."""

        if not self.stops:
            raise ValueError("No stops available to generate a route.")

        self.stops = self.deduplicate_stops()
        ordered_stops = self.ordered_stops()
        origin = self.origin
        route_stops = list(ordered_stops)
        if not origin:
            origin = route_stops[0].address
            route_stops = route_stops[1:]

        waypoints: list[str] = []
        lon, lat = self._geocode(origin)
        if lon is None:
            raise ValueError(f"Could not geocode origin '{origin}' via Mapbox.")
        waypoints.append(f"{lon},{lat}")

        for stop in route_stops:
            lon, lat = self._geocode(stop.address)
            if lon is not None:
                waypoints.append(f"{lon},{lat}")
            else:
                logger.warning("[MAPBOX] Skipping address with no geocode: %s", stop.address)

        if self.destination_override:
            lon, lat = self._geocode(self.destination_override)
            if lon is not None:
                waypoints.append(f"{lon},{lat}")
            else:
                logger.warning("[MAPBOX] Destination geocode failed: %s", self.destination_override)
        else:
            waypoints.append(waypoints[0])

        if len(waypoints) < 2:
            raise ValueError("Could not geocode enough locations to build a Mapbox route.")

        coord_string = ";".join(waypoints)

        try:
            r = requests.get(
                f"{self.BASE_URL}/{coord_string}",
                params={
                    "access_token": self.api_token,
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

        waypoints_order = data.get("waypoints", [])
        coords_for_url = []

        if not waypoints_order:
            return f"{self.CLICK_URL}?coordinates={coord_string}"

        for wp in waypoints_order:
            lon, lat = wp.get("location", [None, None])
            if lon is None:
                continue
            coords_for_url.append(f"{lon},{lat}")

        if not coords_for_url:
            return f"{self.CLICK_URL}?coordinates={coord_string}"

        viewer_url = f"{self.CLICK_URL}?coordinates=" + ";".join(coords_for_url)
        return viewer_url
