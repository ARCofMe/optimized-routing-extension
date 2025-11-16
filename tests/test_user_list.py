"""Optional live test of BlueFolder user listing; requires real credentials."""

import os
import pytest
from bluefolder_api.client import BlueFolderClient


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_BF_TESTS"),
    reason="Set RUN_LIVE_BF_TESTS=1 with real BlueFolder credentials to run.",
)
def test_user_list_and_detail_live():
    """Exercise list/get user endpoints when real credentials are present."""
    client = BlueFolderClient()

    users = client.users.list_all()
    assert isinstance(users, list)
    assert users, "No users returned; check credentials or permissions."

    # Ensure basic keys exist on first record
    u = users[0]
    assert "id" in u and "firstName" in u and "lastName" in u

    # Fetch a single user detail
    detail = client.users.get_by_id(u["id"])
    assert detail, "Expected detail payload for user."
