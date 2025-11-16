# Optimized Routing Extension

This package automates optimized route generation for BlueFolder technician assignments using multiple routing providers (Google Maps, Mapbox, OSM/OSRM) and optional Cloudflare URL shortening.

---

## Features

- Fetches daily assignments from BlueFolder
- Converts assignments → RouteStops with AM/PM/ALL_DAY grouping
- Deduplicates overlapping stops
- Supports provider selection (`google`, `mapbox`, `osm`); Google is default
- Orders stops by service window (AM before PM before ALL_DAY)
- CLI interface for routing or previewing stops
- Optional Cloudflare Worker URL shortener
- Saves final route URL in BlueFolder `link2Url`

---

## Installation

```
pip install -e .
```

Create `.env`:

```
BLUEFOLDER_API_KEY=xxxxx
BLUEFOLDER_BASE_URL=https://your.bluefolder.com/api/2.0

GOOGLE_API_KEY=xxxxx
MAPBOX_API_KEY=xxxxx
OSM_BASE_URL=https://router.project-osrm.org   # optional override

CF_SHORTENER_URL=https://your-worker.workers.dev   # optional
DEFAULT_ORIGIN=South Paris, ME                     # optional
DEFAULT_PROVIDER=google                            # google|mapbox|osm
```

---

## CLI Usage

### Route a single user
```
python3 -m optimized_routing.main --user 33538043
```

### Override origin or destination
```
--origin "Lewiston, ME"
--destination "South Paris, ME"
```

### Pick routing provider
```
--provider google
--provider mapbox
--provider osm

# Skip BF updates (dry run)
--dry-run
```

### Preview mode (no BlueFolder updates)
```
python3 -m optimized_routing.main --preview-stops 33538043
python3 -m optimized_routing.main --preview-stops all
```

---

## Tests

```
pytest -q
```

Tests validate:
- CLI input argument handling
- Provider selection
- Shortener
- BlueFolder shims
- Stop ordering & deduplication
- Provider key validation
- Dry-run behavior and logging (run id)

Note: tests stub network calls; enable coverage flags locally if `pytest-cov` is installed.

---

## License

MIT License
