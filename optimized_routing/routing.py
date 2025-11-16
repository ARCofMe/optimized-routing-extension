# routing.py
"""
Primary orchestration layer for generating technician routes
from BlueFolder assignments using Google Maps.

Responsibilities:
    - Pull technician assignments via BlueFolderIntegration.
    - Convert assignments into structured RouteStop objects.
    - Pass stops to GoogleMapsRoutingManager for optimized routing.
"""
import os
import logging
from datetime import datetime
from typing import List, Optional
import requests
from optimized_routing.bluefolder_integration import BlueFolderIntegration
from optimized_routing.manager.google_manager import GoogleMapsRoutingManager
from optimized_routing.manager.mapbox_manager import MapboxRoutingManager
from optimized_routing.manager.osm_manager import OSMRoutingManager
from optimized_routing.manager.base import RouteStop, ServiceWindow
from optimized_routing.config import RouteConfig, settings

logger = logging.getLogger(__name__)


CF_SHORTENER_URL = os.getenv("CF_SHORTENER_URL")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def shorten_route_url(long_url: str) -> str:
    """
    Hit Cloudflare Worker shortener to convert a long Google Maps route URL.
    Returns short URL, or original URL if anything fails.
    """
    if not CF_SHORTENER_URL:
        logger.warning("[SHORTENER] CF_SHORTENER_URL not set — returning long URL")
        return long_url

    try:
        r = requests.post(f"{CF_SHORTENER_URL}/new", json={"url": long_url}, timeout=6)
        if r.ok:
            data = r.json()
            short = data.get("short")
            if short:
                logger.info(f"[SHORTENER] Shortened → {short}")
                return short
            else:
                logger.warning("[SHORTENER] Response OK but no 'short' key")
        else:
            logger.error(f"[SHORTENER] POST failed: {r.status_code} {r.text}")
    except Exception as e:
        logger.exception(f"[SHORTENER] Exception: {e}")

    return long_url


def determine_service_window(start_time: str) -> ServiceWindow:
    """
    Infer a rough service window (AM, PM, or ALL_DAY) from an ISO datetime string.

    Args:
        start_time (str): ISO datetime string (e.g., '2025-11-08T09:00:00').

    Returns:
        ServiceWindow: Enum representing the time block of the service.
    """
    try:
        hour = datetime.fromisoformat(start_time).hour
    except Exception:
        logger.debug(f"Invalid start_time '{start_time}', defaulting to ALL_DAY")
        return ServiceWindow.ALL_DAY

    if hour < 12:
        return ServiceWindow.AM
    elif hour < 17:
        return ServiceWindow.PM
    return ServiceWindow.ALL_DAY


def bluefolder_to_routestops(assignments: List[dict]) -> List[RouteStop]:
    """
    Convert enriched BlueFolder assignment dictionaries into RouteStop objects.

    Deduplication logic:
        - If BlueFolder creates AM and PM blocks for the same SR,
          they share the same address → causes duplicate waypoints.
        - We dedupe based on (serviceRequestId, address).
        - If duplicates exist, we keep the *earliest* service window.
    """

    raw_stops: List[RouteStop] = []

    for a in assignments:
        address = a.get("address", "")
        city = a.get("city", "")
        state = a.get("state", "")
        zip_code = a.get("zip", "")
        full_address = f"{address}, {city}, {state} {zip_code}".strip(" ,")

        window = determine_service_window(a.get("start", ""))
        label = f"SR-{a.get('serviceRequestId', 'N/A')}"

        raw_stops.append(RouteStop(address=full_address, window=window, label=label))

    unique = {}

    for stop in raw_stops:
        key = (stop.label, stop.address)

        if key not in unique:
            unique[key] = stop
        else:
            # Keep earliest window value
            if stop.window.value < unique[key].window.value:
                unique[key] = stop

    # Preserve a consistent order while respecting service windows (AM -> PM -> ALL_DAY)
    stops = list(unique.values())
    stops.sort(key=lambda s: s.window.value)

    logger.debug(
        f"Converted {len(raw_stops)} assignments → {len(stops)} unique RouteStops."
    )
    return stops


def dedupe_stops(stops):
    """
    Remove duplicate stops caused by AM/PM overlapping assignments.
    Two stops are considered identical if they share the same SR ID or same address.
    """
    seen = set()
    unique = []

    for s in stops:
        # Use SR ID if present, otherwise normalized address
        key = s.label or s.address.lower().strip()

        if key not in seen:
            unique.append(s)
            seen.add(key)

    return unique


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def generate_route_for_provider(
    provider: str,
    user_id: int,
    origin_address: Optional[str] = None,
    destination_override: Optional[str] = None,
) -> str:
    """Generate a route URL for the selected provider."""
    bf = BlueFolderIntegration()
    assignments = bf.get_user_assignments_today(user_id)

    if not assignments:
        logger.warning("No assignments found for user %s", user_id)
        return "No assignments found."

    stops = bluefolder_to_routestops(assignments)
    stops = dedupe_stops(stops)

    provider = provider.lower()
    if provider == "google":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY is required for google provider")
        manager = GoogleMapsRoutingManager(
            origin=origin_address or settings.default_origin,
            destination_override=destination_override,
        )
    elif provider == "mapbox":
        if not settings.mapbox_api_key:
            raise ValueError("MAPBOX_API_KEY is required for mapbox provider")
        manager = MapboxRoutingManager(
            origin=origin_address or settings.default_origin,
            destination_override=destination_override,
        )
    elif provider == "osm":
        manager = OSMRoutingManager(
            origin=origin_address or settings.default_origin,
            destination_override=destination_override,
        )
    else:
        raise ValueError(f"Unknown provider '{provider}'")

    manager.add_stops(stops)

    route_url = manager.build_route_url()
    logger.info(f"[ROUTING] Generated route URL for user {user_id}: {route_url}")

    return route_url


def preview_user_stops(user_id: int, origin: Optional[str] = None):
    """
    CLI helper:
      - Shows enriched assignments
      - Shows deduped RouteStops
      - Shows final ordered stop list
      - Displays route URL (if available)
    """

    bf = BlueFolderIntegration()
    assignments = bf.get_user_assignments_today(user_id)

    print("\n================= RAW ASSIGNMENTS =================")
    if not assignments:
        print(f"[NO ASSIGNMENTS] User {user_id} has no scheduled work today.")
        print("===================================================\n")
        return None

    for a in assignments:
        print(a)

    # Build deduped stops
    stops = bluefolder_to_routestops(assignments)
    stops = dedupe_stops(stops)

    print("\n================= ROUTE STOPS =================")
    if not stops:
        print(
            f"[NO VALID STOPS] User {user_id} had assignments but they could not be converted."
        )
        print("===================================================\n")
        return None

    for s in stops:
        print(f"- {s.label} | {s.window.name} | {s.address}")

    mgr = GoogleMapsRoutingManager(origin=origin or "South Paris, ME")
    mgr.add_stops(stops)

    print("\n================= ROUTE URL =================")
    try:
        url = mgr.build_route_url()
        print(url)
    except Exception as e:
        print("[ERROR] Could not generate route:", e)
        url = None

    print("===================================================\n")
    return url
