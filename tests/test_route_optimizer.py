"""Manual helper for exercising the routing workflow end to end."""

from bluefolder_integration import BlueFolderIntegration
from routing import generate_google_route


def test_route_for_user():
    """Test route optimization + map URL generation for a specific BlueFolder user."""
    uid = 12345
    print(f"=== Generating optimized Google Maps route for user {uid} ===")


    origin = "180 E Hebron Rd, Hebron, ME 04238"  # your shop/home base
    bf = BlueFolderIntegration()

    # Fetch today's assignments
    assignments = bf.get_user_assignments_today(uid)
    print(f"Found {len(assignments)} assignments for user {uid}\n")

    # Print assignments with richer info
    for a in assignments:
        desc = a.get("description") or "No description"
        addr = a.get("address") or "?"
        city = a.get("city") or "?"
        print(f" - {desc} → {addr}, {city}")

    print("\n=== Generating Google Maps Route ===")
    route_url = generate_google_route(uid, origin_address=origin)
    print(f"Google Maps Route URL:\n{route_url}\n")


if __name__ == "__main__":
    # Example: replace with any valid BlueFolder userId
    test_route_for_user(33553227)
