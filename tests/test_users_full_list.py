"""Optional live test hitting BlueFolder listType='full'; requires credentials."""

import os
import xml.etree.ElementTree as ET
import pytest
from bluefolder_api.client import BlueFolderClient


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_BF_TESTS"),
    reason="Set RUN_LIVE_BF_TESTS=1 with real BlueFolder credentials to run.",
)
def test_users_full_list_live():
    """Exercise listType=full endpoint and ensure users are returned."""
    client = BlueFolderClient()

    xml_payload = """<request>
        <userList>
            <listType>full</listType>
        </userList>
    </request>"""

    url = f"{client.base_url}/users/list.aspx"

    response = client.session.post(
        url,
        data=xml_payload.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
        auth=(client.api_key, "x"),
    )

    assert response.status_code == 200, f"HTTP {response.status_code}: {response.text}"

    root = ET.fromstring(response.text)
    users = [{child.tag: child.text for child in u} for u in root.findall(".//user")]

    assert users, "Expected at least one user from listType=full"
