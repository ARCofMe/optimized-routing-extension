# routing.py

import logging
from datetime import datetime
from typing import List
from bluefolder_integration import BlueFolderIntegration
from manager.google_manager import GoogleMapsRoutingManager
from manager.base import RouteStop, ServiceWindow
from config import RouteConfig

logger = logging.getLogger(__name__)

def determine_service_window(start_time: str) -> ServiceWindow:
    """Roughly classify a service window from an ISO datetime."""
    try:
        hour = datetime.fromisoformat(start_time).hour
        if hour < 12:
            return ServiceWindow.AM
        elif hour < 17:
            return ServiceWindow.PM
        else:
            return ServiceWindow.ALL_DAY
    except Exception:
        return ServiceWindow.ALL_DAY


def bluefolder_to_routestops(assignments: List[dict]) -> List[RouteStop]:
    """Convert enriched BlueFolder assignment data into RouteStop objects."""
    stops = []
    for a in assignments:
        full_address = f"{a.get('address', '')}, {a.get('city', '')}, {a.get('state', '')} {a.get('zip', '')}".strip()
        window = determine_service_window(a.get("start", ""))
        label = f"SR-{a['serviceRequestId']}"
        stops.append(RouteStop(address=full_address, window=window, label=label))
    return stops


def generate_google_route(user_id: int, origin_address: str | None = None) -> str:
    """
    Fetch today's assignments for a BlueFolder user,
    convert to RouteStops, and build an optimized Google Maps route URL.
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
    logger.info(f"Generated route URL: {route_url}")
    return route_url
