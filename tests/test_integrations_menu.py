"""Unit tests for integration menus and configuration options."""

import tempfile
import unittest
from unittest.mock import patch
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


if __name__ == "__main__":
    unittest.main()
