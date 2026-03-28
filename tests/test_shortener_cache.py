from optimized_routing import routing


def test_shorten_route_url_caches(monkeypatch):
    routing.short_cache.clear()
    routing.CF_SHORTENER_URL = "https://worker.test"
    monkeypatch.setattr(routing.settings, "cf_shortener_url", "https://worker.test")

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


def test_shorten_route_url_falls_back_when_short_key_is_missing(monkeypatch):
    routing.short_cache.clear()
    routing.CF_SHORTENER_URL = "https://worker.test"
    monkeypatch.setattr(routing.settings, "cf_shortener_url", "https://worker.test")

    class DummyResp:
        ok = True
        status_code = 200
        text = ""

        def json(self):
            return {"unexpected": "payload"}

    monkeypatch.setattr(routing.requests, "post", lambda *a, **k: DummyResp())

    url = routing.shorten_route_url("http://example.com/long")

    assert url == "http://example.com/long"
