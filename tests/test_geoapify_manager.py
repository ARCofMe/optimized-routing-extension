import pytest

from optimized_routing.manager.geoapify_manager import GeoapifyRoutingManager
from optimized_routing.manager.base import RouteStop, ServiceWindow


def test_geoapify_skips_failed_geocode(monkeypatch):
    mgr = GeoapifyRoutingManager(origin="Origin, ME")
    mgr.add_stops(
        [
            RouteStop(address="100 Good St", window=ServiceWindow.AM),
            RouteStop(address="200 Missing St", window=ServiceWindow.PM),
        ]
    )

    calls = []

    def fake_geocode(addr):
        calls.append(addr)
        if "Missing" in addr:
            return None
        return (0.0, 0.0)

    monkeypatch.setattr(mgr, "_geocode", fake_geocode)

    url = mgr.build_route_url()

    assert "map.project-osrm.org" in url
    assert any("Missing" in c for c in calls)


def test_geoapify_raises_when_no_coordinates(monkeypatch):
    mgr = GeoapifyRoutingManager(origin="Origin, ME")
    mgr.add_stops([RouteStop(address="Nowhere", window=ServiceWindow.AM)])

    monkeypatch.setattr(mgr, "_geocode", lambda addr: None)

    with pytest.raises(ValueError):
        mgr.build_route_url()


def test_geoapify_warns_on_failed_geocode(monkeypatch, caplog):
    mgr = GeoapifyRoutingManager(origin="Origin, ME")
    mgr.add_stops([RouteStop(address="Bad Addr", window=ServiceWindow.AM)])

    monkeypatch.setattr(
        mgr,
        "_geocode",
        lambda addr: (0.0, 0.0) if "Origin" in addr else None,
    )
    monkeypatch.setattr(mgr, "_optimize_order_geoapify", lambda coords: None)
    monkeypatch.setattr(mgr, "_optimize_order_osrm", lambda coords: None)

    url = mgr.build_route_url()
    assert "map.project-osrm.org" in url
    assert any("Skipping address" in rec.message for rec in caplog.records)


def test_geoapify_osrm_lon_lat_order(monkeypatch):
    mgr = GeoapifyRoutingManager(origin="Origin, ME")
    mgr.add_stops([RouteStop(address="Good Addr", window=ServiceWindow.AM)])

    # Return two points: origin and stop
    coord_map = {
        "Origin, ME": (-70.2, 44.12),
        "Good Addr": (-70.5, 43.88),
    }

    monkeypatch.setattr(mgr, "_geocode", lambda addr: coord_map.get(addr))

    url = mgr.build_route_url()
    assert "map.project-osrm.org" in url
    assert "loc=44.12,-70.2" in url
    assert "loc=43.88,-70.5" in url


def test_geoapify_optimizes_within_window(monkeypatch):
    mgr = GeoapifyRoutingManager(origin="Origin, ME")
    mgr.add_stops(
        [
            RouteStop(address="A", window=ServiceWindow.AM),
            RouteStop(address="B", window=ServiceWindow.AM),
            RouteStop(address="C", window=ServiceWindow.AM),
        ]
    )

    coord_map = {
        "Origin, ME": (-70.0, 44.0),
        "A": (-70.1, 44.1),
        "B": (-70.2, 44.2),
        "C": (-70.3, 44.3),
    }

    # Force an optimized order of C, B, A
    monkeypatch.setattr(mgr, "_geocode", lambda addr: coord_map.get(addr))
    monkeypatch.setattr(mgr, "_optimize_order_geoapify", lambda coords: [2, 1, 0])
    monkeypatch.setattr(mgr, "_optimize_order_osrm", lambda coords: None)

    url = mgr.build_route_url()
    # Order should be Origin -> C -> B -> A -> Origin (return to origin default)
    assert "loc=44.0,-70.0" in url.split("&")[0]
    assert "loc=44.3,-70.3" in url
    assert url.count("loc=") == 5  # origin + 3 stops + destination(origin)
