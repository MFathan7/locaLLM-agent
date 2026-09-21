"""Unit tests for integration menus and configuration options."""

import tempfile
import unittest
from unittest.mock import MagicMock, patch
from locallm.config import LocaLLMConfig, load_config, save_config
from locallm.modules.agent import toggle_agent_auto_approve


class TestIntegrationsMenu(unittest.TestCase):
    """Test integration menu functions and persistence."""

    def test_toggle_agent_auto_approve(self):
        cfg = LocaLLMConfig(agent_auto_approve_commands=False)
        with patch("locallm.modules.agent.save_config") as mock_save:
            toggle_agent_auto_approve(cfg)
            self.assertTrue(cfg.agent_auto_approve_commands)
            mock_save.assert_called_once_with(cfg)

            toggle_agent_auto_approve(cfg)
            self.assertFalse(cfg.agent_auto_approve_commands)

    def test_context_window_config(self):
        cfg = LocaLLMConfig(context_window=16384)
        self.assertEqual(cfg.context_window, 16384)

    @patch("questionary.select")
    @patch("locallm.ui.menu.render_banner")
    @patch("locallm.ui.menu.get_inference_client")
    def test_start_main_menu_setup_required_when_offline(self, mock_client_factory, mock_banner, mock_select):
        from locallm.ui.menu import start_main_menu
        mock_client = MagicMock()
        mock_client.is_connected.return_value = False
        mock_client.unload_all_models.return_value = 0
        mock_client_factory.return_value = mock_client

        mock_select.return_value.ask.return_value = "Exit"

        cfg = LocaLLMConfig()
        with patch("sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit(0)
            with self.assertRaises(SystemExit):
                start_main_menu(cfg, mock_client)
            mock_exit.assert_called_once_with(0)

        mock_select.assert_called_once()
        args, kwargs = mock_select.call_args
        prompt = args[0]
        choices = kwargs.get("choices", [])
        self.assertIn("Setup Required", prompt)
        self.assertEqual(choices, ["Services", "Settings", "Exit"])

    @patch("questionary.select")
    @patch("locallm.ui.menu.render_banner")
    @patch("locallm.ui.menu.get_inference_client")
    def test_start_main_menu_full_when_online(self, mock_client_factory, mock_banner, mock_select):
        from locallm.ui.menu import start_main_menu
        mock_client = MagicMock()
        mock_client.is_connected.return_value = True
        mock_client.unload_all_models.return_value = 0
        mock_client_factory.return_value = mock_client

        mock_select.return_value.ask.return_value = "Exit"

        cfg = LocaLLMConfig()
        with patch("sys.exit") as mock_exit:
            mock_exit.side_effect = SystemExit(0)
            with self.assertRaises(SystemExit):
                start_main_menu(cfg, mock_client)
            mock_exit.assert_called_once_with(0)

        mock_select.assert_called_once()
        args, kwargs = mock_select.call_args
        prompt = args[0]
        choices = kwargs.get("choices", [])
        self.assertEqual(prompt, "Main Menu:")
        self.assertIn("Assistant", choices)
        self.assertIn("Workspaces", choices)
        self.assertIn("Integrations", choices)
        self.assertIn("Model Manager", choices)
        self.assertIn("Services", choices)


if __name__ == "__main__":
    unittest.main()
