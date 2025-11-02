"""
Command-line interface for optimizing daily job routes using Google Maps.

This script accepts a list of addresses (job locations) as command-line arguments,
calculates the most efficient route using the Google Maps Directions API, and outputs
a sharable Google Maps URL with the optimized order of stops.

Example:
    python main.py "123 Main St, City, ST" "456 Elm St, City, ST" "789 Oak St, City, ST"
"""

import argparse
from routing import get_optimized_route, build_google_maps_url


def main():
    """
    Parses command-line arguments, optimizes the job route, and prints a Google Maps URL.

    Uses the Google Maps Directions API to determine the most efficient route between
    multiple job locations. The output is a shareable URL that opens Google Maps
    with the route preloaded.

    Raises:
        ValueError: If fewer than one address is provided.
        RuntimeError: If the directions API fails to return a valid route.
    """
    parser = argparse.ArgumentParser(description="Daily route optimizer")
    parser.add_argument("addresses", nargs="+", help="List of job addresses")
    args = parser.parse_args()

    route = get_optimized_route(args.addresses)
    url = build_google_maps_url(
        route["origin"], route["destination"], route["waypoints"]
    )

    print("\U0001F697 Optimized Google Maps URL:\n", url)


if __name__ == "__main__":
    main()
