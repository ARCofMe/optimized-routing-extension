"""
ors_native_manager.py

Produces a *native OpenRouteService sharable map URL* instead of Google Maps.

Flow:
 1. Geocode all addresses → coordinates
 2. Run ORS optimization API to reorder waypoints
 3. Construct https://maps.openrouteservice.org/#/directions/<lon>,<lat>/.../driving-car
"""

import os
import logging
from urllib.parse import quote_plus
from typing import List, Optional
import requests

from .base import RoutingProvider, RouteStop

logger = logging.getLogger(__name__)


class ORSNativeRoutingManager(RoutingProvider):
    def __init__(
        self,
        origin: Optional[str] = None,
        destination_override: Optional[str] = None,
    ):
        self.origin = origin
        self.destination_override = destination_override
        self._stops: List[RouteStop] = []
        self.ORS_KEY = os.getenv("ORS_API_KEY")

    # ----------------------------------------------------------------------
    # Add stops
    # ----------------------------------------------------------------------
    def add_stops(self, stops: List[RouteStop]) -> None:
        self._stops.extend(stops)

    # ----------------------------------------------------------------------
    # Helper: geocode
    # ----------------------------------------------------------------------
    def _geocode(self, addr: str) -> Optional[List[float]]:
        if not self.ORS_KEY:
            logger.warning("[ORS] No API key set — cannot geocode.")
            return None

        try:
            r = requests.get(
                "https://api.openrouteservice.org/geocode/search",
                params={"api_key": self.ORS_KEY, "text": addr},
                timeout=6,
            )
            if not r.ok:
                return None

            feats = r.json().get("features", [])
            if not feats:
                return None

            return feats[0]["geometry"]["coordinates"]
        except Exception:
            return None

    # ----------------------------------------------------------------------
    # Helper: optimize order
    # ----------------------------------------------------------------------
    def _optimize(self, coords: List[List[float]]) -> Optional[List[int]]:
        if not self.ORS_KEY:
            return None

        try:
            r = requests.post(
                "https://api.openrouteservice.org/v2/directions/driving-car/optimized",
                json={"coordinates": coords},
                headers={"Authorization": self.ORS_KEY},
                timeout=10,
            )
            if not r.ok:
                return None

            return r.json().get("properties", {}).get("way_points_order")
        except Exception:
            return None

    # ----------------------------------------------------------------------
    # Main route builder
    # ----------------------------------------------------------------------
    def build_route_url(self) -> str:
        if not self._stops:
            raise ValueError("No stops available to generate a route.")

        # 1️⃣ Build full address list
        addresses = []
        if self.origin:
            addresses.append(self.origin)
        for stop in self._stops:
            addresses.append(stop.address)
        if self.destination_override:
            addresses.append(self.destination_override)

        # 2️⃣ Geocode all addresses
        coords: List[List[float]] = []
        for addr in addresses:
            c = self._geocode(addr)
            if not c:
                raise ValueError(f"Could not geocode: {addr}")
            coords.append(c)

        # 3️⃣ Try optimization
        order = self._optimize(coords)
        if order:
            coords = [coords[i] for i in order]
        else:
            logger.warning("[ORS] Optimization failed, using original order.")

        # 4️⃣ Construct ORS shareable URL
        coord_str = "/".join([f"{c[0]},{c[1]}" for c in coords])

        url = f"https://maps.openrouteservice.org/#/directions/{coord_str}/driving-car"

        logger.info("[ORS-NATIVE] Built ORS-native URL.")
        return url
