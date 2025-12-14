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
from optimized_routing.config import settings

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

    def _optimize_order_geoapify(self, coords: List[tuple[float, float]]) -> Optional[List[int]]:
        """
        Try to optimize waypoint order using Geoapify's route matrix (simple heuristic).
        Returns an index list or None on failure. This keeps us on Geoapify and avoids
        public OSRM dependencies.
        """
        if len(coords) < 3 or not self.api_key:
            return None

        attempts = 2
        url = "https://api.geoapify.com/v1/routematrix"
        for attempt in range(1, attempts + 1):
            try:
                payload = {
                    "mode": self.mode or "drive",
                    "sources": coords,
                    "targets": coords,
                }
                resp = requests.post(
                    url,
                    params={"apiKey": self.api_key},
                    json=payload,
                    timeout=8 * attempt,
                )
                if not resp.ok:
                    logger.warning(
                        "[GEOAPIFY] Matrix failed (%d/%d): %s %s",
                        attempt,
                        attempts,
                        resp.status_code,
                        resp.text[:120],
                    )
                    time.sleep(1.0 * attempt)
                    continue

                data = resp.json()
                matrix = data.get("times") or data.get("distances")
                if not matrix:
                    return None

                n = len(coords)
                visited = {0}
                order = [0]
                current = 0
                # simple nearest-neighbor heuristic
                while len(order) < n:
                    best = None
                    best_cost = float("inf")
                    for idx in range(n):
                        if idx in visited:
                            continue
                        cost = matrix[current][idx]
                        if cost is None:
                            continue
                        if cost < best_cost:
                            best_cost = cost
                            best = idx
                    if best is None:
                        break
                    visited.add(best)
                    order.append(best)
                    current = best

                if len(order) == n:
                    logger.info("[GEOAPIFY] Optimized %d stops via routematrix", n)
                    return order
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("[GEOAPIFY] Matrix optimization exception (%d/%d): %s", attempt, attempts, exc)
                time.sleep(1.0 * attempt)

        return None

    def _optimize_order_osrm(self, coords: List[tuple[float, float]]) -> Optional[List[int]]:
        """
        Try to optimize waypoint order using OSRM's trip service with retries.
        Returns an index order list or None on failure.
        """
        if len(coords) < 3:
            return None

        base = (settings.osm_base_url or "https://router.project-osrm.org").rstrip("/")
        coord_str = ";".join([f"{lon},{lat}" for lon, lat in coords])
        url = f"{base}/trip/v1/driving/{coord_str}"
        params = {"source": "first", "destination": "last", "roundtrip": "false"}

        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                resp = requests.get(url, params=params, timeout=8 * attempt)
                if not resp.ok:
                    logger.warning(
                        "[OSRM] Trip optimization failed (%d/%d): %s %s",
                        attempt,
                        attempts,
                        resp.status_code,
                        resp.text[:120],
                    )
                    time.sleep(1.0 * attempt)
                    continue

                data = resp.json()
                waypoints = data.get("waypoints", [])
                if not waypoints:
                    return None

                order = sorted(range(len(waypoints)), key=lambda i: waypoints[i].get("waypoint_index", i))
                return order
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("[OSRM] Trip optimization exception (%d/%d): %s", attempt, attempts, exc)
                time.sleep(1.0 * attempt)

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

        # Origin / destination resolution
        ordered_addresses: List[str] = []
        windowed_coords: List[tuple[str, tuple[float, float]]] = []
        failed: List[str] = []

        # Geocode origin up front
        origin = self.origin or (self.stops[0].address if self.stops else "")
        origin_coord = self._geocode(origin)
        if not origin_coord:
            raise ValueError(f"Could not geocode origin '{origin}' via Geoapify.")
        windowed_coords.append((origin, origin_coord))

        # Process windows independently; optimize within each window if possible.
        for group in grouped:
            addrs = [s.address for s in group]
            addr_coords: List[tuple[str, tuple[float, float]]] = []
            for addr in addrs:
                coord = self._geocode(addr)
                if not coord:
                    logger.warning("[GEOAPIFY] Skipping address (no geocode): %s", addr)
                    failed.append(addr)
                    continue
                addr_coords.append((addr, coord))

            if len(addr_coords) > 2:
                coord_list = [c for _, c in addr_coords]
                order = self._optimize_order_geoapify(coord_list)
                if order:
                    addr_coords = [addr_coords[i] for i in order]
                    logger.info("[GEOAPIFY] Optimized %d stops within window", len(addr_coords))
                else:
                    logger.info("[GEOAPIFY] Using window order (no optimization) for %d stops", len(addr_coords))

            windowed_coords.extend(addr_coords)

        # Destination override / return to origin
        destination = (
            self.destination_override
            if self.destination_override
            else (self.origin if self.end_at_origin else (windowed_coords[-1][0] if windowed_coords else origin))
        )
        dest_coord = self._geocode(destination)
        if dest_coord:
            windowed_coords.append((destination, dest_coord))
        else:
            logger.warning("[GEOAPIFY] Could not geocode destination '%s'; omitting.", destination)

        if len(windowed_coords) < 2:
            raise ValueError("Need at least two geocoded waypoints to build a route.")

        if failed:
            logger.warning(
                "[GEOAPIFY] Skipped %d address(es) that could not be geocoded: %s",
                len(failed),
                "; ".join(failed),
            )

        # Log final address order for observability
        ordered_addresses = [addr for addr, _ in windowed_coords]
        logger.info("[GEOAPIFY] Final waypoint order: %s", " -> ".join(ordered_addresses))

        # Build an OSRM map link (shows all waypoints reliably).
        loc_params = "&".join([f"loc={lat},{lon}" for _, (lon, lat) in windowed_coords])
        osrm_url = f"https://map.project-osrm.org/?{loc_params}"

        # Keep the OSM directions-style URL as a secondary reference
        route_param = ";".join([f"{lat},{lon}" for _, (lon, lat) in windowed_coords])
        engine = "fossgis_osrm_car"
        if self.mode in ("walk", "foot"):
            engine = "fossgis_osrm_foot"
        elif self.mode in ("bike", "bicycle"):
            engine = "fossgis_osrm_bike"
        osm_url = f"{self.ROUTE_VIEW_URL}?engine={engine}&route={route_param}"

        logger.info("[GEOAPIFY] Generated OSRM map link with Geoapify geocoding.")
        # Prefer OSRM map link to ensure via points render; fallback remains in logs.
        return osrm_url

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
