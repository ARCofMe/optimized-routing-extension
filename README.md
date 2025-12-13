# Optimized Routing Extension

This package automates optimized route generation for BlueFolder technician assignments using multiple routing providers (Geoapify, Google Maps, Mapbox, OSM/OSRM) and optional Cloudflare URL shortening.

---

## Features

- Fetches daily assignments from BlueFolder
- Converts assignments → RouteStops with AM/PM/ALL_DAY grouping
- Deduplicates overlapping stops
- Supports provider selection (`geoapify`, `google`, `mapbox`, `osm`); Geoapify is default
- Geoapify builds OSM directions links without exposing API keys; Google/Mapbox/OSM remain available
- Caching for geocoding and URL shortening to reduce rate-limit pressure
- Orders stops by service window (AM before PM before ALL_DAY)
- CLI interface for routing or previewing stops
- Assignments fetch supports custom date ranges (defaults to today)
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

GEOAPIFY_API_KEY=xxxxx
GOOGLE_API_KEY=xxxxx
MAPBOX_API_KEY=xxxxx
OSM_BASE_URL=https://router.project-osrm.org   # optional override

CF_SHORTENER_URL=https://your-worker.workers.dev   # optional
DEFAULT_ORIGIN=South Paris, ME                     # optional
DEFAULT_PROVIDER=geoapify                          # geoapify|google|mapbox|osm
```

---

## Setup & Configuration
- You can configure the client either via BLUEFOLDER_ACCOUNT_NAME (default) or by passing `base_url `explicitly. If `base_url` is provided, it’s used instead of the account name.

## CLI Usage

### Route a single user
```
python3 -m optimized_routing.main --user 123456789
```

### Override origin or destination
```
--origin "Lewiston, ME"
--destination "South Paris, ME"
```

### Pick routing provider
```
--provider geoapify
--provider google
--provider mapbox
--provider osm

# Skip BF updates (dry run)
--dry-run
```

### Quick date helpers
Use `--date monday|today|tomorrow` to auto-populate start/end range without typing timestamps (overrides only if explicit dates aren’t provided).

### Date ranges for assignments

The core fetcher `get_user_assignments_range(user_id, start_date, end_date, date_range_type="scheduled")` accepts explicit BlueFolder-formatted dates (e.g., `2025.11.08 12:00 AM`). If omitted, it defaults to today's range (`12:00 AM` → `11:59 PM`). CLI flags:
```
--start-date "2025.11.08 12:00 AM"
--end-date   "2025.11.08 11:59 PM"
--date-range-type scheduled|created|completed   # default: scheduled
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
