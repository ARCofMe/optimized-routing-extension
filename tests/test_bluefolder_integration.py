"""Unit tests for the BlueFolder integration helper."""

import pytest
from bluefolder_integration import BlueFolderIntegration


class DummyAppointments:
    """Small stub mimicking the BlueFolder appointments domain."""

    def list(self, params):
        """Return canned XML mimicking a single appointment."""
        self.last_params = params
        from xml.etree.ElementTree import Element, SubElement

        root = Element("response")
        appt = SubElement(root, "appointment")
        SubElement(appt, "id").text = "42"
        SubElement(appt, "subject").text = "Test Job"
        SubElement(appt, "locationAddress").text = "123 Main St"
        SubElement(appt, "locationCity").text = "Portland"
        SubElement(appt, "locationState").text = "ME"
        SubElement(appt, "locationZip").text = "04101"
        SubElement(appt, "userId").text = "7"
        return root


@pytest.fixture
def integration(monkeypatch):
    """Provide a BlueFolderIntegration with stubbed appointment client."""
    dummy = DummyAppointments()
    monkeypatch.setattr(
        "bluefolder_integration.BlueFolderClient",
        lambda: type("C", (), {"appointments": dummy})(),
    )
    return BlueFolderIntegration()


def test_get_appointments_filters_and_parses(integration):
    """Verify assignment XML is parsed into a simplified dict."""
    appts = integration.get_appointments(user_id=7, start_date="2025-11-06")
    assert appts[0]["id"] == 42
    assert appts[0]["city"] == "Portland"
