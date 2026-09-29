"""Unit tests for conversational CLI help and application exit farewell."""

import io
from unittest.mock import MagicMock, patch
import unittest

from locallm.cli import main
from locallm.ui.chat_view import print_conversational_cli_help, render_application_farewell


class TestConversationalCLI(unittest.TestCase):
    """Test conversational help and farewell display behaviors."""

    def test_print_conversational_cli_help_runs_cleanly(self):
        """Verify conversational help renders without error."""
        # Should execute cleanly without raising exceptions
        print_conversational_cli_help()

    def test_render_application_farewell_runs_cleanly(self):
        """Verify application farewell panel renders without error."""
        render_application_farewell(unloaded_count=1)

    @patch("locallm.cli.print_conversational_cli_help")
    def test_cli_help_flag_interception(self, mock_help):
        """Verify 'locallm --help', '-h', and 'help' trigger conversational guide."""
        main(["--help"])
        mock_help.assert_called_once()
        mock_help.reset_mock()

        main(["-h"])
        mock_help.assert_called_once()
        mock_help.reset_mock()

        main(["help"])
        mock_help.assert_called_once()


if __name__ == "__main__":
    unittest.main()
