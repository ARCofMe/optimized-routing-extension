import argparse
from routing import get_optimized_route, build_google_maps_url

def main():
    parser = argparse.ArgumentParser(description="Daily route optimizer")
    parser.add_argument("addresses", nargs="+", help="List of job addresses")
    args = parser.parse_args()

    route = get_optimized_route(args.addresses)
    url = build_google_maps_url(route['origin'], route['destination'], route['waypoints'])
    
    print("\U0001F697 Optimized Google Maps URL:\n", url)

if __name__ == "__main__":
    main()
