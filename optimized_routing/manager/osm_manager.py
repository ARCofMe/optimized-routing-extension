"""OpenStreetMap routing manager with optional ORS optimization."""

from __future__ import annotations

import logging
from typing import List, Optional
import requests

from .base import RouteStop, BaseRoutingManager

logger = logging.getLogger(__name__)


class OSMRoutingManager(BaseRoutingManager):
    """
    OpenStreetMap/OSRM-backed route builder with optional ORS optimization.
    """

    def __init__(
        self,
        origin: Optional[str] = None,
        destination_override: Optional[str] = None,
    ):
        super().__init__(origin or "", destination_override=destination_override)
        import os

        self.ors_key = os.getenv("ORS_API_KEY")
        self.nominatim_url = os.getenv("OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
        self.osrm_view_url = "https://map.project-osrm.org/"

    # --------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------

    def _geocode_address(self, address: str) -> Optional[List[float]]:
        """
        Geocode address to `[lon, lat]`, preferring Nominatim and falling back to ORS.
        """
        try:
            r = requests.get(
                self.nominatim_url,
                params={"q": address, "format": "jsonv2", "limit": 1},
                headers={"User-Agent": "optimized-routing-extension/1.1"},
                timeout=6,
            )
            if r.ok:
                matches = r.json()
                if matches:
                    first = matches[0]
                    return [float(first["lon"]), float(first["lat"])]
        except Exception as e:
            logger.warning("[OSM] Nominatim geocode failed for %s: %s", address, e)

        if not self.ors_key:
            return None

        try:
            r = requests.get(
                "https://api.openrouteservice.org/geocode/search",
                params={"api_key": self.ors_key, "text": address},
                timeout=6,
            )
            if not r.ok:
                logger.error("[ORS] Geocode error: %s %s", r.status_code, r.text)
                return None
            feats = r.json().get("features")
            if feats:
                return feats[0]["geometry"]["coordinates"]
        except Exception as e:
            logger.exception("[ORS] Exception geocoding %s: %s", address, e)
        return None

    def _optimize_order(self, coords: List[List[float]]) -> Optional[List[int]]:
        """
        Call ORS optimization API to get best stop ordering.
        coords is a list of [lon, lat].

        Returns an array of indices in the optimized order.
        """
        if not self.ors_key:
            return None

        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/optimized"
            payload = {"coordinates": coords}

            r = requests.post(
                url,
                json=payload,
                headers={"Authorization": self.ors_key},
                timeout=10,
            )

            if not r.ok:
                logger.error("[ORS] Optimization error: %s %s", r.status_code, r.text)
                return None

            j = r.json()
            order = j.get("properties", {}).get("way_points_order")
            return order

        except Exception as e:
            logger.exception("[ORS] Exception in optimization: %s", e)
            return None

    # --------------------------------------------------------------------
    # Main route builder
    # --------------------------------------------------------------------

    def build_route_url(self) -> str:
        if not self.stops:
            raise ValueError("No stops available to generate a route.")

        self.stops = self.deduplicate_stops()
        ordered_stops = self.ordered_stops()
        origin = self.origin
        route_stops = list(ordered_stops)
        if not origin:
            origin = route_stops[0].address
            route_stops = route_stops[1:]

        routed_points: list[tuple[str, list[float]]] = []
        origin_coords = self._geocode_address(origin)
        if not origin_coords:
            raise ValueError(f"Could not geocode origin '{origin}' for OSM routing.")
        routed_points.append((origin, origin_coords))

        for stop in route_stops:
            coords = self._geocode_address(stop.address)
            if coords:
                routed_points.append((stop.address, coords))
            else:
                logger.warning("[OSM] Skipping address with no geocode: %s", stop.address)

        if self.destination_override:
            destination_coords = self._geocode_address(self.destination_override)
            if destination_coords:
                routed_points.append((self.destination_override, destination_coords))
            else:
                logger.warning("[OSM] Destination geocode failed: %s", self.destination_override)
        else:
            routed_points.append((origin, origin_coords))

        if len(routed_points) < 2:
            raise ValueError("Could not geocode enough locations to build an OSM route.")

        coords = [point for _, point in routed_points]
        if len(coords) > 2:
            order = self._optimize_order(coords)
            if order:
                logger.info("[ORS] Using optimized waypoint order")
                routed_points = [routed_points[i] for i in order]
            else:
                logger.warning("[ORS] Optimization failed — using original order")
        else:
            logger.info("[ORS] Optimization skipped")

        loc_params = "&".join(
            f"loc={lat},{lon}"
            for _, (lon, lat) in routed_points
        )
        logger.info("[OSM] Built OSRM map URL with %d routed points", len(routed_points))
        return f"{self.osrm_view_url}?{loc_params}"
