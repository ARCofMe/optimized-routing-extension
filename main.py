import sys
from datetime import datetime

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bluefolder-api')))

from bluefolder_api.appointments import BlueFolderAppointments
from bluefolder_api.users import BlueFolderUsers
from .routing import get_optimized_route, build_google_maps_url

# Helpers
def parse_date():
    if len(sys.argv) > 1:
        try:
            return datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD.")
            sys.exit(1)
    return datetime.today().date()


def get_users_with_appointments(appointments):
    """Group appointment data by userId."""
    user_map = {}
    for appt in appointments:
        uid = appt["userId"]
        addr = appt.get("location", {}).get("address1", "")
        if uid and addr:
            user_map.setdefault(uid, []).append(addr)
    return user_map


def run_for_user(user_id, addresses):
    """Generate a Google Maps route for one tech."""
    if not addresses:
        print(f"❌ No addresses found for user {user_id}")
        return

    try:
        result = get_optimized_route(addresses)
        url = build_google_maps_url(
            result["origin"], result["destination"], result["waypoints"]
        )
        print(f"\n📍 User ID: {user_id}")
        print(f"🗺️  Google Maps URL:\n{url}")
    except Exception as e:
        print(f"⚠️ Error building route for user {user_id}: {e}")


def main():
    run_date = parse_date()

    # Get all appointments for the day
    print(f"📅 Fetching appointments for {run_date.isoformat()}...")
    api = BlueFolderAppointments()
    appointments = api.list(startDate=run_date.isoformat(), endDate=run_date.isoformat())

    if not appointments:
        print("🔍 No appointments found.")
        return

    # Optional: single user override
    if len(sys.argv) > 2:
        user_id = int(sys.argv[2])
        user_appointments = [appt for appt in appointments if appt["userId"] == user_id]
        addresses = [
            appt["location"]["address1"]
            for appt in user_appointments
            if appt.get("location", {}).get("address1")
        ]
        run_for_user(user_id, addresses)
    else:
        user_map = get_users_with_appointments(appointments)
        for user_id, addresses in user_map.items():
            run_for_user(user_id, addresses)


if __name__ == "__main__":
    main()
