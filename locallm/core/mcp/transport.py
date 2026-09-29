"""Transport layers for Model Context Protocol (MCP) communication."""

from abc import ABC, abstractmethod
import concurrent.futures
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional


class BaseTransport(ABC):
    """Abstract base class for MCP transport mechanisms."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the MCP server."""
        pass

    @abstractmethod
    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Send a JSON-RPC 2.0 request and wait synchronously for the response."""
        pass

    @abstractmethod
    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a one-way JSON-RPC 2.0 notification without waiting for a response."""
        pass

    @abstractmethod
    def is_alive(self) -> bool:
        """Check whether the transport connection is currently active."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleanly terminate the transport connection and release resources."""
        pass


class StdioTransport(BaseTransport):
    """Subprocess stdio transport communicating via newline-delimited JSON-RPC."""

    def __init__(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.cwd = cwd or Path.cwd()

        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._request_id = 0
        self._id_lock = threading.Lock()
        self._pending_requests: Dict[int, concurrent.futures.Future] = {}
        self._pending_lock = threading.Lock()
        self._stderr_buffer: List[str] = []
        self._closed = False

    def connect(self) -> None:
        """Spawn the MCP server subprocess with redirected stdio pipes."""
        if self.is_alive():
            return

        cmd = self.command
        # Cross-platform executable resolution for Windows (e.g. npx -> npx.cmd)
        if sys.platform == "win32":
            resolved_cmd = shutil.which(cmd)
            if resolved_cmd:
                cmd = resolved_cmd
            elif not cmd.lower().endswith((".exe", ".cmd", ".bat")):
                for ext in [".cmd", ".exe", ".bat"]:
                    cand = shutil.which(f"{cmd}{ext}")
                    if cand:
                        cmd = cand
                        break

        full_cmd = [cmd] + self.args
        merged_env = os.environ.copy()
        merged_env.update(self.env)
        # Ensure node/python output in UTF-8
        merged_env["PYTHONIOENCODING"] = "utf-8"
        merged_env["NODE_NO_WARNINGS"] = "1"

        try:
            self._process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.cwd),
                env=merged_env,
                bufsize=1,
            )
        except Exception as exc:
            raise ConnectionError(f"Failed to spawn MCP server '{self.command}': {exc}")

        self._closed = False
        self._reader_thread = threading.Thread(target=self._read_stdout_loop, daemon=True)
        self._reader_thread.start()

        self._stderr_thread = threading.Thread(target=self._read_stderr_loop, daemon=True)
        self._stderr_thread.start()

    def _read_stdout_loop(self) -> None:
        """Background thread continuously reading JSON-RPC messages from subprocess stdout."""
        assert self._process is not None and self._process.stdout is not None
        while not self._closed and self._process.poll() is None:
            try:
                line = self._process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_id = msg.get("id")
                if msg_id is not None:
                    with self._pending_lock:
                        fut = self._pending_requests.pop(msg_id, None)
                    if fut and not fut.done():
                        fut.set_result(msg)
            except Exception:
                break

    def _read_stderr_loop(self) -> None:
        """Background thread capturing server stderr diagnostics."""
        assert self._process is not None and self._process.stderr is not None
        while not self._closed and self._process.poll() is None:
            try:
                err_line = self._process.stderr.readline()
                if not err_line:
                    break
                err_line = err_line.strip()
                if err_line:
                    self._stderr_buffer.append(err_line)
                    if len(self._stderr_buffer) > 50:
                        self._stderr_buffer.pop(0)
            except Exception:
                break

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for matched response."""
        if not self.is_alive():
            raise ConnectionError("MCP server process is not running.")

        with self._id_lock:
            self._request_id += 1
            req_id = self._request_id

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        fut: concurrent.futures.Future = concurrent.futures.Future()
        with self._pending_lock:
            self._pending_requests[req_id] = fut

        line = json.dumps(payload, ensure_ascii=False) + "\n"
        try:
            assert self._process is not None and self._process.stdin is not None
            self._process.stdin.write(line)
            self._process.stdin.flush()
        except Exception as exc:
            with self._pending_lock:
                self._pending_requests.pop(req_id, None)
            raise ConnectionError(f"Failed to write to MCP server stdin: {exc}")

        try:
            resp = fut.result(timeout=timeout)
            if "error" in resp:
                err = resp["error"]
                msg = err.get("message", "Unknown error")
                code = err.get("code", -1)
                raise RuntimeError(f"MCP server error ({code}): {msg}")
            return resp.get("result", {})
        except concurrent.futures.TimeoutError:
            with self._pending_lock:
                self._pending_requests.pop(req_id, None)
            recent_err = "\n".join(self._stderr_buffer[-5:]) if self._stderr_buffer else "None"
            raise TimeoutError(f"MCP request '{method}' timed out after {timeout}s. Stderr: {recent_err}")

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send JSON-RPC notification (no response expected)."""
        if not self.is_alive():
            return

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        line = json.dumps(payload, ensure_ascii=False) + "\n"
        try:
            assert self._process is not None and self._process.stdin is not None
            self._process.stdin.write(line)
            self._process.stdin.flush()
        except Exception:
            pass

    def is_alive(self) -> bool:
        """Return True if subprocess is actively running."""
        return self._process is not None and self._process.poll() is None

    def close(self) -> None:
        """Cleanly terminate the server subprocess."""
        self._closed = True
        if self._process:
            try:
                if self._process.stdin:
                    try:
                        self._process.stdin.close()
                    except Exception:
                        pass
                if self._process.stdout:
                    try:
                        self._process.stdout.close()
                    except Exception:
                        pass
                if self._process.stderr:
                    try:
                        self._process.stderr.close()
                    except Exception:
                        pass
                self._process.terminate()
                try:
                    self._process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            except Exception:
                pass
            finally:
                self._process = None

        with self._pending_lock:
            for fut in self._pending_requests.values():
                if not fut.done():
                    fut.set_exception(ConnectionError("MCP transport closed."))
            self._pending_requests.clear()


class SSETransport(BaseTransport):
    """HTTP/SSE transport connecting to remote MCP servers."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._client: Optional[Any] = None
        self._request_id = 0
        self._id_lock = threading.Lock()
        self._connected = False

    def connect(self) -> None:
        """Initialize HTTP client for MCP communication."""
        import httpx

        self._client = httpx.Client(timeout=30.0)
        self._connected = True

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Send JSON-RPC request over HTTP POST to the MCP endpoint."""
        if not self._connected or not self._client:
            self.connect()

        with self._id_lock:
            self._request_id += 1
            req_id = self._request_id

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        assert self._client is not None
        try:
            resp = self._client.post(self.url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                err = data["error"]
                msg = err.get("message", "Unknown error")
                raise RuntimeError(f"MCP server error: {msg}")
            return data.get("result", {})
        except Exception as exc:
            raise RuntimeError(f"MCP HTTP request failed: {exc}")

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send notification over HTTP."""
        if not self._connected or not self._client:
            return

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            self._client.post(self.url, json=payload, timeout=5.0)
        except Exception:
            pass

    def is_alive(self) -> bool:
        return self._connected and self._client is not None

    def close(self) -> None:
        self._connected = False
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
