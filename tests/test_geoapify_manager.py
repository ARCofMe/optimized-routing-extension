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

    assert "directions" in url
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

    monkeypatch.setattr(mgr, "_geocode", lambda addr: None)

    with pytest.raises(ValueError):
        mgr.build_route_url()

    assert any("Skipping address" in rec.message for rec in caplog.records)
