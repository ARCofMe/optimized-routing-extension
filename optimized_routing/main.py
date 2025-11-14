"""
main.py

Daily routing job runner for BlueFolder → Optimized Google Maps URL
with Cloudflare shortener integration + CLI.
"""

import logging
from datetime import datetime
import argparse

from optimized_routing.bluefolder_integration import BlueFolderIntegration
from routing import (
    generate_google_route,
    shorten_route_url,
    preview_user_stops,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


# ----------------------------- CLI HELPERS -----------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optimized Routing Extension CLI"
    )

    parser.add_argument(
        "--user",
        help="Run routing for a specific BlueFolder user ID",
    )

    parser.add_argument(
        "--origin",
        help="Override route origin address",
    )

    parser.add_argument(
        "--destination",
        help="Override route end point (drops a final stop)",
    )

    parser.add_argument(
        "--preview-stops",
        nargs="?",
        const="all",
        help="Preview RouteStops (before generating full URL).",
    )

    return parser


def handle_preview_mode(args):
    """Handle --preview-stops."""
    bf = BlueFolderIntegration()

    if args.preview_stops == "all":
        users = bf.get_active_users()
        print(f"\n=== PREVIEW MODE: Showing stops for {len(users)} users ===\n")
        for u in users:
            uid = int(u["userId"])
            fname = u.get("firstName", "")
            lname = u.get("lastName", "")
            name = (fname + " " + lname).strip() or f"User {uid}"
            print(f"\n#### PREVIEW {name} ({uid}) ####")
            origin = bf.get_user_origin_address(uid)
            preview_user_stops(uid, origin=origin)
        return

    # Single-user preview
    uid = int(args.preview_stops)
    origin = bf.get_user_origin_address(uid)
    preview_user_stops(uid, origin=origin)


def run_daily_routing_single_user(uid: int, args):
    """
    Run routing for a specific user, with optional overrides.
    """
    bf = BlueFolderIntegration()

    name = f"User {uid}"

    origin = (
        args.origin
        or bf.get_user_origin_address(uid)
        or "61 Portland Rd Gray, ME"
    )

    if args.destination:
        logger.info(f"[CLI] Forcing destination to: {args.destination}")

    logger.info(f"[ORIGIN] Using: {origin}")

    if args.destination:
        url = generate_google_route(
            uid,
            origin_address=origin,
            destination_override=args.destination,
        )
    else:
        url = generate_google_route(
            uid,
            origin_address=origin,
        )


    if not url or "No assignments found" in url:
        print("No assignments found.")
        return

    short = shorten_route_url(url)
    print("Generated:", short)

    bf.update_user_custom_field(uid, short)


def run_daily_routing_all(args):
    """
    Normal scheduler: iterate all users.
    """
    bf = BlueFolderIntegration()
    users = bf.get_active_users()

    for u in users:
        uid = int(u["userId"])
        run_daily_routing_single_user(uid, args)


def dispatch_cli(args):
    """
    Unified dispatcher used by actual CLI and tests.
    """
    # Handle preview mode
    if args.preview_stops:
        handle_preview_mode(args)
        return

    # If user passed --user
    if args.user:
        uid = int(args.user)
        run_daily_routing_single_user(uid, args)
        return

    # Otherwise run for all users
    run_daily_routing_all(args)


# ------------------------------ ENTRYPOINT ------------------------------

def __main__():
    """
    Testable entrypoint. (Tests call this!)
    """
    parser = build_parser()
    args = parser.parse_args()
    dispatch_cli(args)


if __name__ == "__main__":
    __main__()

def cli_entry():
    import sys
    dispatch_cli(sys.argv[1:])
