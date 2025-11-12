"""
bluefolder_integration.py

Integration layer between BlueFolder API and routing extensions.

Responsibilities:
    - Retrieve technician assignments, service requests, and appointments.
    - Enrich raw data with location and subject metadata.
    - Cache service requests and locations to reduce API usage.
    - Provide clean data for routing and mapping managers.

Dependencies:
    - bluefolder_api.client.BlueFolderClient
    - utils.cache_manager.CacheManager
"""

from datetime import date, datetime
import logging
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from bluefolder_api.client import BlueFolderClient
from utils.cache_manager import CacheManager

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLASS: BlueFolderIntegration
# ---------------------------------------------------------------------------

class BlueFolderIntegration:
    """
    Provides a high-level interface for retrieving and enriching BlueFolder data.

    Handles:
        - Technician assignments
        - Service request lookups
        - Appointment retrieval
        - User management
        - Caching for performance

    Attributes:
        client (BlueFolderClient): Active API client instance.
    """

    def __init__(self, client: BlueFolderClient = None):
        """Initialize the BlueFolder client connection."""
        self.client = client or BlueFolderClient()

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _enrich_assignment(self, a: dict) -> dict | None:
        sr_id = a.get("serviceRequestId")
        if not sr_id:
            return None

        sr_xml = self.client.service_requests.get_by_id(sr_id)
        sr = sr_xml.find(".//serviceRequest")
        if sr is None:
            return None

        customer_id = sr.findtext("customerId")
        loc_id = sr.findtext("customerLocationId") or customer_id
        subject = sr.findtext("subject") or sr.findtext("description") or "Unlabeled SR"

        address = city = state = zip_code = None
        if loc_id:
            loc_data = self.client.customers.get_location_by_id(loc_id)

            if isinstance(loc_data, dict):
                address = loc_data.get("address", "")
                city = loc_data.get("city", "")
                state = loc_data.get("state", "")
                zip_code = loc_data.get("zip", "")
            else:
                loc = loc_data.find(".//customerLocation")
                if loc is not None:
                    address = loc.findtext("addressStreet")
                    city = loc.findtext("addressCity")
                    state = loc.findtext("addressState")
                    zip_code = loc.findtext("addressPostalCode")

        return {
            "assignmentId": a.get("assignmentId"),
            "serviceRequestId": sr_id,
            "subject": subject,
            "address": address,
            "city": city,
            "state": state,
            "zip": zip_code,
            "start": a.get("start"),
            "end": a.get("end"),
            "isComplete": a.get("isComplete"),
        }

    # -----------------------------------------------------------------------
    # Assignment Retrieval
    # -----------------------------------------------------------------------

    def get_user_assignments_today(self, user_id: int) -> list[dict]:
        today = date.today().strftime("%Y.%m.%d")
        start_date = f"{today} 12:00 AM"
        end_date = f"{today} 11:59 PM"

        logger.info(f"Fetching BlueFolder assignments {start_date} → {end_date}")

        sr_cache = CacheManager("service_requests", ttl_minutes=60)
        loc_cache = CacheManager("locations", ttl_minutes=120)

        assignments = self.client.assignments.list_for_user_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            date_range_type="scheduled",
        )

        enriched = []
        for a in assignments:
            sr_id = a.get("serviceRequestId")
            if not sr_id:
                continue

            sr_data = sr_cache.get(sr_id)
            if not sr_data:
                sr_xml = self.client.service_requests.get_by_id(sr_id)
                sr = sr_xml.find(".//serviceRequest")
                if sr is None:
                    continue
                sr_data = {
                    "customerId": sr.findtext("customerId"),
                    "locationId": sr.findtext("customerLocationId"),
                    "subject": (
                        sr.findtext("description")
                        or sr.findtext("subject")
                        or sr.findtext(".//title")
                        or "Unlabeled Service Request"
                    ),
                }
                sr_cache.set(sr_id, sr_data)

            customer_id = sr_data.get("customerId")
            location_id = sr_data.get("locationId")
            loc_key = f"{customer_id}:{location_id}"
            loc_data = loc_cache.get(loc_key)

            if not loc_data and customer_id and location_id:
                try:
                    loc_xml = self.client.customers.get_location_by_id(customer_id, location_id)
                    loc = loc_xml.find(".//customerLocation")
                    if loc is not None:
                        loc_data = {
                            "address": loc.findtext("addressStreet"),
                            "city": loc.findtext("addressCity"),
                            "state": loc.findtext("addressState"),
                            "zip": loc.findtext("addressPostalCode"),
                        }
                        loc_cache.set(loc_key, loc_data)
                except Exception as e:
                    logger.warning(f"[CACHE] location fetch failed for {loc_key}: {e}")

            enriched.append({
                "assignmentId": a.get("assignmentId"),
                "serviceRequestId": sr_id,
                "subject": sr_data.get("subject"),
                "address": loc_data.get("address") if loc_data else None,
                "city": loc_data.get("city") if loc_data else None,
                "state": loc_data.get("state") if loc_data else None,
                "zip": loc_data.get("zip") if loc_data else None,
                "start": a.get("start"),
                "end": a.get("end"),
                "isComplete": a.get("isComplete"),
            })

        logger.info(f"[CACHE] saved: {len(sr_cache.data)} SRs, {len(loc_cache.data)} locations")
        return enriched

    # -----------------------------------------------------------------------
    # User Management
    # -----------------------------------------------------------------------

    def get_users(self, full: bool = False):
        """
        Retrieve all users from BlueFolder.
        The SDK only supports the basic user list (id, names, etc.).
        The 'full' flag is ignored here for compatibility.
        """
        try:
            users = self.client.users.list_all()
            logger.info(f"[USERS] Retrieved {len(users)} users (basic list).")
            return users
        except Exception as e:
            logger.exception(f"[USERS] Failed to retrieve user list: {e}")
            return []

    def get_user(self, user_id: int):
        """
        Retrieve a single user's record using the SDK.
        """
        try:
            user = self.client.users.get_by_id(user_id)
            if not user:
                logger.warning(f"[USERS] No user found with ID {user_id}")
                # 🔍 temporary debug: show what the SDK saw
                raw = getattr(self.client.users, "last_response", None)
                if raw is not None:
                    print("\n----- RAW BlueFolder XML -----\n", raw, "\n-----------------------------\n")
                return None

            logger.info(f"[USERS] Retrieved {user.get('displayName', 'Unknown')} (ID: {user_id})")
            return user
        except Exception as e:
            logger.exception(f"[USERS] Failed to fetch user {user_id}: {e}")
            return None

    def edit_user(self, user_id: int, **fields):
        """
        Edit a BlueFolder user through the SDK’s update() call.
        Some SDK builds expect the full payload including userId inside the dict.
        """
        try:
            payload = {"userId": user_id}
            payload.update({k: v for k, v in fields.items() if v is not None})

            logger.info(f"[USERS] Updating user {user_id} with fields: {payload}")
            result = self.client.users.update(payload)
            logger.info(f"[USERS] Successfully updated user {user_id}")
            return result
        except Exception as e:
            logger.exception(f"[USERS] Failed to edit user {user_id}: {e}")
            return None

    def get_active_users(self):
        """Return active users using the client's built-in list_active()."""
        try:
            users = self.client.users.list_active()
            logger.info(f"[USERS] Retrieved {len(users)} active users.")
            return users
        except Exception as e:
            logger.exception(f"[USERS] Failed to fetch active users: {e}")
            return []




    def update_user_custom_field(self, user_id: int, field_value: str, field_name: str = None):
        """Update a BlueFolder user's custom field using an env-based or provided field name."""
        try:
            # Fallback order: explicit arg → env var → hardcoded default
            field_name = field_name or os.getenv("CUSTOM_ROUTE_URL_FIELD_NAME", "OptimizedRouteURL")

            payload = {
                "CustomFields": {
                    "CustomField": {
                        "Name": field_name,
                        "Value": field_value
                    }
                },
                "userId": user_id
            }

            result = self.client.users.update(params=payload)
            logger.info(f"[USERS] Updated {field_name} for user {user_id}.")
            return result

        except Exception as e:
            logger.exception(f"[USERS] Failed to update custom field for user {user_id}: {e}")
            return None

