from __future__ import annotations

from datetime import datetime, timedelta, timezone

from optimized_routing.bluefolder_integration import HTTPError, bluefolder_safe


class _Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_bluefolder_safe_retries_429_until_success(monkeypatch):
    calls = {"count": 0}
    sleeps: list[float] = []
    retry_at = (datetime.now(timezone.utc) + timedelta(seconds=6)).isoformat().replace("+00:00", "Z")
    xml = f"<response><error>Rate limited. Try again after {retry_at}</error></response>"

    monkeypatch.setattr("optimized_routing.bluefolder_integration.time.sleep", lambda seconds: sleeps.append(seconds))

    @bluefolder_safe
    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise HTTPError(response=_Response(429, xml))
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3
    assert len(sleeps) == 2
    assert all(seconds >= 5 for seconds in sleeps)


def test_bluefolder_safe_gives_up_after_retry_budget(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("optimized_routing.bluefolder_integration.time.sleep", lambda seconds: sleeps.append(seconds))

    @bluefolder_safe
    def always_limited():
        raise HTTPError(response=_Response(429, "<response><error>429</error></response>"))

    assert always_limited() is None
    assert len(sleeps) == 5
