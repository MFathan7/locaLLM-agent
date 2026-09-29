"""Unit tests for automatic VRAM model unloading and complete service process termination."""

from typing import Any, Dict
import unittest
from unittest.mock import MagicMock, patch
from locallm.core.ollama_client import OllamaClient
from locallm.core.service_manager import stop_ollama_service


class TestCleanupAndStop(unittest.TestCase):
    """Test model unload methods and comprehensive process termination."""

    @patch("httpx.Client")
    def test_get_loaded_models(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "gemma4:12b", "size": 7600000000},
                {"name": "qwen2.5:7b", "size": 4500000000},
            ]
        }
        mock_client.get.return_value = mock_response

        client = OllamaClient()
        loaded = client.get_loaded_models()
        self.assertEqual(loaded, ["gemma4:12b", "qwen2.5:7b"])
        mock_client.get.assert_called_with("/api/ps")

    @patch("httpx.Client")
    def test_unload_model(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response

        client = OllamaClient()
        success = client.unload_model("gemma4:12b")
        self.assertTrue(success)
        mock_client.post.assert_called_with(
            "/api/generate", json={"model": "gemma4:12b", "keep_alive": 0}
        )

    @patch.object(OllamaClient, "is_connected", return_value=True)
    @patch.object(OllamaClient, "get_loaded_models", return_value=["gemma4:12b"])
    @patch.object(OllamaClient, "unload_model", return_value=True)
    def test_unload_all_models(self, mock_unload, mock_loaded, mock_conn):
        client = OllamaClient()
        count = client.unload_all_models()
        self.assertEqual(count, 1)
        mock_unload.assert_called_once_with("gemma4:12b")

    @patch.object(OllamaClient, "is_connected", return_value=True)
    @patch.object(OllamaClient, "get_loaded_models", return_value=[])
    @patch.object(OllamaClient, "unload_model", return_value=True)
    def test_unload_all_models_fallback(self, mock_unload, mock_loaded, mock_conn):
        client = OllamaClient()
        count = client.unload_all_models(fallback_model="fallback-model:latest")
        self.assertEqual(count, 1)
        mock_unload.assert_called_once_with("fallback-model:latest")

    @patch("psutil.process_iter")
    @patch("httpx.Client")
    def test_stop_ollama_service_targets_llama_server(self, mock_http_cls, mock_process_iter):
        mock_http = MagicMock()
        mock_http_cls.return_value.__enter__.return_value = mock_http
        mock_http.get.side_effect = Exception("offline")

        # Mock two processes: ollama.exe and llama-server.exe
        proc_ollama = MagicMock()
        proc_ollama.info = {"pid": 1001, "name": "ollama.exe"}
        proc_ollama.children.return_value = []

        proc_llama_server = MagicMock()
        proc_llama_server.info = {"pid": 1002, "name": "llama-server.exe"}
        proc_llama_server.children.return_value = []

        proc_other = MagicMock()
        proc_other.info = {"pid": 1003, "name": "notepad.exe"}
        proc_other.children.return_value = []

        mock_process_iter.return_value = [proc_ollama, proc_llama_server, proc_other]

        ok, msg = stop_ollama_service()
        self.assertTrue(ok)
        self.assertIn("Stopped 2", msg)
        self.assertIn("runner", msg.lower())

        proc_ollama.terminate.assert_called_once()
        proc_llama_server.terminate.assert_called_once()
        proc_other.terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
