# tests/test_cli_arguments.py

import sys
import builtins
from io import StringIO
from unittest.mock import patch, MagicMock

import optimized_routing.main as main


def run_cli(args: list[str]):
    """Helper: call optimized_routing.main.__main__() with patched argv."""
    saved = sys.argv
    sys.argv = ["optimized_routing.main"] + args

    with patch.object(builtins, "print") as mock_print:
        try:
            main.__main__()
        except SystemExit:
            pass

    sys.argv = saved
    return [" ".join(str(a) for a in call.args) for call in mock_print.call_args_list]


def test_cli_origin_override():
    """Ensure --origin overrides the routing origin."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        with patch("optimized_routing.main.generate_google_route") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            run_cli(["--user", "12345", "--origin", "Lewiston, ME"])

            mock_gen.assert_called_with(
                12345,
                origin_address="Lewiston, ME",
                destination_override=None,
            )


def test_cli_destination_override():
    """Ensure --destination is passed into routing layer."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        with patch("optimized_routing.main.generate_google_route") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            run_cli(["--user", "12345", "--destination", "Portland, ME"])

            mock_gen.assert_called_with(
                12345,
                origin_address=None,
                destination_override="Portland, ME",
            )


def test_cli_both_origin_and_destination():
    """Ensure both overrides work when passed together."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        with patch("optimized_routing.main.generate_google_route") as mock_gen:
            mock_gen.return_value = "ROUTE"

            run_cli(
                [
                    "--user",
                    "12345",
                    "--origin",
                    "Lewiston, ME",
                    "--destination",
                    "Bangor, ME",
                ]
            )

            mock_gen.assert_called_with(
                12345,
                origin_address="Lewiston, ME",
                destination_override="Bangor, ME",
            )


def test_cli_preview_stops_single_user():
    """Ensure preview mode calls preview_user_stops exactly once."""
    with patch("optimized_routing.main.preview_user_stops") as mock_prev:
        with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
            inst = MockBF.return_value
            inst.get_active_users.return_value = []
            inst.get_user_origin_address.return_value = "Test Origin"

            run_cli(["--preview-stops", "12345"])

            mock_prev.assert_called_once()


def test_cli_preview_stops_all():
    """Ensure preview mode loops through all active users."""
    with patch("optimized_routing.main.preview_user_stops") as mock_prev:
        with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
            inst = MockBF.return_value
            inst.get_active_users.return_value = [
                {"userId": "1"},
                {"userId": "2"},
                {"userId": "3"},
            ]
            inst.get_user_origin_address.return_value = "Test Origin"

            run_cli(["--preview-stops", "all"])

            assert mock_prev.call_count == 3
