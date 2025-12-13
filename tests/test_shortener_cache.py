from optimized_routing import routing


def test_shorten_route_url_caches(monkeypatch):
    routing.short_cache.clear()
    routing.CF_SHORTENER_URL = "https://worker.test"

    calls = {"count": 0}

    class DummyResp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"short": "https://sho.rt/abc"}

    def fake_post(url, json=None, timeout=None):
        calls["count"] += 1
        return DummyResp()

    monkeypatch.setattr(routing.requests, "post", fake_post)

    first = routing.shorten_route_url("http://example.com/long")
    second = routing.shorten_route_url("http://example.com/long")

    assert first == second == "https://sho.rt/abc"
    assert calls["count"] == 1
