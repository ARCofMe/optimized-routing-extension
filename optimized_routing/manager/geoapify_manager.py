"""
Geoapify Routing Manager

Builds technician routes using Geoapify services for geocoding and emits a
shareable, non-Google map URL. This keeps routing off Google Maps APIs while
still producing a clickable set of driving directions.
"""

from __future__ import annotations

import logging
import os
import time
from typing import List, Optional
from urllib.parse import urlencode

import requests

from optimized_routing.manager.base import BaseRoutingManager, RouteStop
from optimized_routing.utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)

# Cache geocode lookups to reduce rate-limit pressure
geocode_cache = CacheManager("geoapify_geocode", ttl_minutes=24 * 60)


class GeoapifyRoutingManager(BaseRoutingManager):
    """Routing manager that leans on Geoapify for lookups."""

    GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
    ROUTE_VIEW_URL = "https://www.openstreetmap.org/directions"

    def __init__(
        self,
        origin: str,
        destination_override: Optional[str] = None,
        end_at_origin: bool = True,
    ):
        super().__init__(origin, destination_override=destination_override, end_at_origin=end_at_origin)

        self.api_key = os.getenv("GEOAPIFY_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEOAPIFY_API_KEY in environment.")

        self.mode = "drive"  # Geoapify routing mode; we translate to OSRM viewer
        self.avoid: Optional[str] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _geocode(self, address: str) -> Optional[tuple[float, float]]:
        """Return (lon, lat) for an address or None on failure."""
        cache_key = address.strip().lower()
        cached = geocode_cache.get(cache_key)
        if cached:
            return tuple(cached)

        attempts = 3
        try:
            for attempt in range(1, attempts + 1):
                params = {
                    "text": address,
                    "limit": 1,
                    "format": "json",
                    "apiKey": self.api_key,
                }
                resp = requests.get(self.GEOCODE_URL, params=params, timeout=6)
                if resp.status_code == 429:
                    logger.warning("[GEOAPIFY] Rate limited on geocode '%s' (attempt %d/%d)", address, attempt, attempts)
                    time.sleep(1.5 * attempt)
                    continue

                resp.raise_for_status()

                data = resp.json()
                result = None
                if isinstance(data, dict):
                    results = data.get("results") or data.get("features")
                    if results:
                        first = results[0]
                        # handle both results list shape and GeoJSON features
                        if "lon" in first and "lat" in first:
                            result = (first["lon"], first["lat"])
                        elif "geometry" in first and first["geometry"].get("coordinates"):
                            lon, lat = first["geometry"]["coordinates"][:2]
                            result = (lon, lat)

                if result:
                    geocode_cache.set(cache_key, list(result))
                    return result

                logger.warning("[GEOAPIFY] No geocode result for '%s' (attempt %d/%d)", address, attempt, attempts)
                time.sleep(0.5 * attempt)

        except Exception as exc:  # pragma: no cover - defensive network guard
            logger.error("[GEOAPIFY] Geocode failed for '%s': %s", address, exc)

        return None

    # ------------------------------------------------------------------
    # Main URL builder
    # ------------------------------------------------------------------
    def build_route_url(self) -> str:
        """
        Build a shareable route URL using Geoapify geocoding and an
        OpenStreetMap OSRM directions link for navigation.
        """
        unique_stops = self.deduplicate_stops()
        self.stops = unique_stops

        if not self.stops:
            raise ValueError("No stops available to generate a route.")

        grouped = self.grouped_stops()

        if len(grouped) > 1:
            ordered_addresses = [s.address for group in grouped for s in group]
        else:
            ordered_addresses = [s.address for s in self.stops]

        origin = self.origin or ordered_addresses[0]
        destination = (
            self.destination_override
            if self.destination_override
            else (self.origin if self.end_at_origin else ordered_addresses[-1])
        )

        full_route: List[str] = [origin] + ordered_addresses
        if destination:
            full_route.append(destination)

        coords: List[tuple[float, float]] = []
        kept_route: List[str] = []
        failed: List[str] = []
        for addr in full_route:
            result = self._geocode(addr)
            if not result:
                logger.warning("[GEOAPIFY] Skipping address (no geocode): %s", addr)
                failed.append(addr)
                continue
            coords.append(result)
            kept_route.append(addr)

        if failed:
            logger.warning(
                "[GEOAPIFY] Skipped %d address(es) that could not be geocoded: %s",
                len(failed),
                "; ".join(failed),
            )

        if len(coords) < 2:
            raise ValueError("Need at least two geocoded waypoints to build a route.")

        # Build an OSM directions URL (avoids exposing the API key in the link).
        route_param = ";".join([f"{lat},{lon}" for lon, lat in coords])
        engine = "fossgis_osrm_car"
        if self.mode in ("walk", "foot"):
            engine = "fossgis_osrm_foot"
        elif self.mode in ("bike", "bicycle"):
            engine = "fossgis_osrm_bike"

        qs = urlencode({"engine": engine, "route": route_param})
        url = f"{self.ROUTE_VIEW_URL}?{qs}"

        logger.info("[GEOAPIFY] Generated OSM directions link with Geoapify geocoding.")
        return url

    # ------------------------------------------------------------------
    # Config accessors for parity
    # ------------------------------------------------------------------
    def set_mode(self, mode: str = "drive"):
        """Set routing mode (drive|walk|bike as supported by Geoapify)."""
        self.mode = mode

    def get_mode(self) -> str:
        return self.mode or "drive"

    def set_avoid(self, avoid: Optional[str] = None):
        """Set avoid preference (e.g., tolls, ferries)."""
        self.avoid = avoid

    def get_avoid(self) -> Optional[str]:
        return self.avoid
