"""Pytest fixtures for optimized routing tests."""

import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    """Provide dummy env vars for all tests."""
    monkeypatch.setenv("BLUEFOLDER_API_KEY", "test-key")
    monkeypatch.setenv("BLUEFOLDER_ACCOUNT_NAME", "testaccount")
