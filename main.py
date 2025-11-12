"""
main.py
Daily orchestration entry point for the Optimized Routing Extension.

- Iterates over all active technicians.
- Uses routing.generate_google_route() to get optimized route URLs.
- Updates each technician's BlueFolder record with the generated link.
"""

import logging
from datetime import datetime
from bluefolder_integration import BlueFolderIntegration
from routing import generate_google_route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_daily_routing():
    """
    Pull all active BlueFolder users, generate optimized routes,
    and push route URLs into their BlueFolder custom field.
    """
    logger.info(f"[START] Route generation job started at {datetime.now()}")
    bf = BlueFolderIntegration()

    users = bf.get_active_users()  # assumes you have this method
    if not users:
        logger.warning("No active users found.")
        return

    for user in users:
        user_id = user.get("id")
        user_name = f"{user.get("firstName")} {user.get("lastName", "Unknown")}"
        logger.info(f"Processing routes for {user_name} (User ID: {user_id})")

        try:
            route_url = generate_google_route(user_id)
            if "No assignments" in route_url:
                logger.info(f"No assignments found for {user_name}.")
                continue

            # Update the route URL into the technician’s BlueFolder custom field
            bf.update_user_custom_field(
                user_id=user_id,
                field_name="DailyRouteURL",  # matches your BlueFolder custom field
                field_value=route_url
            )

            logger.info(f"✅ Updated route for {user_name}: {route_url}")

        except Exception as e:
            logger.exception(f"❌ Error processing user {user_name}: {e}")
        logger.info("--------------------------------------------------------------")

    logger.info(f"[END] Route generation job completed at {datetime.now()}")


if __name__ == "__main__":
    run_daily_routing()
