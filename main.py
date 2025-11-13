"""
main.py

Daily routing job runner for BlueFolder → Optimized Google Maps URL
with Cloudflare shortener integration.
"""

import logging
from datetime import datetime
import argparse
from bluefolder_integration import BlueFolderIntegration
from routing import generate_google_route, shorten_route_url, preview_user_stops

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


def run_daily_routing():
    """Main entry point for generating + shortening + updating routes."""
    logger.info("[START] Route generation job started at %s", datetime.now())

    bf = BlueFolderIntegration()
    users = bf.get_active_users()

    if not users:
        logger.warning("No active users found.")
        return

    for user in users:
        uid = user.get("userId") or user.get("id")
        name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()

        logger.info("---- Processing %s (ID: %s) ----", name, uid)

        # 1️⃣ Get user address for their origin (work or home)
        origin = bf.get_user_origin_address(uid)
        if origin:
            logger.info("[ORIGIN] Using user-specific origin: %s", origin)
        else:
            origin = "61 Portland Rd Gray, ME"
            logger.info("[ORIGIN] No user origin found — using fallback: %s", origin)

        # 2️⃣ Generate long Google Maps route URL
        try:
            route_url = generate_google_route(int(uid), origin_address=origin)
            logger.info("[ROUTE] Generated URL: %s", route_url)
        except Exception as e:
            logger.exception("[ERROR] Failed generating route for user %s: %s", uid, e)
            continue

        # 🚫 Skip users with no assignments
        if not route_url or "No assignments found" in route_url:
            logger.info("[SKIP] No assignments for %s — skipping update.", name)
            continue

        # 3️⃣ Shorten the URL via Cloudflare Worker
        try:
            short_url = shorten_route_url(route_url)
            logger.info("[SHORT] Short URL: %s", short_url)
        except Exception as e:
            logger.exception("[ERROR] Failed shortening route URL for %s: %s", uid, e)
            short_url = route_url  # fallback

        # 4️⃣ Update BlueFolder user with shortened URL
        try:
            bf.update_user_custom_field(int(uid), short_url)
            logger.info("[DONE] Updated route for %s", name)
        except Exception as e:
            logger.error("[ERROR] Failed updating BF custom field for %s: %s", name, e)

    logger.info("[FINISHED] Daily routing job complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimized Routing Extension")
    parser.add_argument(
        "--preview-stops",
        nargs="?",
        const="all",
        help="Preview RouteStops for a user (e.g., --preview-stops 33538043 or --preview-stops all)",
    )

    args = parser.parse_args()

    # CLI: Preview-only mode
    if args.preview_stops:
        bf = BlueFolderIntegration()

        if args.preview_stops == "all":
            users = bf.get_active_users()
            print(f"\n=== PREVIEW MODE: Showing stops for {len(users)} users ===\n")
            for u in users:
                uid = int(u.get("userId"))
                name = f"{u.get('firstName')} {u.get('lastName')}"
                print(f"\n#### PREVIEW {name} ({uid}) ####")
                origin = bf.get_user_origin_address(uid)
                preview_user_stops(uid, origin=origin)
        else:
            try:
                uid = int(args.preview_stops)
            except:
                raise ValueError("User ID must be a number or 'all'")

            name = args.preview_stops
            origin = BlueFolderIntegration().get_user_origin_address(uid)
            preview_user_stops(uid, origin=origin)

        exit(0)

    # Normal scheduled run
    run_daily_routing()

