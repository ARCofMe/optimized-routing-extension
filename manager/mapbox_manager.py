from __future__ import annotations

from .base import BaseRoutingManager


class MapboxRoutingManager(BaseRoutingManager):
    """Placeholder for Mapbox routing integration.

    To implement:
    - Use Mapbox Directions API with access token
    - Geocode addresses to coordinates
    - Build a deep-link URL or use it purely server-side
    """

    def build_route_url(self) -> str:
        raise NotImplementedError(
            "MapboxRoutingManager.build_route_url is not implemented yet. "
        )
