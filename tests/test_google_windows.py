import optimized_routing.manager.google_manager as gm
from optimized_routing.manager.base import RouteStop, ServiceWindow


class DummyManager(gm.GoogleMapsRoutingManager):
    def __init__(self):
        # Avoid initializing real client; has API key check
        self.origin = "Origin"
        self.destination_override = None
        self.stops = []
        self.end_at_origin = True
        self.use_query_string = False

    def get_optimized_route(self, addresses, config=None):
        # Return addresses as-is to avoid network
        return {"origin": addresses[0], "destination": addresses[-1], "waypoints": addresses}


def test_window_order_enforced():
    mgr = DummyManager()
    mgr.stops = [
        RouteStop(address="PM Address", window=ServiceWindow.PM, label="pm"),
        RouteStop(address="AM Address", window=ServiceWindow.AM, label="am"),
        RouteStop(address="AllDay Address", window=ServiceWindow.ALL_DAY, label="all"),
    ]

    url = mgr.build_route_url()
    assert "AM+Address" in url
    assert url.index("AM+Address") < url.index("AllDay+Address") < url.index("PM+Address")
