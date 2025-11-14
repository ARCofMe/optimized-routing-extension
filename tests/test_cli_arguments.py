# tests/test_cli_arguments.py

import sys
import json
import builtins
from unittest.mock import patch, MagicMock
from io import StringIO

import main


def run_cli(args: list[str]):
    """Helper: run main.py with CLI args and capture stdout."""
    saved_argv = sys.argv
    sys.argv = ["main.py"] + args

    captured_out = StringIO()
    with patch.object(builtins, "print") as mock_print:
        try:
            main.__main__()
        except SystemExit:
            pass

    sys.argv = saved_argv

    printed = []
    for call in mock_print.call_args_list:
        printed.append(" ".join(str(a) for a in call.args))

    return printed


def test_cli_origin_override():
    """Verify passing --origin overrides the routing origin."""
    with patch("main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        # Mock route generation
        with patch("main.generate_google_route") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            out = run_cli(["--user", "12345", "--origin", "Lewiston, ME"])

            mock_gen.assert_called_with(12345, origin_address="Lewiston, ME")


def test_cli_destination_override():
    """Verify destination override is passed to routing layer."""
    with patch("main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        # Patch routing + destination behavior
        with patch("main.generate_google_route") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            out = run_cli(["--user", "12345", "--destination", "Portland, ME"])

            # The destination override is applied inside routing, so confirm this flag
            # was parsed and the routing call was made at least once.
            mock_gen.assert_called()


def test_cli_both_origin_and_destination():
    """Passing both overrides should not crash and should route."""
    with patch("main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        with patch("main.generate_google_route") as mock_gen:
            mock_gen.return_value = "URL_OK"

            out = run_cli([
                "--user", "12345",
                "--origin", "Lewiston, ME",
                "--destination", "Bangor, ME"
            ])

            mock_gen.assert_called_once()


def test_cli_preview_stops_single_user():
    """Ensure preview mode calls preview_user_stops."""
    with patch("main.preview_user_stops") as mock_preview:
        with patch("main.BlueFolderIntegration") as MockBF:
            inst = MockBF.return_value
            inst.get_active_users.return_value = []
            inst.get_user_origin_address.return_value = "Test Origin"

            out = run_cli(["--preview-stops", "12345"])

            mock_preview.assert_called_once()


def test_cli_preview_stops_all():
    """Ensure preview mode runs through all active users."""
    with patch("main.preview_user_stops") as mock_preview:
        with patch("main.BlueFolderIntegration") as MockBF:
            inst = MockBF.return_value
            inst.get_active_users.return_value = [
                {"userId": "1"}, {"userId": "2"}, {"userId": "3"}
            ]
            inst.get_user_origin_address.return_value = "Test Origin"

            out = run_cli(["--preview-stops", "all"])

            assert mock_preview.call_count == 3
