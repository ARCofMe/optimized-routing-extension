"""
osm_manager.py

OpenStreetMap / OpenRouteService routing provider.

This version performs ACTUAL route optimization via ORS and then converts the
optimized waypoint order into a Google Maps /dir URL so technicians get a
familiar Maps experience.

Requirements:
    - ORS_API_KEY must be set in your .env
"""

from __future__ import annotations

import os
import logging
from typing import List, Optional
from urllib.parse import quote_plus
import requests

from .base import RouteStop, BaseRoutingManager, ServiceWindow

logger = logging.getLogger(__name__)


class OSMRoutingManager(BaseRoutingManager):
    """
    Real ORS-backed optimization engine.
    It:
        1. Calls ORS optimization API with all stops
        2. Receives the optimized waypoint ordering
        3. Emits a Google Maps /dir URL using the optimized order
    """

    def __init__(
        self,
        origin: Optional[str] = None,
        destination_override: Optional[str] = None,
    ):
        self.origin = origin
        self.destination_override = destination_override
        self._stops: List[RouteStop] = []
        self.ORS_KEY = os.getenv("ORS_API_KEY")

    # --------------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------------

    def add_stops(self, stops: List[RouteStop]) -> None:
        self._stops.extend(stops)
        logger.debug("[ORS] Added %d stops (total=%d)", len(stops), len(self._stops))

    # --------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------

    def _geocode_address(self, address: str) -> Optional[List[float]]:
        """
        Geocode address → [lon, lat] using ORS.
        """
        if not self.ORS_KEY:
            logger.warning("ORS_API_KEY not set — skipping optimization.")
            return None

        try:
            url = "https://api.openrouteservice.org/geocode/search"
            params = {"api_key": self.ORS_KEY, "text": address}
            r = requests.get(url, params=params, timeout=6)

            if not r.ok:
                logger.error("[ORS] Geocode error: %s %s", r.status_code, r.text)
                return None

            j = r.json()
            feats = j.get("features")
            if not feats:
                return None

            coords = feats[0]["geometry"]["coordinates"]  # lon, lat
            return coords

        except Exception as e:
            logger.exception("[ORS] Exception geocoding %s: %s", address, e)
            return None

    def _optimize_order(self, coords: List[List[float]]) -> Optional[List[int]]:
        """
        Call ORS optimization API to get best stop ordering.
        coords is a list of [lon, lat].

        Returns an array of indices in the optimized order.
        """
        if not self.ORS_KEY:
            return None

        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/optimized"
            payload = {"coordinates": coords}

            r = requests.post(
                url,
                json=payload,
                headers={"Authorization": self.ORS_KEY},
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
        if not self._stops:
            raise ValueError("No stops available to generate a route.")

        # 1️⃣ Collect all addresses (origin + stops + optional destination)
        addresses: List[str] = []

        if self.origin:
            addresses.append(self.origin)

        # Honor service windows: AM → ALL_DAY → PM
        priority = {
            ServiceWindow.AM: 0,
            ServiceWindow.ALL_DAY: 1,
            ServiceWindow.PM: 2,
        }
        ordered_stops = sorted(self._stops, key=lambda s: priority[s.window])
        for stop in ordered_stops:
            addresses.append(stop.address)

        if self.destination_override:
            addresses.append(self.destination_override)

        # 2️⃣ Geocode all addresses => coords
        coords = []
        for addr in addresses:
            c = self._geocode_address(addr)
            if c:
                coords.append(c)
            else:
                logger.warning(
                    "[ORS] Could not geocode '%s' — disabling optimization", addr
                )
                coords = []
                break  # fallback mode triggers below

        # 3️⃣ If optimization possible → reorder addresses
        if coords and len(coords) > 2:
            order = self._optimize_order(coords)
            if order:
                logger.info("[ORS] Using optimized waypoint order")
                addresses = [addresses[i] for i in order]
            else:
                logger.warning("[ORS] Optimization failed — using original order")
        else:
            logger.info("[ORS] Optimization skipped")

        # 4️⃣ Convert to Google Maps URL
        encoded = [quote_plus(a) for a in addresses]
        url = "https://www.google.com/maps/dir/" + "/".join(encoded)

        logger.info("[ORS] Built Google Maps URL with optimized order")
        return url
