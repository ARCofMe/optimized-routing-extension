from routing import get_optimized_route, build_google_maps_url


addresses = [
    "180 E Hebron Rd, Hebron, ME",
    "14 Maple Ln, Harpswell, ME, USA",
    "37 County Xing, Brunswick, ME",
    "3 Bickford Dr, Topsham, ME",
    "46 Indian Cove, Phippsburg, ME",
    "46 Elm St, Topsham, ME",
    "180 E Hebron Rd, Hebron, ME",
]


route = get_optimized_route(addresses)
url = build_google_maps_url(route["origin"], route["destination"], route["waypoints"])


print("\U0001F697 Optimized Google Maps URL:\n", url)


