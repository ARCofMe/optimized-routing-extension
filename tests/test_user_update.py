#!/usr/bin/env python3
"""Manual smoke test for updating BlueFolder user records."""

import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bluefolder_integration import BlueFolderIntegration
from bluefolder_api.client import BlueFolderClient

from dotenv import load_dotenv
import json

load_dotenv()

# -----------------------------
# EDIT THIS: your user ID
# -----------------------------
MY_UID = os.getenv("BLUEFOLDER_TEST_USER_ID")


def pretty(obj):
    """Pretty-print a JSON-serializable object for console output."""
    print(json.dumps(obj, indent=4, default=str))


def main():
    """Exercise the update workflow for a configured test user."""
    print("\n🔐 Initializing BlueFolder client…")
    bf = BlueFolderIntegration(BlueFolderClient())

    print(f"\n🔍 Fetching full record for user {MY_UID} …")
    user = bf.get_user(MY_UID)

    if not user:
        print(f"❌ Could not load user {MY_UID}")
        return

    print("\n📄 Current user profile:")
    pretty(user)

    # --------------------------------------------------------------
    # Prepare new work address values
    # --------------------------------------------------------------
    new_work_street = "Finale Dr"
    new_work_city = "Lewiston"
    new_work_state = "ME"
    new_work_zip = "04240"

    print("\n✏️ Attempting to update WORK address fields…")

    # The update payload MUST contain userId
    payload = {
        "userId": MY_UID,
        "link2Url": "test",
        # "workAddressStreetAddress": new_work_street,
        # "workAddressCity": new_work_city,
        # "workAddressState": new_work_state,
        # "workAddressPostalCode": new_work_zip
    }

    # Use the raw + safe users update
    try:
        result = bf._safe_users_update(payload)
        print("\n✅ Update sent successfully. BlueFolder responded:")
        print(payload)
    except Exception as e:
        print("\n❌ Error during update:")
        print(e)
        return

    print("\n🔁 Re-fetching user to confirm update…")
    updated_user = bf.get_user(MY_UID)

    print("\n📄 Updated user profile:")
    pretty(updated_user)

    print("\n🎉 DONE\n")


if __name__ == "__main__":
    main()
