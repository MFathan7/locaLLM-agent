"""Unit tests for configuration manager."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from locallm.config import LocaLLMConfig, load_config, save_config


class TestConfig(unittest.TestCase):
    """Test configuration loading and saving logic."""

    def test_default_config_values(self):
        cfg = LocaLLMConfig()
        self.assertEqual(cfg.ollama_host, "http://127.0.0.1:11434")
        self.assertEqual(cfg.temperature, 0.7)
        self.assertFalse(cfg.agent_auto_approve_commands)

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "config.json"
            with patch("locallm.config.get_config_file_path", return_value=temp_file):
                custom_cfg = LocaLLMConfig(
                    default_model="test-model:latest",
                    temperature=0.4,
                    telegram_token="dummy_token_123",
                )
                save_config(custom_cfg)
                self.assertTrue(temp_file.exists())

                loaded_cfg = load_config()
                self.assertEqual(loaded_cfg.default_model, "test-model:latest")
                self.assertEqual(loaded_cfg.temperature, 0.4)
                self.assertEqual(loaded_cfg.telegram_token, "dummy_token_123")


if __name__ == "__main__":
    unittest.main()
