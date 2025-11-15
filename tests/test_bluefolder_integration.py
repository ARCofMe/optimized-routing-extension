# tests/test_bluefolder_integration.py

import pytest
from optimized_routing.bluefolder_integration import BlueFolderIntegration


class DummyAppointments:
    """Stub object to mimic BlueFolderClient.appointments.list()."""

    def list(self, params):
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
    dummy = DummyAppointments()

    monkeypatch.setattr(
        "optimized_routing.bluefolder_integration.BlueFolderClient",
        lambda: type("C", (), {"appointments": dummy})(),
    )

    return BlueFolderIntegration()


def test_get_appointments_filters_and_parses(integration):
    appts = integration.get_appointments(7, "2025-11-06")
    assert appts[0]["id"] == 42
    assert appts[0]["city"] == "Portland"
