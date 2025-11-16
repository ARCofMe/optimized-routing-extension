# tests/test_route_optimizer.py

import optimized_routing.routing as routing
from optimized_routing.bluefolder_integration import BlueFolderIntegration


def test_route_for_user():
    """Smoke test that calls don't crash end-to-end."""
    uid = 12345
    origin = "180 E Hebron Rd, Hebron, ME 04238"

    bf = BlueFolderIntegration()

    # Should not crash even with no real BlueFolder data
    assignments = bf.get_user_assignments_today(uid)
    assert isinstance(assignments, list)

    # Should always return a URL or placeholder text
    route = routing.generate_route_for_provider(
        "google",
        uid,
        origin_address=origin,
        destination_override=None,
    )

    assert isinstance(route, str)
    assert len(route) > 0
