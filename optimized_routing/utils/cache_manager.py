"""Lightweight JSON-backed cache with TTL expiry and atomic persistence."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TTL_MINUTES = 30


# ---------------------------------------------------------------------------
# CacheManager Class
# ---------------------------------------------------------------------------


class CacheManager:
    """
    Generic key–value cache with both in-memory and on-disk persistence.

    Each instance operates within its own cache file (namespace) located in
    the `.cache/` folder.

    Attributes:
        name (str): Cache namespace (creates `{name}.json` under `.cache/`).
        ttl (int): Cache time-to-live in seconds.
        file_path (str): Path to the JSON file backing this cache.
        data (dict): In-memory dictionary of cached entries.

    JSON File Structure:
        {
            "data": {
                "key1": [timestamp, value],
                "key2": [timestamp, value]
            },
            "timestamp": <last_saved_time>
        }
    """

    def __init__(self, name: str, ttl_minutes: int = DEFAULT_TTL_MINUTES):
        """
        Initialize the cache.

        Args:
            name (str): Cache file name (without extension).
            ttl_minutes (int): How long (in minutes) cached data should persist.
        """
        self.name = name
        self.ttl = ttl_minutes * 60
        self.file_path = CACHE_DIR / f"{name}.json"
        self.data = self._load()

        logger.debug(f"[CACHE] Initialized '{self.name}' at {self.file_path}")

    # -----------------------------------------------------------------------
    # Internal File Operations
    # -----------------------------------------------------------------------

    def _load(self) -> dict:
        """Load cache data from disk."""
        if not self.file_path.exists():
            return {}

        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
            payload = raw.get("data", {})
            if isinstance(payload, dict):
                return payload
            logger.warning("[CACHE] Ignoring malformed payload in '%s'", self.name)
        except Exception as e:
            logger.warning(f"[CACHE] Failed to load '{self.name}': {e}")
        return {}

    def _save(self) -> None:
        """Persist cache data to disk."""
        try:
            payload = json.dumps({"data": self.data, "timestamp": time.time()}, indent=2)
            temp_path = self.file_path.with_suffix(f"{self.file_path.suffix}.tmp")
            temp_path.write_text(payload, encoding="utf-8")
            temp_path.replace(self.file_path)
            logger.debug(f"[CACHE] Saved '{self.name}' ({len(self.data)} entries)")
        except Exception as e:
            logger.warning(f"[CACHE] Failed to save '{self.name}': {e}")

    # -----------------------------------------------------------------------
    # Public Cache API
    # -----------------------------------------------------------------------

    def get(self, key: str):
        """
        Retrieve a cached value if not expired.

        Args:
            key (str): The key to retrieve.

        Returns:
            Any | None: The cached value, or None if not found or expired.
        """
        entry = self.data.get(str(key))
        if not entry:
            return None

        ts, value = entry
        if time.time() - ts > self.ttl:
            # Expired — remove and ignore
            logger.debug(f"[CACHE] Expired key '{key}' in '{self.name}'")
            del self.data[str(key)]
            self._save()
            return None

        return value

    def set(self, key: str, value) -> None:
        """
        Store a value and persist it to disk immediately.

        Args:
            key (str): The key under which to store the value.
            value (Any): The value to cache.
        """
        self.data[str(key)] = (time.time(), value)
        self._save()
        logger.info(f"[CACHE] Stored key '{key}' in '{self.name}'")

    def clear(self) -> None:
        """
        Clear all entries in this cache and delete the cache file.
        """
        self.data = {}
        if self.file_path.exists():
            self.file_path.unlink()
        logger.info(f"[CACHE] Cleared '{self.name}'")
