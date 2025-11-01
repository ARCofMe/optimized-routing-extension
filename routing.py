import os
from dotenv import load_dotenv
import googlemaps
from urllib.parse import quote_plus

load_dotenv()
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))


def geocode_address(address):
    result = gmaps.geocode(address)
    if not result:
        raise ValueError(f"Could not geocode address: {address}")
    location = result[0]["geometry"]["location"]
    return [location["lng"], location["lat"]]


def build_google_maps_url(addresses):
    if len(addresses) < 2:
        raise ValueError("At least 2 addresses (start and end) required.")

    origin = quote_plus(addresses[0])
    destination = quote_plus(addresses[-1])
    waypoints = "|".join(quote_plus(addr) for addr in addresses[1:-1])  # midpoints only

    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin}"
        f"&destination={destination}"
        f"&waypoints=optimize:true|{waypoints}"
    )
