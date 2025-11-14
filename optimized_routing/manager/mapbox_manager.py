"""
manager/mapbox_manager.py

Placeholder for future Mapbox routing integration.

To implement:
    - Integrate with the Mapbox Directions API.
    - Convert street addresses to coordinates (via Mapbox Geocoding API).
    - Generate deep-link URLs or return optimized coordinate sequences.
"""

from __future__ import annotations
import logging

from optimized_routing.manager.base import BaseRoutingManager

logger = logging.getLogger(__name__)


class MapboxRoutingManager(BaseRoutingManager):
    """
    Future routing manager for Mapbox integration.

    Planned capabilities:
        - Route optimization using Mapbox Directions API.
        - Address geocoding to GPS coordinates.
        - URL and API-based route visualization.

    Mapbox Documentation:
        https://docs.mapbox.com/api/navigation/directions/
    """

    def build_route_url(self) -> str:
        """
        Placeholder route builder.

        Returns:
            str: Placeholder URL for now.

        Raises:
            NotImplementedError: This feature is not yet implemented.
        """
        raise NotImplementedError(
            "MapboxRoutingManager.build_route_url is not implemented yet. "
            "See MapboxRoutingManager class docstring for future plans."
        )
