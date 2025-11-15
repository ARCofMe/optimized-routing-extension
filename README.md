# Optimized Routing Extension

A Python package that connects **BlueFolder**, **mapping providers** (Google Maps, Mapbox, or OpenStreetMap), and an optional **Cloudflare URL shortener** to generate daily optimized driving routes for field technicians.

---

## ✨ What This Does

- Pulls **today’s assignments** for each active BlueFolder user
- Resolves **customer + location** info with caching to reduce API calls
- Builds an **optimized route URL** using your chosen provider
- (Optionally) **shortens** long route URLs via a Cloudflare Worker
- Stores the final URL in the user’s **`link2Url`** field in BlueFolder

> **Note:** Due to BlueFolder permission limitations for Standard API users, `link2Url` is currently the most reliable field for storing a route link.

---

## 🧱 Project Layout

```bash
optimized-routing-extension/
├── cache/                      # JSON cache of assignments / locations
├── docs/
│   └── images/
│       └── readme_cli_example.png
├── optimized_routing/
│   ├── __init__.py
│   ├── main.py                 # CLI entry point (routing job + preview)
│   ├── route_today.py          # Simple helper script for a single user
│   ├── routing.py              # Route building & URL shortener integration
│   ├── config.py               # RouteConfig & global settings
│   ├── bluefolder_integration.py
│   │                           # BlueFolder users / assignments / SRs
│   ├── manager/
│   │   ├── __init__.py
│   │   ├── base.py             # RouteStop, ServiceWindow, Provider enum
│   │   ├── google_manager.py   # Google Maps route builder
│   │   ├── mapbox_manager.py   # Mapbox Directions route builder
│   │   └── osm_manager.py      # OpenStreetMap / OSRM-style route builder
│   └── utils/
│       ├── __init__.py
│       └── cache_manager.py    # Simple TTL file-based cache
├── tests/                      # Pytest suite
├── pyproject.toml              # Packaging metadata
├── requirements.txt
└── README.md                   # (You are here)
```

---

## ⚙️ Installation

Create a virtualenv (recommended) and install dependencies:

```bash
cd optimized-routing-extension
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

If you want to use this project from other repos:

```bash
pip install -e /path/to/optimized-routing-extension
```

This exposes the package as `optimized_routing`.

---

## 🔐 Environment Configuration

Create a `.env` file in the project root with at least:

```env
# BlueFolder
BLUEFOLDER_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BLUEFOLDER_BASE_URL=https://<your-subdomain>.bluefolder.com/api/2.0

# Google Maps (if using Google provider)
GOOGLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Cloudflare URL shortener
CF_SHORTENER_URL=https://your-shortener-worker.workers.dev

