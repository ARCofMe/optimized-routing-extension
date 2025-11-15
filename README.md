# Optimized Routing Extension

This package automates optimized route generation for BlueFolder technician assignments using multiple routing providers (Google Maps, Mapbox, OSM/OSRM) and optional Cloudflare URL shortening.

---

## Features

- Fetches daily assignments from BlueFolder
- Converts assignments → RouteStops with AM/PM/ALL_DAY grouping
- Deduplicates overlapping stops
- Supports provider selection (`google`, `mapbox`, `osm`)
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

CF_SHORTENER_URL=https://your-worker.workers.dev   # optional
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

---

## License

MIT License