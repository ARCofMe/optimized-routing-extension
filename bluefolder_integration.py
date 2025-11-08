from datetime import date, datetime
from bluefolder_api.client import BlueFolderClient

class BlueFolderIntegration:
    def __init__(self):
        self.client = BlueFolderClient()

    def get_user_appointments_today(self, user_id: int):
        appts = self.client.appointments.get_appointments_for_routing(user_id)
        enriched = []

        # simple cache to avoid duplicate lookups
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
                "state": loc.get("AddressState", ""),
                "zip": loc.get("zaddressPostalCode", ""),
            })
            enriched.append(appt)

        return enriched

    def get_user_service_requests_today(
        self,
        user_id: int,
        date_field: str = "dateTimeScheduled",
        start_date: str = None,
        end_date: str = None,
    ):
        """Get all service requests for a user for today's schedule (or a custom date range)."""

        # Default to today in BlueFolder format if no range passed
        if not start_date or not end_date:
            today = date.today()
            start_date = today.strftime("%Y.%m.%d 12:00 AM")
            end_date = today.strftime("%Y.%m.%d 11:59 PM")
            
        print(f"Using date range: {start_date} → {end_date}")

        return self.client.service_requests.list_for_user_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            date_range_type=date_field,
        )
        
    def get_all_service_requests_today(self, date_field="dateTimeScheduled"):
        today = date.today()
        start_date = datetime(today.year, today.month, today.day, 0, 0).strftime("%Y.%m.%d %I:%M %p")
        end_date = datetime(today.year, today.month, today.day, 23, 59).strftime("%Y.%m.%d %I:%M %p")

        print(f"Using date range: {start_date} → {end_date}")

        return self.client.service_requests.list_for_range(
            start_date=start_date,
            end_date=end_date,
            date_field=date_field,
        )

    def get_user_assignments_today(self, user_id: int):
        today = date.today().strftime("%Y.%m.%d")
        start_date = f"{today} 12:00 AM"
        end_date = f"{today} 11:59 PM"
        print(f"Using date range: {start_date} → {end_date}")

        return self.client.assignments.list_for_user_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            date_range_type="scheduled",
        )
        
    def get_user_assignments_today(self, user_id: int):
        today = date.today().strftime("%Y.%m.%d")
        start_date = f"{today} 12:00 AM"
        end_date   = f"{today} 11:59 PM"
        print(f"Using date range: {start_date} → {end_date}")

        assignments = self.client.assignments.list_for_user_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            date_range_type="scheduled"
        )

        enriched = []
        for a in assignments:
            sr_id = a.get("serviceRequestId")
            if not sr_id:
                continue

            # --- Service Request details ---
            sr_xml = self.client.service_requests.get_by_id(sr_id)
            sr = sr_xml.find(".//serviceRequest")
            if sr is None:
                continue
            else:
                customer_id = sr.get("customerId")

            loc_id = sr.findtext("customerLocationId") or sr.findtext("customerId")
            subject = sr.findtext("subject")

            # --- Location details ---
            address = city = state = zip_code = None
            if loc_id:
                loc_xml = self.client.customers.get_location_by_id(loc_id)
                loc = loc_xml.find(".//customerLocation")
                if loc is not None:
                    address = loc.findtext("addressStreet")
                    city    = loc.findtext("addressCity")
                    state   = loc.findtext("addressState")
                    zip_code= loc.findtext("addressPostalCode")

            enriched.append({
                "assignmentId": a["assignmentId"],
                "serviceRequestId": sr_id,
                "subject": subject,
                "address": address,
                "city": city,
                "state": state,
                "zip": zip_code,
                "start": a["start"],
                "end": a["end"],
                "isComplete": a["isComplete"]
            })

        return enriched