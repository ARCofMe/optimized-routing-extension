# Optimized Routing Extension

A Python integration for **BlueFolder** service management that generates optimized
**Google Maps routes** for technicians based on their daily assignments.

---

## 🚀 Features

- 🔗 BlueFolder API integration (Assignments, Customers, Locations)
- 🗺️ Google Maps optimization with deduplication + caching
- ⚡ Parallel enrichment and persistent caching to reduce API usage
- 🧰 CLI and test utility for per-technician route generation
- 🧠 Modular structure (extendable for automation and new API domains)

---

## ⚙️ Setup

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/yourusername/optimized-routing-extension.git
cd optimized-routing-extension
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and populate it with your credentials:

```bash
cp .env.example .env
```

Fill in the following keys:

```
BLUEFOLDER_API_KEY=your_api_key_here
BLUEFOLDER_ACCOUNT_NAME=your_account_name_here
GOOGLE_MAPS_API_KEY=your_google_maps_key_here
```

---

## 🧪 Usage Example

```bash
python test_route_optimizer.py
```

Example output:

```
=== Generating optimized Google Maps route for user 33553227 ===
[ROUTING] Deduplicated 8 redundant stops → 1 unique locations.
Google Maps Route:
https://www.google.com/maps/dir/180+E+Hebron+Rd%2C+Hebron%2C+ME%2C+04238/164+NEW+COUNTY+RD,+Thomaston,+ME/180+E+Hebron+Rd,+Hebron,+ME
```

---

## 🗂️ Project Structure

```
optimized-routing-extension/
│
├── bluefolder_api/
│   ├── base.py
│   ├── client.py
│   ├── customers.py
│   ├── customer_locations.py
│   ├── assignments.py
│   ├── appointments.py
│   ├── users.py
│   └── ...
│
├── manager/
│   ├── base.py
│   ├── google_manager.py
│
├── utils/
│   ├── cache_manager.py
│
├── routing.py
├── bluefolder_integration.py
├── test_route_optimizer.py
├── requirements.txt
└── README.md
```

---

## 🧹 Linting & Formatting

Keep your codebase consistent and readable:

```bash
pip install black isort
black .
isort .
```

---

## 🛣️ Roadmap

| Feature | Status |
|----------|---------|
| BlueFolder API integration | ✅ |
| Google Maps Routing | ✅ |
| Deduplication of stops | ✅ |
| Persistent caching | ✅ |
| CLI Route Generator | 🧩 Planned |
| Fuzzy address matching | 🧩 Planned |
| Route summary export (CSV/PDF) | 🧩 Planned |

---

## 🧾 License

MIT License © 2025 — Developed by [Your Name / Team]