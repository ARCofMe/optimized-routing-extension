# 🗺️ Daily Routing Extension

This extension generates optimized daily routes for service technicians using ticket data from BlueFolder and Google Maps Directions API.

It is designed to streamline dispatching and improve on-site efficiency for service-based businesses.

---

## 🚀 Features

- 🔄 Pulls daily service tickets from the BlueFolder API  
- 📍 Extracts customer locations from ticket data  
- 🧠 Geocodes addresses using Google Maps API  
- 🧭 Optimizes travel routes and generates turn-by-turn Google Maps URLs  
- 🧪 Modular and testable architecture  

---

## 🛠 Setup

### 1. Clone the repository
```bash
git clone https://github.com/ARCofMe/daily-routing-extension.git
cd daily-routing-extension
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root with the following:
```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
BLUEFOLDER_API_KEY=your_bluefolder_api_key
BLUEFOLDER_ACCOUNT_NAME=your_bluefolder_subdomain  # e.g. yourcompany if URL is yourcompany.bluefolder.com
```

---

## 🧪 Testing

Run the test script to verify setup:
```bash
python test_routing.py
```

This will print the optimized address order and a shareable Google Maps route URL.

---

## 📁 File Structure

```bash
├── bluefolder_api.py       # BlueFolder API wrapper
├── routing.py              # Geocoding + route optimization logic
├── test_routing.py         # Test file for validating routing output
├── requirements.txt
├── .env
└── README.md
```

---

## ✅ TODO

- [ ] Support multiple technicians  
- [ ] Add time-window-based scheduling  
- [ ] Integrate Google Calendar sync  
- [ ] Add error logging and dashboard output  

---

## 📄 License

MIT License — see `LICENSE` file.