# Optional: custom field name (if you ever switch away from link2Url)
CUSTOM_ROUTE_URL_FIELD_NAME=OptimizedRouteURL
```

> If you’re only using Mapbox or OSM, you can omit `GOOGLE_API_KEY` and still use the routing layer.

---

## 🗺️ Routing Providers

The core routing layer supports **multiple providers** via a simple enum in `manager/base.py`:

- `Provider.GOOGLE` – Google Maps directions URL
- `Provider.MAPBOX` – Mapbox Directions (URL-style & API-friendly)
- `Provider.OSM` – OpenStreetMap / OSRM-style URL

You choose the provider when you build your routing manager (usually in `routing.py`):

```python
from optimized_routing.manager.base import Provider
from optimized_routing.manager.google_manager import GoogleMapsRoutingManager
from optimized_routing.manager.mapbox_manager import MapboxRoutingManager
from optimized_routing.manager.osm_manager import OSMMultiStopRoutingManager
```

The `generate_google_route(...)` helper currently uses **Google Maps** internally, but the provider-aware managers let you drop in Mapbox/OSM with similar semantics if you want to extend the CLI later.

---

## 🧠 How It Works (High-Level)

1. **BlueFolderIntegration** pulls:
   - Active users
   - Today’s assignments (with caching)
   - Service request details
   - Customer location details

2. **routing.py** converts those assignments into `RouteStop` objects with:
   - An address string
   - A `ServiceWindow` (AM/PM/ALL_DAY) inferred from the scheduled time
   - A label (`SR-<serviceRequestId>`)

3. A provider-specific manager (`GoogleMapsRoutingManager` etc.):
   - Applies sorting/grouping heuristics to avoid duplicate stops
   - Builds a final multi-stop directions URL

4. `shorten_route_url()` optionally calls your **Cloudflare Worker**:
   - Sends `{ "url": "<long URL>" }` to `<CF_SHORTENER_URL>/new`
   - Expects JSON back with `{ "short": "<short URL>" }`
   - Falls back to the original URL on error

5. The final (possibly shortened) URL is written into `link2Url` for each user.

---

## 🧪 Running Tests

The repo includes a small pytest suite covering BlueFolder integration, CLI behavior, and URL shortening.

```bash
pytest -q
```

You should see all tests passing once your environment and dev dependencies are set up.

---

## 🖥️ CLI Usage

The primary entry point is `optimized_routing.main`.

From the project root (with the venv active):

### 1. Generate routes for all active users (production mode)

```bash
python3 -m optimized_routing.main
```

This will:

1. Fetch active users
2. Determine each user’s origin (work address or fallback)
3. Build an optimized route URL for today’s assignments
4. Shorten the URL (if `CF_SHORTENER_URL` is set)
5. Save the result into the user’s `link2Url` field

### 2. Generate a route for a single user

```bash
python3 -m optimized_routing.main --user 33538043
```

This is useful for ad-hoc testing or a manual “rebuild my route” action.

### 3. Override Origin / Destination

You can override the origin and/or destination when running a one-off route:

```bash
# Origin override only
python3 -m optimized_routing.main --user 33538043     --origin "180 E Hebron Rd, Hebron, ME 04238"

# Destination override only
python3 -m optimized_routing.main --user 33538043     --destination "Portland, ME"

# Override both
python3 -m optimized_routing.main --user 33538043     --origin "Lewiston, ME"     --destination "Bangor, ME"
```

### 4. Preview Stops (no writes to BlueFolder)

To preview the stops that would be used to build a route:

```bash
# Single user
python3 -m optimized_routing.main --preview-stops 33538043

# All active users
python3 -m optimized_routing.main --preview-stops all
```

Preview mode prints:

- Raw enriched assignments
- Converted `RouteStop` objects (AM / PM buckets)
- The final route URL (without writing back to BlueFolder)

---

## 🌩️ Cloudflare Shortener Worker (v2)

The shortener is intentionally minimal. The Python side expects an endpoint:

```text
POST <CF_SHORTENER_URL>/new
Content-Type: application/json

{ "url": "<long-url-here>" }
```

with a JSON response:

```json
{ "short": "https://your-shortener.workers.dev/r/abc123" }
```

The Worker stores `key → URL` pairs in a KV namespace (e.g., `optimized-routing`) and redirects `/r/<key>` to the full URL.

> This keeps the BlueFolder `link2Url` field safely under 255 characters even for long, multi-stop Google Maps routes.

---

## 🔐 BlueFolder Permissions

- Standard API keys cannot see some user details from `users/get.aspx`
- To work around this:
  - The integration uses `users/list.aspx` with `listType="full"` to get a richer user list
  - It falls back to searching the full list when direct lookups aren’t allowed
- `link2Url` is used for storing route URLs because other fields are not reliably editable at this permission level

If you later gain Admin API access, you can extend:

- `bluefolder_integration.update_user_custom_field(...)`
- CLI behavior around which field is used

---

## 🚧 Future Directions

- **Dedicated provider switch** on the CLI (e.g. `--provider mapbox`)
- **Admin-only mode** with richer user field editing
- Persistent caching via **Redis** or a hosted KV store
- A small **web UI** for dispatchers to trigger and view routes

---

## 📄 License

MIT License — feel free to fork, extend, or integrate this with your own BlueFolder workflows.