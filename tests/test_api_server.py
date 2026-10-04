"""Unit tests for the OpenAI-compatible HTTP API Gateway server and port management."""

import json
import socket
import threading
import time
import unittest
from typing import Any, Dict, Generator, List, Optional
import httpx

from locallm.config import LocaLLMConfig
from locallm.modules.api_server import (
    OpenAIAPIHandler,
    ThreadingOpenAIServer,
    find_available_port,
    is_port_in_use,
)


class MockInferenceClient:
    """Mock inference client for testing OpenAI API endpoints."""

    def __init__(self, models: Optional[List[Dict[str, Any]]] = None):
        self._models = models or [
            {"name": "test-model-1", "id": "test-model-1"},
            {"name": "test-model-2", "id": "test-model-2"},
        ]

    def list_models(self) -> List[Dict[str, Any]]:
        return self._models

    def chat_turn(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        num_ctx: int = 8192,
        stats_out: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if stats_out is not None:
            stats_out["prompt_eval_count"] = 12
            stats_out["eval_count"] = 8
        return {"role": "assistant", "content": f"Mock response from {model}"}

    def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        num_ctx: int = 8192,
    ) -> Generator[str, None, None]:
        yield "Mock "
        yield "streaming "
        yield f"from {model}"


class TestPortUtilities(unittest.TestCase):
    """Tests for network port checking and fallback allocation."""

    def test_is_port_in_use_on_free_port(self) -> None:
        # Find a port by binding and immediately closing it
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        self.assertFalse(is_port_in_use(free_port, "127.0.0.1"))

    def test_is_port_in_use_on_busy_port(self) -> None:
        # Keep a socket open to simulate busy port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            busy_port = s.getsockname()[1]
            self.assertTrue(is_port_in_use(busy_port, "127.0.0.1"))

    def test_find_available_port_fallback(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            busy_port = s.getsockname()[1]

            chosen, was_fallback = find_available_port(start_port=busy_port, host="127.0.0.1")
            self.assertTrue(was_fallback)
            self.assertNotEqual(chosen, busy_port)
            self.assertFalse(is_port_in_use(chosen, "127.0.0.1"))


class TestOpenAIAPIServer(unittest.TestCase):
    """Integration tests for the HTTP API Gateway server."""

    server: ThreadingOpenAIServer
    server_thread: threading.Thread
    port: int
    base_url: str

    @classmethod
    def setUpClass(cls) -> None:
        # Bind on random free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]

        cls.config = LocaLLMConfig(
            default_model="test-model-1",
            server_host="127.0.0.1",
            server_port=cls.port,
            server_api_key="secret-token-123",
        )
        cls.mock_client = MockInferenceClient()

        cls.server = ThreadingOpenAIServer(
            ("127.0.0.1", cls.port),
            OpenAIAPIHandler,
            config=cls.config,
            client=cls.mock_client,
            api_key=cls.config.server_api_key,
            workspace="default",
            default_model="test-model-1",
        )

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)

    def test_health_endpoint(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{self.base_url}/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("status"), "ok")
            self.assertIn("service", data)
            self.assertEqual(data.get("active_model"), "test-model-1")

    def test_cors_options(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            resp = client.options(f"{self.base_url}/v1/chat/completions")
            self.assertEqual(resp.status_code, 204)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))

    def test_auth_rejection(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            # Missing header
            resp = client.get(f"{self.base_url}/v1/models")
            self.assertEqual(resp.status_code, 401)
            err = resp.json()
            self.assertEqual(err.get("error", {}).get("code"), "invalid_api_key")

            # Incorrect header
            resp2 = client.get(
                f"{self.base_url}/v1/models",
                headers={"Authorization": "Bearer wrong-key"},
            )
            self.assertEqual(resp2.status_code, 401)

    def test_models_endpoint(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{self.base_url}/v1/models",
                headers={"Authorization": "Bearer secret-token-123"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("object"), "list")
            ids = [m["id"] for m in data.get("data", [])]
            self.assertIn("test-model-1", ids)
            self.assertIn("test-model-2", ids)
            self.assertIn("locallm-agent", ids)
            self.assertIn("auto", ids)

    def test_chat_completions_non_streaming(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            payload = {
                "model": "test-model-1",
                "messages": [{"role": "user", "content": "Hello test"}],
                "stream": False,
            }
            resp = client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Authorization": "Bearer secret-token-123"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("object"), "chat.completion")
            self.assertEqual(data.get("model"), "test-model-1")
            self.assertTrue(len(data.get("choices", [])) > 0)
            choice = data["choices"][0]
            self.assertEqual(choice.get("finish_reason"), "stop")
            self.assertIn("Mock response from test-model-1", choice.get("message", {}).get("content", ""))
            self.assertIn("usage", data)
            self.assertEqual(data["usage"].get("total_tokens"), 20)

    def test_chat_completions_streaming_sse(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            payload = {
                "model": "test-model-2",
                "messages": [{"role": "user", "content": "Stream please"}],
                "stream": True,
            }
            resp = client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Authorization": "Bearer secret-token-123"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/event-stream", resp.headers.get("Content-Type", ""))

            lines = resp.text.strip().split("\n")
            data_lines = [l for l in lines if l.startswith("data: ")]
            self.assertTrue(len(data_lines) >= 3)
            self.assertEqual(data_lines[-1], "data: [DONE]")

            # Check middle chunk
            first_data = json.loads(data_lines[0].replace("data: ", ""))
            self.assertEqual(first_data.get("object"), "chat.completion.chunk")
            self.assertEqual(first_data.get("model"), "test-model-2")

    def test_chat_completions_with_workspace_header(self) -> None:
        with httpx.Client(timeout=3.0) as client:
            payload = {
                "model": "test-model-1",
                "messages": [{"role": "user", "content": "Check workspace context"}],
                "stream": False,
            }
            resp = client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": "Bearer secret-token-123",
                    "X-Workspace": "default",
                },
            )
            self.assertEqual(resp.status_code, 200)


class TestBackgroundAPIServerLifecycle(unittest.TestCase):
    """Tests for non-blocking background daemon execution."""

    def test_background_server_start_and_stop(self) -> None:
        from locallm.modules.api_server import (
            get_api_server_info,
            is_api_server_running,
            start_background_api_server,
            stop_background_api_server,
        )

        cfg = LocaLLMConfig(
            server_host="127.0.0.1",
            server_port=8089,
            server_api_key="test-bg-key",
            default_model="gemma4:12b",
        )

        # Start background server
        ok, msg, port = start_background_api_server(cfg, quiet=True)
        self.assertTrue(ok)
        self.assertTrue(is_api_server_running())

        info = get_api_server_info()
        self.assertEqual(info.get("port"), port)
        self.assertEqual(info.get("api_key"), "test-bg-key")

        # Verify background server accepts requests and buffers them quietly
        with httpx.Client(timeout=3.0) as client:
            res = client.get(f"http://127.0.0.1:{port}/health")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json().get("status"), "ok")

        from locallm.modules.api_server import (
            build_request_logs_table,
            clear_api_request_logs,
            get_api_request_logs,
        )

        logs = get_api_request_logs()
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[-1]["method"], "GET")
        self.assertEqual(logs[-1]["path"], "/health")
        self.assertEqual(logs[-1]["status"], 200)

        # Verify table builder formats cleanly
        tbl = build_request_logs_table(limit=10)
        self.assertIsNotNone(tbl)

        # Clear logs
        clear_api_request_logs()
        self.assertEqual(len(get_api_request_logs()), 0)

        # Stop background server
        stop_ok, stop_msg = stop_background_api_server()
        self.assertTrue(stop_ok)
        self.assertFalse(is_api_server_running())


if __name__ == "__main__":
    unittest.main()

