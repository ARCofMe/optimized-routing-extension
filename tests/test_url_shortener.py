# tests/test_urt_shortener.py
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from optimized_routing.routing import shorten_route_url

# Make sure your .env has:
# CF_SHORTENER_URL=https://route-shortener.<you>.workers.dev

TEST_URL = "https://www.google.com/maps/dir/61+Portland+Rd%2C+Suite+A%2C+Gray%2C+ME%2C+04039/18+Mill+Stream+Dr.%2C+Atkinson%2C+NH+03811/139+Mill+Rd%2C+Hampton%2C+NH+03842/24+SAMOSET+DR%2C+Salem%2C+NH+03079/24+SAMOSET+DR%2C+Salem%2C+NH+03079/47+Glastombury+Dr%2C+Sandown%2C+NH+03873/15+CULVER+ST+%2324%2C+Plaistow%2C+NH+03865/87L+DERRYFIELD+RD%2C+Derry%2C+NH+03038/61+Portland+Rd%2C+Suite+A%2C+Gray%2C+ME%2C+04039"

print("🔧 Testing Cloudflare Shortener...")
print("Worker =", os.getenv("CF_SHORTENER_URL"))
print("Original length =", len(TEST_URL))

short = shorten_route_url(TEST_URL)

print("Short URL:", short)
print("Short length:", len(short))
