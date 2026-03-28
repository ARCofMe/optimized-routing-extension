import pytest

from optimized_routing.routing import generate_route_for_provider


class DummyIntegration:
    def get_user_assignments_today(self, user_id):
        return [
            {
                "serviceRequestId": "1",
                "address": "123 Main",
                "city": "Town",
                "state": "ME",
                "zip": "04000",
                "start": "2024-01-01T08:00:00",
            }
        ]

def test_geoapify_provider_requires_key(monkeypatch):
    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    from optimized_routing import routing
    monkeypatch.setattr(routing.settings, "geoapify_api_key", "")

    with pytest.raises(ValueError):
        generate_route_for_provider("geoapify", 1)


def test_mapbox_provider_requires_key(monkeypatch):
    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    from optimized_routing import routing
    monkeypatch.setattr(routing.settings, "mapbox_api_key", "")

    with pytest.raises(ValueError):
        generate_route_for_provider("mapbox", 1)


def test_osm_provider_does_not_require_key(monkeypatch):
    monkeypatch.setattr("optimized_routing.routing.BlueFolderIntegration", lambda: DummyIntegration())
    monkeypatch.setattr("optimized_routing.manager.osm_manager.OSMRoutingManager._geocode_address", lambda self, address: [-70.0, 44.0])
    monkeypatch.setattr("optimized_routing.manager.osm_manager.OSMRoutingManager._optimize_order", lambda self, coords: None)
    url = generate_route_for_provider("osm", 1, origin_address="Start")
    assert "map.project-osrm.org" in url
