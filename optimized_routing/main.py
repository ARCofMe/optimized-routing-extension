"""
main.py

Optimized Routing Extension – now with provider selection:
    --provider google
    --provider osm
    --provider ors-native
"""

import logging
from datetime import datetime
import argparse

from optimized_routing.bluefolder_integration import BlueFolderIntegration
from optimized_routing.routing import (
    generate_google_route,
    shorten_route_url,
    preview_user_stops,
)

# Routing managers
from optimized_routing.manager.google_manager import GoogleMapsRoutingManager
from optimized_routing.manager.osm_manager import OSMRoutingManager
from optimized_routing.manager.ors_native_manager import ORSNativeRoutingManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Routing Provider Factory
# ---------------------------------------------------------------------------
def get_routing_manager(provider: str, origin: str, destination: str):
    provider = provider.lower()

    if provider == "google":
        return GoogleMapsRoutingManager(
            origin=origin,
            destination_override=destination or None,
        )

    if provider == "osm":
        return OSMRoutingManager(
            origin=origin,
            destination_override=destination or None,
        )

    if provider == "ors-native":
        return ORSNativeRoutingManager(
            origin=origin,
            destination_override=destination or None,
        )

    raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# Daily run
# ---------------------------------------------------------------------------
def run_daily_routing(
    provider: str, origin_override: str = None, destination_override: str = None
):
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

        # Determine origin
        origin = origin_override or bf.get_user_origin_address(uid)
        if origin:
            logger.info("[ORIGIN] Using origin: %s", origin)
        else:
            origin = "61 Portland Rd, Gray ME"
            logger.info("[ORIGIN] Using fallback: %s", origin)

        # Determine destination
        destination = destination_override or None

        # Select provider
        mgr = get_routing_manager(provider, origin, destination)

        # Fetch assignments
        assignments = bf.get_user_assignments_today(uid)
        if not assignments:
            logger.info("[SKIP] No assignments for %s — skipping update.", name)
            continue

        # Convert to stops
        from optimized_routing.routing import bluefolder_to_routestops

        stops = bluefolder_to_routestops(assignments)
        mgr.add_stops(stops)

        # Generate route URL
        try:
            route_url = mgr.build_route_url()
            logger.info("[ROUTE] Provider '%s' URL: %s", provider, route_url)
        except Exception as e:
            logger.exception("[ERROR] Failed generating route for %s: %s", uid, e)
            continue

        # Shorten (optional)
        short = shorten_route_url(route_url)

        # Save to BlueFolder
        bf.update_user_custom_field(int(uid), short)
        logger.info("[DONE] Updated BF route field for %s", name)

    logger.info("[FINISHED] Daily routing job complete.")


# ---------------------------------------------------------------------------
# Preview mode
# ---------------------------------------------------------------------------
def handle_preview_mode(args):
    bf = BlueFolderIntegration()

    if args.preview_stops == "all":
        users = bf.get_active_users()
        print(f"\n=== PREVIEW MODE: Showing stops for {len(users)} users ===\n")
        for u in users:
            uid = int(u["userId"])
            origin = args.origin or bf.get_user_origin_address(uid)
            preview_user_stops(uid, origin=origin)
    else:
        uid = int(args.preview_stops)
        origin = args.origin or BlueFolderIntegration().get_user_origin_address(uid)
        preview_user_stops(uid, origin=origin)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def dispatch_cli(args):
    # Preview mode first
    if args.preview_stops:
        handle_preview_mode(args)
        return

    # Normal routing job
    run_daily_routing(
        provider=args.provider,
        origin_override=args.origin,
        destination_override=args.destination,
    )


def __main__():
    parser = argparse.ArgumentParser(description="Optimized Routing Extension")

    parser.add_argument(
        "--provider",
        default="google",
        choices=["google", "osm", "ors-native"],
        help="Routing provider to use.",
    )

    parser.add_argument(
        "--user",
        help="Route for a single user (not implemented in provider mode yet).",
    )

    parser.add_argument("--origin", help="Override route origin")
    parser.add_argument("--destination", help="Override route final destination")

    parser.add_argument(
        "--preview-stops",
        nargs="?",
        const="all",
        help="Preview RouteStops for a user or all users",
    )

    args = parser.parse_args()
    dispatch_cli(args)


if __name__ == "__main__":
    __main__()
