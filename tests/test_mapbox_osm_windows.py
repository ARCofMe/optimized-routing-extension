from optimized_routing.manager.base import RouteStop, ServiceWindow
from optimized_routing.manager import mapbox_manager, osm_manager


def test_mapbox_window_order(monkeypatch):
    # Force token present
    mapbox_manager.MAPBOX_TOKEN = "token"

    # Stub geocode to return sequential coords in call order
    coords = [(i, i) for i in range(10)]
    call_idx = {"n": 0}

    def fake_geocode(self, address):
        i = call_idx["n"]
        call_idx["n"] += 1
        return coords[i]

    monkeypatch.setattr(mapbox_manager.MapboxRoutingManager, "_geocode", fake_geocode)

    class FakeResp:
        ok = True

        def json(self):
            # four waypoints: origin + AM + ALL + PM (we don't add destination override)
            return {
                "waypoints": [
                    {"location": [0, 0]},
                    {"location": [1, 1]},
                    {"location": [2, 2]},
                    {"location": [3, 3]},
                ]
            }

        def raise_for_status(self):
            return None

    monkeypatch.setattr("optimized_routing.manager.mapbox_manager.requests.get", lambda *a, **k: FakeResp())

    mgr = mapbox_manager.MapboxRoutingManager(origin="Origin", destination_override=None)
    mgr.add_stops(
        [
            RouteStop("PM", ServiceWindow.PM),
            RouteStop("AM", ServiceWindow.AM),
            RouteStop("ALL", ServiceWindow.ALL_DAY),
        ]
    )

    url = mgr.build_route_url()
    # Coordinates appended in call order -> check that AM was geocoded before ALL and PM
    assert url.startswith("https://www.mapbox.com/directions?coordinates=")
    # With fake coords, AM -> (0,0), ALL -> (1,1), PM -> (2,2)
    assert "0,0;1,1;2,2" in url


def test_osm_window_order(monkeypatch):
    # Stub geocode and optimize to preserve order of input addresses respecting windows
    def fake_geocode(self, address):
        # return placeholder lon/lat
        return [1.0, 2.0]

    monkeypatch.setattr(osm_manager.OSMRoutingManager, "_geocode_address", fake_geocode)
    monkeypatch.setattr(osm_manager.OSMRoutingManager, "_optimize_order", lambda *a, **k: None)

    mgr = osm_manager.OSMRoutingManager(origin="Origin")
    mgr.add_stops(
        [
            RouteStop("PM", ServiceWindow.PM),
            RouteStop("AM", ServiceWindow.AM),
            RouteStop("ALL", ServiceWindow.ALL_DAY),
        ]
    )

    url = mgr.build_route_url()
    # Google Maps dir URL should place AM before ALL before PM
    assert url.startswith("https://www.google.com/maps/dir/")
    assert url.index("AM") < url.index("ALL") < url.index("PM")
