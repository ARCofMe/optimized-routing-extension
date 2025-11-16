"""Pytest fixtures for optimized routing tests."""

import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

# Stub dotenv if missing
if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = type("dotenv", (), {"load_dotenv": lambda *a, **k: None})

# Stub requests if missing
if "requests" not in sys.modules:
    class DummyResp:
        status_code = 200
        content = b"<response status='ok'></response>"
        text = "<response status='ok'></response>"

        def json(self):
            return {}

        def raise_for_status(self):
            return None

    class DummySession:
        def __init__(self):
            self.calls = []

        def post(self, url, data=None, headers=None, timeout=None, json=None, params=None):
            self.calls.append({"url": url, "data": data, "headers": headers, "json": json, "params": params})
            return DummyResp()

        def get(self, url, params=None, timeout=None):
            self.calls.append({"url": url, "params": params, "timeout": timeout})
            return DummyResp()

    requests = type("requests", (), {
        "Session": DummySession,
        "post": staticmethod(lambda *a, **k: DummyResp()),
        "get": staticmethod(lambda *a, **k: DummyResp()),
        "exceptions": type("exceptions", (), {"HTTPError": Exception}),
    })
    sys.modules["requests"] = requests

if "bluefolder_api" not in sys.modules:
    fake_module = type("bluefolder_api", (), {})
    fake_client_module = type("bluefolder_api.client", (), {"BlueFolderClient": object})
    sys.modules["bluefolder_api"] = fake_module
    sys.modules["bluefolder_api.client"] = fake_client_module

# Stub googlemaps if missing
if "googlemaps" not in sys.modules:
    sys.modules["googlemaps"] = type("googlemaps", (), {"Client": object})

if "tenacity" not in sys.modules:
    # Minimal stubs for decorators used in google_manager
    def _noop(fn):
        return fn
    sys.modules["tenacity"] = type(
        "tenacity",
        (),
        {
            "retry": lambda *a, **k: _noop,
            "stop_after_attempt": lambda *a, **k: None,
            "wait_exponential": lambda *a, **k: None,
        },
    )

if "pydantic" not in sys.modules:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, **kwargs):
        return default

    sys.modules["pydantic"] = type("pydantic", (), {"BaseModel": BaseModel, "Field": Field})


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Provide dummy env vars for all tests."""
    monkeypatch.setenv("BLUEFOLDER_API_KEY", "test-key")
    monkeypatch.setenv("BLUEFOLDER_ACCOUNT_NAME", "testaccount")
