"""
Main CLI entry point for Optimized Routing Extension.
"""

import logging
from datetime import datetime
import argparse
import uuid

from optimized_routing.bluefolder_integration import BlueFolderIntegration
from optimized_routing.routing import (
    generate_route_for_provider,
    shorten_route_url,
    preview_user_stops,
)

from optimized_routing.config import settings
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
    provider: str = settings.default_provider,
    dry_run: bool = False,
    start_date: str | None = None,
    end_date: str | None = None,
    date_range_type: str = "scheduled",
):
    """Main runner for routing job."""

    run_id = uuid.uuid4().hex[:8]
    logger.info("[START] Route generation job %s at %s", run_id, datetime.now())

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

        logger.info(f"---- Processing {name} (ID: {uid}) [run={run_id}] ----")

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

        # Fetch assignments for the desired date range (defaults to today)
        assignments = bf.get_user_assignments_range(
            uid,
            start_date=start_date,
            end_date=end_date,
            date_range_type=date_range_type,
        )
        if not assignments:
            logger.info("[SKIP] No assignments for %s in range %s → %s", name, start_date, end_date)
            continue

        # Select provider manager
        # Generate long route URL using selected provider
        try:
            long_url = generate_route_for_provider(
                provider,
                uid,
                origin_address=origin,
                destination_override=destination,
                assignments=assignments,
            )
            logger.info("[ROUTE] Generated URL: %s [run=%s, user=%s]", long_url, run_id, uid)
        except Exception as e:
            logger.exception("[ERROR] Route generation failed for %s: %s [run=%s]", uid, e, run_id)
            continue

        # Shorten
        try:
            short = shorten_route_url(long_url)
            logger.info("[SHORT] %s → %s", long_url[:60], short)
        except Exception as e:
            logger.exception("[ERROR] Shortener failed: %s", e)
            short = long_url

        # Update BlueFolder
        if dry_run:
            logger.info("[DRY RUN] Skipping BlueFolder update for %s [run=%s]", name, run_id)
        else:
            try:
                bf.update_user_custom_field(uid, short)
                logger.info("[DONE] Updated route URL for %s [run=%s]", name, run_id)
            except Exception as e:
                logger.error("[ERROR] BF update failed for %s: %s [run=%s]", name, e, run_id)

    logger.info("[FINISHED] Routing job complete [run=%s]", run_id)


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
    provider = args.provider or settings.default_provider
    dry_run = bool(getattr(args, "dry_run", False))
    start_date = getattr(args, "start_date", None)
    end_date = getattr(args, "end_date", None)
    date_range_type = getattr(args, "date_range_type", "scheduled")
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
            provider=provider or "google",
            dry_run=dry_run,
            start_date=start_date,
            end_date=end_date,
            date_range_type=date_range_type,
        )

    # FULL RUN
    return run_daily_routing(
        user_override=None,
        origin_override=args.origin,
        destination_override=args.destination,
        provider=provider or "google",
        dry_run=dry_run,
        start_date=start_date,
        end_date=end_date,
        date_range_type=date_range_type,
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
        "--provider", choices=["google", "mapbox", "osm"], default=settings.default_provider
    )

    parser.add_argument(
        "--preview-stops",
        nargs="?",
        const="all",
        help="Preview stops for a specific user or all users",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not update BlueFolder with generated routes.",
    )
    parser.add_argument(
        "--start-date",
        help='Optional start date (BlueFolder format), e.g. "2025.11.08 12:00 AM". Defaults to today.',
    )
    parser.add_argument(
        "--end-date",
        help='Optional end date (BlueFolder format), e.g. "2025.11.08 11:59 PM". Defaults to today.',
    )
    parser.add_argument(
        "--date-range-type",
        choices=["scheduled", "created", "completed"],
        default="scheduled",
        help="Which date field to filter on (default: scheduled).",
    )

    args = parser.parse_args()
    dispatch_cli(args)


if __name__ == "__main__":
    __main__()
