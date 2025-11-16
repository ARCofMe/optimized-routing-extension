"""
Main CLI entry point for Optimized Routing Extension.
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

from optimized_routing.manager.google_manager import GoogleMapsRoutingManager
from optimized_routing.manager.mapbox_manager import MapboxRoutingManager
from optimized_routing.manager.osm_manager import OSMRoutingManager

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Routing Manager Factory
# -------------------------------------------------------------------
def get_routing_manager(provider: str, origin: str, destination: str | None):
    provider = provider.lower()

    if provider == "google":
        return GoogleMapsRoutingManager(
            origin=origin,
            destination_override=destination,
        )
    elif provider == "mapbox":
        return MapboxRoutingManager(
            origin=origin,
            destination_override=destination,
        )
    elif provider == "osm":
        return OSMRoutingManager(
            origin=origin,
            destination_override=destination,
        )
    else:
        raise ValueError(f"Unknown provider '{provider}'")


# -------------------------------------------------------------------
# MAIN DAILY ROUTER
# -------------------------------------------------------------------
def run_daily_routing(
    user_override: int | None = None,
    origin_override: str | None = None,
    destination_override: str | None = None,
    provider: str = "google",
):
    """Main runner for routing job."""

    logger.info("[START] Route generation job started at %s", datetime.now())

    bf = BlueFolderIntegration()

    # --- Select users ---
    if user_override:
        logger.info(f"[CLI] Running routing ONLY for user {user_override}")
        all_users = bf.get_active_users()
        users = [u for u in all_users if str(u.get("userId")) == str(user_override)]
        if not users:
            logger.error(f"[ERROR] User {user_override} not found in active list.")
            return
    else:
        users = bf.get_active_users()

    # --- Loop users ---
    for user in users:
        uid = int(user["userId"])
        name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()

        logger.info(f"---- Processing {name} (ID: {uid}) ----")

        # Resolve origin; allow routing layer to apply its own default if missing.
        origin = origin_override or bf.get_user_origin_address(uid)
        if origin_override:
            logger.info("[ORIGIN] Using CLI overridden origin: %s", origin_override)
        elif origin:
            logger.info("[ORIGIN] Using user-specific origin: %s", origin)
        else:
            logger.info(
                "[ORIGIN] No origin found; using routing default inside generator."
            )

        # Destination optional
        destination = destination_override or None

        # Select provider manager
        mgr = get_routing_manager(provider, origin, destination)

        # Generate long route URL
        try:
            long_url = generate_google_route(
                uid,
                origin_address=origin,
                destination_override=destination,
            )
            logger.info("[ROUTE] Generated URL: %s", long_url)
        except Exception as e:
            logger.exception("[ERROR] Route generation failed for %s: %s", uid, e)
            continue

        # Skip users with no assignments
        if not long_url or "No assignments" in long_url:
            logger.info("[SKIP] No assignments for %s — skipping.", name)
            continue

        # Shorten
        try:
            short = shorten_route_url(long_url)
            logger.info("[SHORT] %s → %s", long_url[:60], short)
        except Exception as e:
            logger.exception("[ERROR] Shortener failed: %s", e)
            short = long_url

        # Update BlueFolder
        try:
            bf.update_user_custom_field(uid, short)
            logger.info("[DONE] Updated route URL for %s", name)
        except Exception as e:
            logger.error("[ERROR] BF update failed for %s: %s", name, e)

    logger.info("[FINISHED] Routing job complete.")


# -------------------------------------------------------------------
# PREVIEW MODE HANDLER
# -------------------------------------------------------------------
def handle_preview_mode(args):
    bf = BlueFolderIntegration()

    if args.preview_stops == "all":
        users = bf.get_active_users()
        print(f"\n=== PREVIEW MODE: Showing stops for {len(users)} users ===\n")
        for u in users:
            uid = int(u["userId"])
            origin = bf.get_user_origin_address(uid)
            name = f"{u.get('firstName')} {u.get('lastName')}"
            print(f"\n#### PREVIEW {name} ({uid}) ####")
            preview_user_stops(uid, origin=origin)
    else:
        uid = int(args.preview_stops)
        origin = bf.get_user_origin_address(uid)
        preview_user_stops(uid, origin=origin)


# -------------------------------------------------------------------
# CLI ENTRY POINT
# -------------------------------------------------------------------
def dispatch_cli(args):
    # PREVIEW MODE
    if args.preview_stops:
        handle_preview_mode(args)
        return

    # SINGLE-USER MODE
    if args.user:
        return run_daily_routing(
            user_override=int(args.user),
            origin_override=args.origin,
            destination_override=args.destination,
            provider=args.provider,
        )

    # FULL RUN
    return run_daily_routing(
        user_override=None,
        origin_override=args.origin,
        destination_override=args.destination,
        provider=args.provider,
    )


# -------------------------------------------------------------------
# __main__
# -------------------------------------------------------------------
def __main__():
    parser = argparse.ArgumentParser(description="Optimized Routing Extension")

    parser.add_argument("--user", help="Run routing ONLY for this user ID")
    parser.add_argument("--origin", help="Override origin address")
    parser.add_argument("--destination", help="Override final destination")
    parser.add_argument(
        "--provider", choices=["google", "mapbox", "osm"], default="google"
    )

    parser.add_argument(
        "--preview-stops",
        nargs="?",
        const="all",
        help="Preview stops for a specific user or all users",
    )

    args = parser.parse_args()
    dispatch_cli(args)


if __name__ == "__main__":
    __main__()
