"""Unit tests for Ollama HTTP client."""

import unittest
from locallm.core.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    """Test live or mock Ollama client endpoints."""

    def setUp(self):
        self.client = OllamaClient(base_url="http://127.0.0.1:11434")
        if not self.client.is_connected():
            self.skipTest("Live Ollama service is not running locally")

    def test_client_connection(self):
        # Ollama server is running locally in this environment
        connected = self.client.is_connected()
        self.assertTrue(connected)

    def test_get_version(self):
        version = self.client.get_version()
        self.assertIsNotNone(version)
        self.assertIsInstance(version, str)

    def test_list_models(self):
        models = self.client.list_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        model_names = [m["name"] for m in models]
        # Verify one of the installed models exists
        self.assertTrue(any("gemma4" in name for name in model_names))


from unittest.mock import MagicMock, patch


class TestModelPullWizard(unittest.TestCase):
    """Test pull model wizard with single-line live progress."""

    @patch("questionary.text")
    def test_pull_model_wizard_single_line_progress(self, mock_text):
        from locallm.modules.models_manager import _pull_model_wizard
        mock_text.return_value.ask.side_effect = ["test-model:latest", ""]

        mock_client = MagicMock(spec=OllamaClient)
        mock_client.pull_model_stream.return_value = [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 500, "total": 1000},
            {"status": "downloading", "completed": 1000, "total": 1000},
            {"status": "verifying sha256 digest"},
            {"status": "success"},
        ]

        with patch("locallm.modules.models_manager.console.print") as mock_print:
            _pull_model_wizard(mock_client)
            mock_client.pull_model_stream.assert_called_once_with("test-model:latest")
            printed_texts = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Successfully pulled model" in t for t in printed_texts))


if __name__ == "__main__":
    unittest.main()
