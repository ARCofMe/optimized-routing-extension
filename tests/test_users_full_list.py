"""
Forces a 'full' user list call to BlueFolder, with explicit authentication.
"""

import xml.etree.ElementTree as ET
from bluefolder_api.client import BlueFolderClient
from pprint import pprint

print("\n🔐 Testing BlueFolder user list with listType='full' (authenticated)...\n")

client = BlueFolderClient()

xml_payload = """<request>
    <userList>
        <listType>full</listType>
    </userList>
</request>"""

url = f"{client.base_url}/users/list.aspx"

# ✅ FIX: include Basic Auth manually
response = client.session.post(
    url,
    data=xml_payload.encode("utf-8"),
    headers={"Content-Type": "application/xml"},
    auth=(client.api_key, "x"),
)

print(f"HTTP {response.status_code}")
print("Raw response (first 500 chars):\n", response.text[:500], "...\n")

if response.status_code != 200:
    raise SystemExit("❌ Request failed. Check API key or base URL.")

root = ET.fromstring(response.text)
users = [{child.tag: child.text for child in u} for u in root.findall(".//user")]

print(f"✅ Parsed {len(users)} users from listType='full'\n")

if users:
    print("🧩 Available keys in first user record:")
    print(sorted(users[0].keys()))
    print()
    pprint(users[0])
else:
    print(
        "⚠️ No <user> elements returned — permission may still restrict full list access."
    )
