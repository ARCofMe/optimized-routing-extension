#!/usr/bin/env python3
"""
Quick script to generate *your* optimized route for today.
Uses the existing optimized-routing-extension internals.
"""

import os
from datetime import date

from optimized_routing.bluefolder_integration import BlueFolderIntegration
from optimized_routing.routing import bluefolder_to_routestops, shorten_route_url
from optimized_routing.manager.google_manager import GoogleMapsRoutingManager


# 🔹 CHANGE THIS TO YOUR BlueFolder userId
MY_USER_ID = int(os.getenv("MY_BF_USER_ID", "33538043"))  # your ID or env override


def route_my_calls():
    print(f"\n🔍 Fetching assignments for user {MY_USER_ID} ({date.today()})\n")

    bf = BlueFolderIntegration()

    # 1️⃣ Get assignments for today
    assignments = bf.get_user_assignments_today(MY_USER_ID)

    if not assignments:
        print("⚠️ No assignments found for today.")
        return

    # 2️⃣ Convert to RouteStop objects
    stops = bluefolder_to_routestops(assignments)

    print("📌 Stops for today:")
    for s in stops:
        print(f" - {s.label} @ {s.address} ({s.window.name})")

    # 3️⃣ Determine origin address (work > home fallback)
    origin = bf.get_user_origin_address(MY_USER_ID) or "South Paris, ME"
    print("\n🏁 Origin:", origin)

    # 4️⃣ Build Google Maps route
    mgr = GoogleMapsRoutingManager(origin=origin)
    mgr.add_stops(stops)
    url = mgr.build_route_url()

    print("\n🗺️  Google Maps Route URL (before shortening):")
    print(url)

    # 5️⃣ Try to shorten with Cloudflare Worker
    short = shorten_route_url(url)

    print("\n🔗 Short URL:")
    print(short)

    # 6️⃣ And update user link2Url in BlueFolder
    print("\n💾 Updating BlueFolder user with short URL...")
    #bf.update_user_custom_field(MY_USER_ID, short, field_name="link2Url")

    print("\n✅ DONE — your optimized route is ready.\n")


if __name__ == "__main__":
    route_my_calls()
