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
from concurrent.futures import ThreadPoolExecutor
from bluefolder_api.client import BlueFolderClient
from utils.cache_manager import CacheManager

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
        - Caching for performance

    Attributes:
        client (BlueFolderClient): Active API client instance.
    """

    def __init__(self):
        """Initialize the BlueFolder client connection."""
        self.client = BlueFolderClient()

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _enrich_assignment(self, a: dict) -> dict | None:
        """
        Enrich a BlueFolder assignment with service request and location data.

        Args:
            a (dict): Raw assignment object from BlueFolder.

        Returns:
            dict | None: Enriched assignment data, or None if invalid.
        """
        sr_id = a.get("serviceRequestId")
        if not sr_id:
            return None

        # --- Retrieve Service Request details ---
        sr_xml = self.client.service_requests.get_by_id(sr_id)
        sr = sr_xml.find(".//serviceRequest")
        if sr is None:
            return None

        customer_id = sr.findtext("customerId")
        loc_id = sr.findtext("customerLocationId") or customer_id
        subject = sr.findtext("subject") or sr.findtext("description") or "Unlabeled SR"

        # --- Retrieve Location details ---
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
        """
        Retrieve and enrich today's assignments for a specific user.

        Adds caching for both service requests and customer locations to minimize API calls.

        Args:
            user_id (int): BlueFolder user ID.

        Returns:
            list[dict]: Enriched assignment data.
        """
        today = date.today().strftime("%Y.%m.%d")
        start_date = f"{today} 12:00 AM"
        end_date = f"{today} 11:59 PM"

        logger.info(f"Fetching BlueFolder assignments {start_date} → {end_date}")

        # Initialize cache layers
        sr_cache = CacheManager("service_requests", ttl_minutes=60)
        loc_cache = CacheManager("locations", ttl_minutes=120)

        # Fetch assignments
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

            # --- 1️⃣ Service Request (cache-aware) ---
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
            else:
                logger.debug(f"[CACHE] hit: serviceRequest {sr_id}")

            # --- 2️⃣ Location (cache-aware) ---
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
            else:
                logger.debug(f"[CACHE] hit: location {loc_key}")

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
    # Service Request Retrieval
    # -----------------------------------------------------------------------

    def get_user_service_requests_today(self, user_id: int, date_field="dateTimeScheduled") -> list[dict]:
        """
        Retrieve all service requests for a specific user today.

        Args:
            user_id (int): BlueFolder user ID.
            date_field (str): Date field to filter on (default: 'dateTimeScheduled').

        Returns:
            list[dict]: List of service requests.
        """
        today = date.today()
        start_date = today.strftime("%Y.%m.%d 12:00 AM")
        end_date = today.strftime("%Y.%m.%d 11:59 PM")

        sr_cache = CacheManager("service_requests", ttl_minutes=60)
        cache_key = f"{user_id}:{today.isoformat()}"

        cached = sr_cache.get(cache_key)
        if cached:
            logger.debug(f"[CACHE] hit: service_requests for {user_id}")
            return cached

        result = self.client.service_requests.list_for_user_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            date_range_type=date_field,
        )

        sr_cache.set(cache_key, result)
        return result

    # -----------------------------------------------------------------------
    # Appointment Retrieval
    # -----------------------------------------------------------------------

    def get_user_appointments_today(self, user_id: int) -> list[dict]:
        """
        Retrieve and enrich today's appointments for a given user.

        Args:
            user_id (int): BlueFolder user ID.

        Returns:
            list[dict]: Appointment data enriched with address details.
        """
        appt_cache = CacheManager("appointments", ttl_minutes=30)
        cache_key = f"{user_id}:{date.today().isoformat()}"

        cached = appt_cache.get(cache_key)
        if cached:
            logger.debug(f"[CACHE] hit: appointments for {user_id}")
            return cached

        appts = self.client.appointments.get_appointments_for_routing(user_id)
        enriched = []
        location_cache = {}

        for appt in appts:
            customer_id = appt.get("customerId")
            if not customer_id or customer_id == "0":
                enriched.append(appt)
                continue

            if customer_id not in location_cache:
                locs = self.client.customer_locations.get_by_customer_id(customer_id)
                location_cache[customer_id] = locs[0] if locs else {}

            loc = location_cache[customer_id]
            appt.update({
                "address": loc.get("addressStreet", ""),
                "city": loc.get("addressCity", ""),
                "state": loc.get("addressState", ""),
                "zip": loc.get("addressPostalCode", ""),
            })
            enriched.append(appt)

        appt_cache.set(cache_key, enriched)
        return enriched

    # -----------------------------------------------------------------------
    # All Service Requests
    # -----------------------------------------------------------------------

    def get_all_service_requests_today(self, date_field="dateTimeScheduled") -> list[dict]:
        """
        Retrieve all service requests for all users for the current day.

        Args:
            date_field (str): BlueFolder field to filter by.

        Returns:
            list[dict]: List of all service requests for the current day.
        """
        today = date.today()
        start_date = datetime(today.year, today.month, today.day, 0, 0).strftime("%Y.%m.%d %I:%M %p")
        end_date = datetime(today.year, today.month, today.day, 23, 59).strftime("%Y.%m.%d %I:%M %p")

        logger.info(f"Using date range: {start_date} → {end_date}")

        return self.client.service_requests.list_for_range(
            start_date=start_date,
            end_date=end_date,
            date_field=date_field,
        )
