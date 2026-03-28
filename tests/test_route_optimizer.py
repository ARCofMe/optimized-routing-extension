# tests/test_route_optimizer.py

import optimized_routing.routing as routing
from optimized_routing.bluefolder_integration import BlueFolderIntegration


def test_route_for_user():
    """Smoke test that calls don't crash end-to-end."""
    uid = 12345
    origin = "180 E Hebron Rd, Hebron, ME 04238"

    bf = BlueFolderIntegration()

    # Should not crash even with no real BlueFolder data
    assignments = bf.get_user_assignments_today(uid)
    assert isinstance(assignments, list)

    # Should always return a URL or placeholder text
    route = routing.generate_route_for_provider(
        "osm",
        uid,
        origin_address=origin,
        destination_override=None,
    )

    assert isinstance(route, str)
    assert len(route) > 0


def test_route_for_user_osm_without_external_network(monkeypatch):
    monkeypatch.setattr(
        "optimized_routing.manager.osm_manager.OSMRoutingManager._geocode_address",
        lambda self, address: [-70.0, 44.0],
    )
    monkeypatch.setattr(
        "optimized_routing.manager.osm_manager.OSMRoutingManager._optimize_order",
        lambda self, coords: None,
    )

    route = routing.generate_route_for_provider(
        "osm",
        12345,
        origin_address="180 E Hebron Rd, Hebron, ME 04238",
        destination_override=None,
        assignments=[
            {
                "serviceRequestId": "1",
                "address": "123 Main",
                "city": "Town",
                "state": "ME",
                "zip": "04000",
                "start": "2024-01-01T08:00:00",
            }
        ],
    )

    assert "map.project-osrm.org" in route
