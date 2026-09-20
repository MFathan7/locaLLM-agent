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


if __name__ == "__main__":
    unittest.main()
