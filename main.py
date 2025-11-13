#!/usr/bin/env python3
"""
Daily Route Updater for BlueFolder
----------------------------------
For each active technician:
    - Fetch today's assignments
    - Determine their route origin (work > home > default)
    - Generate optimized Google Maps route URL
    - Store that URL in their configured custom field

Uses:
    - bluefolder_integration.BlueFolderIntegration
    - routing.generate_google_route
"""

import logging
from datetime import datetime
from dotenv import load_dotenv
import os
from bluefolder_api.client import BlueFolderClient

from bluefolder_integration import BlueFolderIntegration
from routing import generate_google_route

# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
load_dotenv()

DEFAULT_ORIGIN = os.getenv("DEFAULT_ORIGIN", "South Paris, ME")
CUSTOM_FIELD_NAME = os.getenv("CUSTOM_ROUTE_URL_FIELD_NAME", "OptimizedRouteURL")


# -------------------------------------------------------------------
# Daily Route Processor
# -------------------------------------------------------------------
def run_daily_routing():
    logger.info("[START] Route generation job started at %s", datetime.now())

    # Initialize API + integration
    client = BlueFolderClient()
    bf = BlueFolderIntegration(client)

    # Step 1 — Get active users
    users = bf.get_active_users()
    if not users:
        logger.warning("[ABORT] No active users found.")
        return

    logger.info("[USERS] Processing %d active users.", len(users))

    # Step 2 — Process each user
    for u in users:
        uid = u.get("userId") or u.get("id")
        if not uid:
            logger.warning("Skipping user with missing ID: %s", u)
            continue

        name = f"{u.get('firstName', '')} {u.get('lastName', '')}".strip()
        logger.info("---- Processing %s (ID: %s) ----", name, uid)

        # Step 3 — Resolve origin address
        origin = bf.get_user_origin_address(uid)
        if origin:
            logger.info(f"[ORIGIN] Using user-specific origin: {origin}")
        else:
            origin = DEFAULT_ORIGIN
            logger.info(f"[ORIGIN] No work/home address -> using default: {origin}")

        # Step 4 — Generate route URL
        route_url = generate_google_route(int(uid), origin_address=origin)

        if "No assignments" in route_url:
            logger.info(f"[ROUTE] No assignments for {name}. Skipping update.")
            continue

        logger.info(f"[ROUTE] Generated URL: {route_url}")

        # Step 5 — Update custom field
        bf.update_user_custom_field(
            int(uid),
            field_value=route_url,
            field_name=CUSTOM_FIELD_NAME,
        )

        logger.info("[DONE] Updated route for %s", name)

    logger.info("[COMPLETE] Daily route job finished.")


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    run_daily_routing()
