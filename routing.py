"""
routing.py

Primary orchestration layer for generating technician routes
from BlueFolder assignments using Google Maps.

Responsibilities:
    - Pull technician assignments via BlueFolderIntegration.
    - Convert assignments into structured RouteStop objects.
    - Pass stops to GoogleMapsRoutingManager for optimized routing.
"""

import logging
from datetime import datetime
from typing import List, Optional

from bluefolder_integration import BlueFolderIntegration
from manager.google_manager import GoogleMapsRoutingManager
from manager.base import RouteStop, ServiceWindow
from config import RouteConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

    Args:
        assignments (List[dict]): List of enriched BlueFolder assignments.

    Returns:
        List[RouteStop]: Structured stops ready for route building.
    """
    stops: List[RouteStop] = []

    for a in assignments:
        address = a.get("address", "")
        city = a.get("city", "")
        state = a.get("state", "")
        zip_code = a.get("zip", "")
        full_address = f"{address}, {city}, {state} {zip_code}".strip(" ,")

        window = determine_service_window(a.get("start", ""))
        label = f"SR-{a.get('serviceRequestId', 'N/A')}"

        stops.append(RouteStop(address=full_address, window=window, label=label))

    logger.debug(f"Converted {len(stops)} assignments to RouteStops.")
    return stops


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def generate_google_route(user_id: int, origin_address: Optional[str] = None) -> str:
    """
    Generate a Google Maps route URL for a technician’s assignments today.

    Steps:
        1. Fetch today's BlueFolder assignments for the given user.
        2. Convert them into RouteStop objects.
        3. Build an optimized Google Maps route URL.

    Args:
        user_id (int): The BlueFolder user ID to fetch assignments for.
        origin_address (Optional[str]): Optional override for route start.

    Returns:
        str: A fully formed Google Maps route URL or a message if no assignments found.
    """
    bf = BlueFolderIntegration()
    assignments = bf.get_user_assignments_today(user_id)

    if not assignments:
        logger.warning("No assignments found for user %s", user_id)
        return "No assignments found."

    stops = bluefolder_to_routestops(assignments)

    manager = GoogleMapsRoutingManager(origin=origin_address or "South Paris, ME")
    manager.add_stops(stops)

    route_url = manager.build_route_url()
    logger.info(f"[ROUTING] Generated route URL for user {user_id}: {route_url}")

    return route_url
