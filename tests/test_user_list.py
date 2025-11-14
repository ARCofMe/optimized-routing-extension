"""
test_bluefolder_users.py
------------------------
Verifies user list and detail access with current BlueFolder API key.
Prints available fields (especially address & office-related ones).
"""

from bluefolder_api.client import BlueFolderClient
from pprint import pprint

print("\n🔐 Testing BlueFolder user list and detail access...\n")

client = BlueFolderClient()

try:
    # --- 1️⃣ Get all users ---
    users = client.users.list_all()
    print(f"✅ Retrieved {len(users)} users via list_all()\n")

    if not users:
        print("⚠️ No users returned. Check permissions or API key scope.")
        raise SystemExit(0)

    # --- 2️⃣ Show key fields for first few users ---
    print("👥 First few users (summary):")
    for u in users[:5]:
        print(
            f"ID: {u.get('id')} | "
            f"Name: {u.get('firstName')} {u.get('lastName')} | "
            f"Inactive: {u.get('inactive')} | "
            f"Type: {u.get('userType')}"
        )
    print()

    # --- 3️⃣ Inspect available keys in first user record ---
    print("🧩 Available keys in basic user record:")
    print(sorted(users[0].keys()))
    print()

    # --- 4️⃣ Try to fetch full details for one user ---
    test_id = users[0].get("id")
    print(f"🔎 Fetching full details for User ID {test_id}...\n")

    detail = client.users.get_by_id(test_id)
    if detail:
        print("✅ User detail retrieved.\n")
        print("🧱 Available fields in full user detail:")
        print(sorted(detail.keys()))
        print()

        # --- 5️⃣ Highlight address-related fields ---
        addr_fields = [
            k for k in detail.keys() if "address" in k.lower() or "office" in k.lower()
        ]
        if addr_fields:
            print("📍 Address/Office-related fields found:")
            for f in addr_fields:
                print(f"  {f}: {detail.get(f)}")
        else:
            print("⚠️ No address/office fields found in user details.")
    else:
        print(
            "⚠️ get_by_id() returned empty or None — user details may still be restricted."
        )

except Exception as e:
    print("❌ Error while testing BlueFolder user access:")
    print(e)
