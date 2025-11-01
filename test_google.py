from routing import build_google_maps_url

addresses = [
    "180 E Hebron Rd, Hebron, ME",
    "14 Maple Ln, Harpswell,ME,USA",
    "37 County Xing, Brunswick, ME",
    "3 Bickford Dr, Topsham, ME",
    "46 Indian Cove, Phippsburg, ME",
    "46 Elm St, Topsham, ME",
]

maps_url = build_google_maps_url(addresses)
print("🚗 Optimized Google Maps URL:\n", maps_url)
