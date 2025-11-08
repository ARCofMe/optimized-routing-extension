import os
import json
import time
import hashlib
from pathlib import Path

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

DEFAULT_TTL = 60 * 15  # 15 minutes

def _cache_key(prefix: str, *args, **kwargs) -> str:
    key_raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    digest = hashlib.md5(key_raw.encode()).hexdigest()
    return f"{prefix}_{digest}.json"

def get_cached(prefix: str, *args, ttl: int = DEFAULT_TTL, **kwargs):
    key = _cache_key(prefix, *args, **kwargs)
    path = CACHE_DIR / key
    if not path.exists():
        return None

    if time.time() - path.stat().st_mtime > ttl:
        path.unlink(missing_ok=True)
        return None

    with open(path, "r") as f:
        return json.load(f)

def set_cached(prefix: str, data, *args, **kwargs):
    key = _cache_key(prefix, *args, **kwargs)
    path = CACHE_DIR / key
    with open(path, "w") as f:
        json.dump(data, f)
    return path
