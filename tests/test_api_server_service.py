"""Unit tests for API server background service lifecycle (start, stop, status)."""

import unittest
from unittest.mock import MagicMock, patch
from locallm.core.service_manager import (
    is_api_server_running,
    start_api_server_service,
    stop_api_server_service,
    get_all_services_status,
)


class TestAPIServerService(unittest.TestCase):
    """Test background API Gateway service lifecycle methods."""

    @patch("httpx.Client")
    def test_is_api_server_running_via_http(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response

        self.assertTrue(is_api_server_running("127.0.0.1", 8080, max_cache_age=0.0))

    @patch("httpx.Client")
    @patch("psutil.process_iter")
    def test_is_api_server_running_fallback_process(self, mock_iter, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = Exception("offline")

        proc_serve = MagicMock()
        proc_serve.info = {"name": "python.exe", "cmdline": ["python", "-m", "locallm.cli", "serve"]}
        mock_iter.return_value = [proc_serve]

        self.assertTrue(is_api_server_running("127.0.0.1", 8080, max_cache_age=0.0))

    @patch("httpx.Client")
    @patch("psutil.process_iter")
    def test_is_api_server_running_offline(self, mock_iter, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = Exception("offline")

        proc_other = MagicMock()
        proc_other.info = {"name": "notepad.exe", "cmdline": ["notepad.exe"]}
        mock_iter.return_value = [proc_other]

        self.assertFalse(is_api_server_running("127.0.0.1", 8080, max_cache_age=0.0))

    @patch("locallm.core.service_manager.is_api_server_running", return_value=True)
    def test_start_api_server_already_running(self, mock_running):
        ok, msg = start_api_server_service(host="127.0.0.1", port=8080)
        self.assertTrue(ok)
        self.assertIn("already running", msg)

    @patch("subprocess.Popen")
    @patch("locallm.core.service_manager.is_api_server_running")
    def test_start_api_server_spawns_process(self, mock_is_running, mock_popen):
        mock_is_running.side_effect = [False, True]
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        ok, msg = start_api_server_service(host="127.0.0.1", port=8080)
        self.assertTrue(ok)
        self.assertIn("started in background", msg)
        mock_popen.assert_called_once()

    @patch("psutil.process_iter")
    def test_stop_api_server_service(self, mock_iter):
        proc_serve = MagicMock()
        proc_serve.info = {"pid": 2048, "name": "python.exe", "cmdline": ["python", "-m", "locallm.cli", "serve"]}
        proc_serve.children.return_value = []

        mock_iter.return_value = [proc_serve]

        ok, msg = stop_api_server_service("127.0.0.1", 8080)
        self.assertTrue(ok)
        self.assertIn("Stopped 1", msg)
        proc_serve.terminate.assert_called_once()

    @patch("locallm.core.service_manager.is_ollama_running", return_value=True)
    @patch("locallm.core.service_manager.is_api_server_running", return_value=True)
    def test_get_all_services_status_includes_api_server(self, mock_api, mock_ollama):
        statuses = get_all_services_status()
        self.assertIn("Ollama", statuses)
        self.assertIn("API Gateway Server", statuses)
        self.assertTrue(statuses["Ollama"])
        self.assertTrue(statuses["API Gateway Server"])


if __name__ == "__main__":
    unittest.main()
