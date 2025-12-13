import pytest

from optimized_routing.routing import generate_route_for_provider
from optimized_routing.manager.google_manager import GoogleMapsRoutingManager


class DummyIntegration:
    def get_user_assignments_today(self, user_id):
        return [
            {"serviceRequestId": "1", "address": "123 Main", "city": "Town", "state": "ME", "zip": "04000", "start": "2024-01-01T08:00:00"},
            {"serviceRequestId": "2", "address": "456 Oak", "city": "Town", "state": "ME", "zip": "04000", "start": "2024-01-01T13:00:00"},
        ]


def test_generate_route_for_provider_unknown_provider(monkeypatch):
    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    with pytest.raises(ValueError):
        generate_route_for_provider("bogus", 1)


def test_generate_route_for_provider_geoapify(monkeypatch):
    class DummyManager:
        def __init__(self, origin, destination_override=None):
            self.origin = origin
            self.destination_override = destination_override
            self.stops = []

        def add_stops(self, stops):
            self.stops = stops

        def build_route_url(self):
            return "geo://route"

    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    monkeypatch.setattr("optimized_routing.routing.GeoapifyRoutingManager", DummyManager)
    from optimized_routing import routing
    routing.settings.geoapify_api_key = "dummy"

    url = generate_route_for_provider("geoapify", 1, origin_address="Origin")
    assert url == "geo://route"


def test_generate_route_for_provider_google(monkeypatch):
    # Mock manager to avoid real gmaps calls
    class DummyManager:
        def __init__(self, origin, destination_override=None):
            self.origin = origin
            self.destination_override = destination_override
            self.stops = []

        def add_stops(self, stops):
            self.stops = stops

        def build_route_url(self):
            return "mock://route"

    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    monkeypatch.setattr("optimized_routing.routing.GoogleMapsRoutingManager", DummyManager)
    from optimized_routing import routing
    routing.settings.google_api_key = "dummy"

    url = generate_route_for_provider("google", 1, origin_address="Origin")
    assert url == "mock://route"
