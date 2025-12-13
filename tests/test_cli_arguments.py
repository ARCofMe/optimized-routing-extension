# tests/test_cli_arguments.py

import sys
import builtins
from io import StringIO
from unittest.mock import patch, MagicMock

import optimized_routing.main as main
from unittest.mock import ANY


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

        main.settings.default_provider = "geoapify"
        with patch("optimized_routing.main.generate_route_for_provider") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            run_cli(["--user", "12345", "--origin", "Lewiston, ME"])

            mock_gen.assert_called_with(
                "geoapify",
                12345,
                origin_address="Lewiston, ME",
                destination_override=None,
                assignments=ANY,
            )


def test_cli_destination_override():
    """Ensure --destination is passed into routing layer."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        main.settings.default_provider = "geoapify"
        with patch("optimized_routing.main.generate_route_for_provider") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            run_cli(["--user", "12345", "--destination", "Portland, ME"])

            mock_gen.assert_called_with(
                "geoapify",
                12345,
                origin_address=None,
                destination_override="Portland, ME",
                assignments=ANY,
            )


def test_cli_both_origin_and_destination():
    """Ensure both overrides work when passed together."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None

        main.settings.default_provider = "geoapify"
        with patch("optimized_routing.main.generate_route_for_provider") as mock_gen:
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
                "geoapify",
                12345,
                origin_address="Lewiston, ME",
                destination_override="Bangor, ME",
                assignments=ANY,
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


def test_cli_relative_monday_sets_dates():
    """Relative --date monday should compute start/end dates."""
    with patch("optimized_routing.main.BlueFolderIntegration") as MockBF:
        inst = MockBF.return_value
        inst.get_active_users.return_value = [{"userId": "12345"}]
        inst.get_user_origin_address.return_value = None
        inst.get_user_assignments_range.return_value = [{"serviceRequestId": "1"}]

        with patch("optimized_routing.main.generate_route_for_provider") as mock_gen:
            mock_gen.return_value = "FAKE_URL"

            run_cli(["--user", "12345", "--date", "monday"])

        expected_start, expected_end = main.resolve_relative_date("monday")

        inst.get_user_assignments_range.assert_called_with(
            12345, start_date=expected_start, end_date=expected_end, date_range_type="scheduled"
        )
