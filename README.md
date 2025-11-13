# Optimized Routing Extension

This extension integrates **BlueFolder**, **Google Maps**, and optional **Cloudflare Workers URL Shortening** to automatically generate daily optimized driving routes for technicians.

---

## ✨ Features

### 🔧 BlueFolder Integration
- Fetches technician assignments for the current day
- Resolves customer and location data with caching to reduce API calls
- Falls back to listType="full" user list when user detail API is restricted
- Saves generated route links into `link2Url` field on user accounts (best available writeable field)

### 🗺️ Google Maps Route Optimization
- Converts service requests into structured route stops
- Applies AM/PM service windows
- Builds a final optimized Google Maps direction URL
- CLI preview mode allows inspection before updating BlueFolder

### 🔗 Cloudflare URL Shortening (Optional)
Long Google Maps URLs can exceed the BlueFolder 255–character field limit.  
This extension supports a **Cloudflare Worker URL shortener**:

```
CF_SHORTENER_URL=https://<your-worker>.workers.dev
```

When configured, the route URL is automatically shortened before saving.

---

## 📦 Directory Structure

```
optimized-routing-extension/
│
├── main.py                    # Main CLI entry point
├── routing.py                 # Route generation + shortener integration
├── bluefolder_integration.py  # User, SR, assignment adapters
│
├── manager/
│   ├── base.py                # RouteStop + enums
│   └── google_manager.py      # Google Maps routing builder
│
├── tests/
│   ├── test_url_shortener.py
│   ├── test_user_update.py
│   └── ...
│
└── utils/
    └── cache_manager.py
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env`:

```
BLUEFOLDER_API_KEY=xxxx
BLUEFOLDER_BASE_URL=https://example.bluefolder.com/api/2.0
GOOGLE_API_KEY=xxxx
CF_SHORTENER_URL=https://your-worker.workers.dev   # optional
```

### 3. Test Your Setup
```
python3 tests/test_url_shortener.py
python3 tests/test_user_update.py
```

### 4. Generate a Route
```
python3 main.py --user 33538043
```

### 5. Preview Stops (no update to BlueFolder)
```
python3 main.py --preview-stops 33538043
python3 main.py --preview-stops all
```

---

## 📝 Notes

### BlueFolder Permissions
Standard API keys **cannot update most user fields**.  
This extension stores route URLs in the **`link2Url`** field because it is the only reliably editable field at this permission level.

### Rate Limiting
BlueFolder enforces strict rate limits.  
`bluefolder_safe` decorator automatically retries after parsing the returned "Try again after" timestamp.

---

## 📘 Future Enhancements
- Dedicated domain route shortening service (self-hosted)
- Full user editing when Admin API scope is granted
- Persistent cloud caching layer (Redis / KV)

---

## 📄 License
MIT License — Free to modify and integrate into your own systems.