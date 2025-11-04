# 🗺️ Optimized Routing Extension

This extension generates optimized daily service routes using the BlueFolder API and Google Maps Directions API.  
It streamlines technician dispatching by building turn-by-turn routes from service ticket addresses.

---

## 🚀 Features

- 🔄 Pulls daily service tickets from BlueFolder
- 📍 Extracts customer addresses
- 🌐 Geocodes locations using Google Maps
- 🧠 Optimizes travel path using Google's Directions API
- 🗺️ Outputs shareable Google Maps route URLs
- 🧪 Modular, testable, and extensible structure

---

## 🛠️ Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ARCofMe/optimized-routing-extension.git
cd optimized-routing-extension
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .env\Scriptsctivate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root with the following contents:
```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
BLUEFOLDER_API_KEY=your_bluefolder_api_key
BLUEFOLDER_ACCOUNT_NAME=your_subdomain  # e.g. arcme if arcme.bluefolder.com
```

---

## 🧪 Testing

You can validate the core routing logic using:
```bash
python test_google.py
```

This will:
- Sort a sample list of addresses
- Print the optimized route
- Output a clickable Google Maps URL

---

## 🖥️ CLI Usage

To run the tool from the command line:
```bash
python main.py "123 Main St, Hebron ME" "55 Elm St, Auburn ME" "40 Mechanic Falls, ME"
```

It will:
- Fetch an optimized route from Google Maps
- Return a link to view the turn-by-turn navigation

---

## 🧱 Project Structure

```bash
├── config.py             # Route config settings
├── main.py               # CLI entry point
├── routing.py            # Geocoding + optimization logic
├── test_google.py        # Sample unit test
├── .env                  # API credentials (not committed)
├── requirements.txt
└── README.md
```

---

## ✅ TODO

- [ ] Support for multiple techs/routes
- [ ] Add technician availability calendar
- [ ] Schedule-aware routing (time windows, service length)
- [ ] Logging and dashboard display of route metrics
- [ ] Export routes to calendar/CSV
- [ ] Include BlueFolder integration for live ticket pulling

---

## 📄 License

MIT License — see `LICENSE` file.

---

## 🤝 Contributing

PRs are welcome. Please fork the repo, make changes on a feature branch, and open a pull request.

---

## 📬 Contact

Questions, feature requests, or issues?  
Feel free to reach out via GitHub or open an issue in the repo.