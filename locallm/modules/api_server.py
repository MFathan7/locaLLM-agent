"""OpenAI-compatible HTTP API Gateway server for locaLLM.

Exposes standard OpenAI endpoints (/v1/chat/completions, /v1/models, /health)
backed by locaLLM's local inference engines, smart routing, and workspace context.
"""

from collections import deque
from datetime import datetime
import http.server
import json
from pathlib import Path
import socket
import socketserver
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import questionary
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from locallm.config import LocaLLMConfig, save_config
from locallm.core.openai_client import get_inference_client
from locallm.core.router import route_prompt
from locallm.core.workspace import load_workspace_context
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette

_API_REQUEST_LOGS: deque = deque(maxlen=200)
_API_LOGS_LOCK = threading.Lock()


def record_api_request_log(
    method: str,
    path: str,
    status: int,
    detail: str = "",
    client_ip: str = "",
) -> Dict[str, Any]:
    """Record an API request event in the in-memory ring buffer."""
    entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "method": method,
        "path": path,
        "status": status,
        "detail": detail,
        "client_ip": client_ip,
    }
    with _API_LOGS_LOCK:
        _API_REQUEST_LOGS.append(entry)
    return entry


def get_api_request_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent API request log entries."""
    with _API_LOGS_LOCK:
        return list(_API_REQUEST_LOGS)[-limit:]


def clear_api_request_logs() -> None:
    """Clear stored API request log entries."""
    with _API_LOGS_LOCK:
        _API_REQUEST_LOGS.clear()


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a specific network port is currently occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            # On Linux/macOS, attempt to bind to verify true availability
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except (OSError, socket.error):
            return True


def find_available_port(
    start_port: int = 8080,
    host: str = "127.0.0.1",
    max_attempts: int = 100,
) -> Tuple[int, bool]:
    """Find the next available port starting from start_port.

    Returns:
        Tuple of (selected_port, was_fallback_triggered)
    """
    if not is_port_in_use(start_port, host):
        return start_port, False

    for candidate in range(start_port + 1, start_port + max_attempts):
        if not is_port_in_use(candidate, host):
            return candidate, True

    return start_port, False


class ThreadingOpenAIServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Multi-threaded HTTP server for handling concurrent OpenAI API requests."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Any,
        config: LocaLLMConfig,
        client: Any,
        api_key: str = "",
        workspace: str = "default",
        default_model: Optional[str] = None,
        is_background: bool = False,
    ):
        super().__init__(server_address, RequestHandlerClass)
        self.config = config
        self.client = client
        self.api_key = api_key.strip()
        self.workspace = workspace
        self.default_model = default_model or config.default_model
        self.is_background = is_background


class OpenAIAPIHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler implementing OpenAI-compatible REST API endpoints."""

    server: ThreadingOpenAIServer

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP server stderr output in favor of formatted logging."""
        pass

    def _send_cors_headers(self) -> None:
        """Attach standard Cross-Origin Resource Sharing (CORS) headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Authorization, Content-Type, X-Workspace, X-Model, Accept, User-Agent",
        )
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send formatted JSON response with CORS headers."""
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_openai_error(self, status_code: int, message: str, error_type: str = "invalid_request_error", code: Optional[str] = None) -> None:
        """Send standard OpenAI error payload."""
        payload = {
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": code,
            }
        }
        self._send_json_response(status_code, payload)

    def _check_auth(self) -> bool:
        """Validate bearer token authentication if an API key is configured."""
        required_key = getattr(self.server, "api_key", "").strip()
        if not required_key:
            return True

        auth_header = self.headers.get("Authorization", "").strip()
        if not auth_header:
            self._send_openai_error(
                401,
                "Missing Authorization header. Bearer API key required.",
                error_type="authentication_error",
                code="invalid_api_key",
            )
            return False

        parts = auth_header.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else parts[0]
        if token != required_key:
            self._send_openai_error(
                401,
                "Incorrect or invalid API key provided.",
                error_type="authentication_error",
                code="invalid_api_key",
            )
            return False

        return True

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for health diagnostics and model listings."""
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/health", "/v1/health"):
            active_ws = self.server.workspace
            backend_name = self.server.config.active_backend
            model = self.server.default_model
            self._send_json_response(200, {
                "status": "ok",
                "service": "locaLLM OpenAI-Compatible API Gateway",
                "backend": backend_name,
                "active_model": model,
                "workspace": active_ws,
                "timestamp": datetime.now().isoformat(),
            })
            self._log_request_event("GET", path, 200)
            return

        if not self._check_auth():
            self._log_request_event("GET", path, 401)
            return

        if path in ("/v1/models", "/models"):
            try:
                raw_models: List[Dict[str, Any]] = []
                if hasattr(self.server.client, "list_models"):
                    raw_models = self.server.client.list_models() or []

                model_entries: List[Dict[str, Any]] = [
                    {
                        "id": "locallm-agent",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "locallm",
                        "permission": [],
                        "root": "locallm-agent",
                        "parent": None,
                    },
                    {
                        "id": "auto",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "locallm",
                        "permission": [],
                        "root": "auto",
                        "parent": None,
                    },
                ]

                for m in raw_models:
                    m_id = m.get("name") or m.get("id")
                    if m_id:
                        model_entries.append({
                            "id": m_id,
                            "object": "model",
                            "created": m.get("created", int(time.time())),
                            "owned_by": m.get("owned_by", "locallm"),
                            "permission": [],
                            "root": m_id,
                            "parent": None,
                        })

                self._send_json_response(200, {
                    "object": "list",
                    "data": model_entries,
                })
                self._log_request_event("GET", path, 200, detail=f"{len(model_entries)} models")
            except Exception as exc:
                self._send_openai_error(500, f"Failed to retrieve models: {exc}", error_type="api_error")
                self._log_request_event("GET", path, 500, detail=str(exc))
            return

        self._send_openai_error(404, f"The requested endpoint '{path}' was not found.")
        self._log_request_event("GET", path, 404)

    def do_POST(self) -> None:
        """Handle POST requests for chat completions."""
        start_time = time.time()
        path = self.path.split("?")[0].rstrip("/")

        if not self._check_auth():
            self._log_request_event("POST", path, 401)
            return

        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._send_openai_error(404, f"The requested endpoint '{path}' was not found.")
            self._log_request_event("POST", path, 404)
            return

        # Parse request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._send_openai_error(400, "Empty request body.")
                self._log_request_event("POST", path, 400)
                return

            body_bytes = self.rfile.read(content_length)
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception as exc:
            self._send_openai_error(400, f"Invalid JSON payload: {exc}")
            self._log_request_event("POST", path, 400)
            return

        # Extract parameters
        model_req = str(payload.get("model", "")).strip() or self.server.default_model
        messages: List[Dict[str, Any]] = payload.get("messages", [])
        stream_requested = bool(payload.get("stream", False))
        temperature = float(payload.get("temperature", self.server.config.temperature))
        max_tokens = payload.get("max_tokens") or payload.get("max_completion_tokens")
        context_window = getattr(self.server.config, "context_window", 8192)

        if not messages:
            self._send_openai_error(400, "Field 'messages' is required and cannot be empty.")
            self._log_request_event("POST", path, 400)
            return

        # Resolve active workspace context
        req_ws = self.headers.get("X-Workspace", "").strip() or self.server.workspace
        ws_context = load_workspace_context(req_ws)

        # Inject workspace context into system messages
        processed_messages = self._prepare_messages_with_context(messages, ws_context)

        # Intelligent Router resolution
        target_model = model_req
        if model_req.lower() in ("auto", "locallm-agent", ""):
            last_prompt = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_prompt = str(m.get("content", ""))
                    break
            if last_prompt:
                route_res = route_prompt(last_prompt, self.server.config, self.server.client)
                target_model = route_res.selected_model
            else:
                target_model = self.server.default_model

        if stream_requested:
            self._handle_streaming_completion(
                target_model=target_model,
                messages=processed_messages,
                temperature=temperature,
                context_window=context_window,
                start_time=start_time,
                path=path,
            )
        else:
            self._handle_non_streaming_completion(
                target_model=target_model,
                messages=processed_messages,
                temperature=temperature,
                context_window=context_window,
                start_time=start_time,
                path=path,
            )

    def _prepare_messages_with_context(
        self,
        messages: List[Dict[str, Any]],
        ws_context: str,
    ) -> List[Dict[str, Any]]:
        """Inject workspace context and environment directives into conversation messages."""
        if not ws_context:
            return list(messages)

        result: List[Dict[str, Any]] = []
        has_system = False

        for msg in messages:
            if msg.get("role") == "system" and not has_system:
                existing = str(msg.get("content", ""))
                combined = f"{existing}\n\n{ws_context}"
                result.append({"role": "system", "content": combined})
                has_system = True
            else:
                result.append(dict(msg))

        if not has_system:
            result.insert(0, {
                "role": "system",
                "content": f"{self.server.config.system_prompt}\n\n{ws_context}",
            })

        return result

    def _handle_non_streaming_completion(
        self,
        target_model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        context_window: int,
        start_time: float,
        path: str,
    ) -> None:
        """Execute non-streaming chat turn and deliver standard OpenAI completion response."""
        stats: Dict[str, Any] = {}
        try:
            turn_msg: Optional[Dict[str, Any]] = None
            if hasattr(self.server.client, "chat_turn"):
                turn_msg = self.server.client.chat_turn(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    num_ctx=context_window,
                    stats_out=stats,
                )

            content = ""
            if turn_msg and isinstance(turn_msg, dict):
                content = turn_msg.get("content", "")

            prompt_tokens = stats.get("prompt_eval_count") or len(str(messages)) // 4
            completion_tokens = stats.get("eval_count") or len(content) // 4
            total_tokens = prompt_tokens + completion_tokens

            cmpl_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
            created_ts = int(time.time())

            response_data = {
                "id": cmpl_id,
                "object": "chat.completion",
                "created": created_ts,
                "model": target_model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
            }

            self._send_json_response(200, response_data)
            duration = round(time.time() - start_time, 2)
            self._log_request_event(
                "POST",
                path,
                200,
                detail=f"model={target_model} tokens={total_tokens} ({duration}s)",
            )
        except Exception as exc:
            self._send_openai_error(500, f"Inference execution failed: {exc}", error_type="api_error")
            self._log_request_event("POST", path, 500, detail=str(exc))

    def _handle_streaming_completion(
        self,
        target_model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        context_window: int,
        start_time: float,
        path: str,
    ) -> None:
        """Stream completion tokens via Server-Sent Events (SSE)."""
        cmpl_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
        created_ts = int(time.time())

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self._send_cors_headers()
        self.end_headers()

        def _send_chunk(payload_bytes: bytes) -> None:
            if not payload_bytes:
                return
            chunk_header = f"{len(payload_bytes):X}\r\n".encode("ascii")
            self.wfile.write(chunk_header + payload_bytes + b"\r\n")
            self.wfile.flush()

        token_count = 0
        try:
            # Emit initial empty role chunk
            initial_chunk = {
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": target_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": ""},
                        "finish_reason": None,
                    }
                ],
            }
            _send_chunk(f"data: {json.dumps(initial_chunk)}\n\n".encode("utf-8"))

            # Stream generated tokens
            if hasattr(self.server.client, "chat_stream"):
                for token in self.server.client.chat_stream(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    num_ctx=context_window,
                ):
                    if not token:
                        continue
                    token_count += 1
                    chunk = {
                        "id": cmpl_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": target_model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    _send_chunk(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))

            # Emit final finish chunk
            finish_chunk = {
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": target_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            _send_chunk(f"data: {json.dumps(finish_chunk)}\n\n".encode("utf-8"))
            _send_chunk(b"data: [DONE]\n\n")

            # Terminate HTTP chunked stream
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

            duration = round(time.time() - start_time, 2)
            self._log_request_event(
                "POST",
                path,
                200,
                detail=f"model={target_model} stream=true tokens={token_count} ({duration}s)",
            )
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected before stream finished
            self._log_request_event("POST", path, 499, detail="client disconnected prematurely")
        except Exception as exc:
            duration = round(time.time() - start_time, 2)
            self._log_request_event("POST", path, 500, detail=f"stream error: {exc} ({duration}s)")

    def _log_request_event(self, method: str, path: str, status: int, detail: str = "") -> None:
        """Format and record structured HTTP log event."""
        client_ip = ""
        try:
            if self.client_address:
                client_ip = str(self.client_address[0])
        except Exception:
            pass

        record_api_request_log(method, path, status, detail=detail, client_ip=client_ip)

        # Suppress direct stdout console print if running as background server daemon.
        # This prevents incoming requests from corrupting or closing interactive TUI menus.
        if not getattr(self.server, "is_background", False):
            now = datetime.now().strftime("%H:%M:%S")
            status_color = "green" if 200 <= status < 300 else ("yellow" if 300 <= status < 500 else "red")
            detail_str = f" • [dim]{detail}[/]" if detail else ""
            console.print(
                f"[dim]{now}[/] [bold cyan]{method:<4}[/] [#bbbbbb]{path:<22}[/] "
                f"[{status_color}]{status}[/]{detail_str}"
            )


def run_api_server(
    config: LocaLLMConfig,
    host: Optional[str] = None,
    port: Optional[int] = None,
    api_key: Optional[str] = None,
    workspace: Optional[str] = None,
    model: Optional[str] = None,
    auto_fallback_port: bool = True,
) -> None:
    """Launch OpenAI-compatible HTTP API Gateway server."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    target_host = host or getattr(config, "server_host", "127.0.0.1")
    requested_port = port or getattr(config, "server_port", 8080)
    effective_api_key = api_key if api_key is not None else getattr(config, "server_api_key", "")
    target_workspace = workspace or getattr(config, "active_workspace", "default")
    target_model = model or config.default_model

    client = get_inference_client(config)

    # Port conflict detection and smart fallback handling
    chosen_port = requested_port
    was_fallback = False

    if is_port_in_use(requested_port, target_host):
        if auto_fallback_port:
            chosen_port, was_fallback = find_available_port(requested_port, target_host)
            console.print(
                f"[bold yellow]▲ Port Conflict Detected:[/] Port [bold red]{requested_port}[/] is currently occupied."
            )
            console.print(
                f"[bold {palette.success}]✔ Smart Auto-Fallback:[/] Bound successfully to next available port: [bold {palette.primary}]{chosen_port}[/]\n"
            )
        else:
            console.print(
                f"[bold red]✖ Error:[/] Port {requested_port} is already in use by another application."
            )
            console.print("[#aaaaaa]Please specify a different port using '--port <number>' or allow auto-fallback.[/]")
            return

    server_address = (target_host, chosen_port)
    try:
        httpd = ThreadingOpenAIServer(
            server_address,
            OpenAIAPIHandler,
            config=config,
            client=client,
            api_key=effective_api_key,
            workspace=target_workspace,
            default_model=target_model,
            is_background=False,
        )
    except Exception as exc:
        console.print(f"[bold red]Failed to initialize HTTP API server:[/] {exc}")
        return

    # Render comprehensive server startup card
    base_url = f"http://{target_host}:{chosen_port}/v1"
    auth_status = f"[bold {palette.success}]Bearer Key Required[/]" if effective_api_key else "[#aaaaaa]Open (No Key)[/]"

    overview_table = Table(
        box=palette.box_style,
        border_style=palette.border_style,
        expand=True,
    )
    overview_table.add_column("Property", style=f"bold {palette.primary}", width=22)
    overview_table.add_column("Value")

    overview_table.add_row("OpenAI Base URL", f"[bold {palette.accent}]{base_url}[/]")
    overview_table.add_row("Chat Completions Endpoint", f"[bold white]{base_url}/chat/completions[/]")
    overview_table.add_row("Models List Endpoint", f"[bold white]{base_url}/models[/]")
    overview_table.add_row("Health Diagnostics", f"[bold white]http://{target_host}:{chosen_port}/health[/]")
    overview_table.add_row("Active Inference Engine", f"[bold {palette.success}]{config.active_backend}[/]")
    overview_table.add_row("Default Model", f"[bold cyan]{target_model}[/]")
    overview_table.add_row("Injected Workspace", f"[bold white]{target_workspace}[/]")
    overview_table.add_row("Authentication", auth_status)

    console.print(Panel(
        overview_table,
        title=f"[bold {palette.primary}]⟦{palette.icon} locaLLM OpenAI-Compatible API Gateway⟧[/]",
        border_style=palette.border_style,
        box=palette.box_style,
    ))

    console.print("[dim]Quickstart Integrations:[/]")
    console.print(f"  [dim]• Open WebUI / Continue / Dify Base URL:[/] [bold]{base_url}[/]")
    if effective_api_key:
        console.print(f"  [dim]• API Key:[/] [bold]{effective_api_key}[/]")
    console.print(
        f"  [dim]• cURL Example:[/] curl -X POST {base_url}/chat/completions "
        f"-H \"Content-Type: application/json\" -d '{{\"model\": \"{target_model}\", \"messages\": [{{\"role\": \"user\", \"content\": \"Hello\"}}]}}'\n"
    )

    console.print(f"[bold {palette.success}]✔ Server is active and listening on http://{target_host}:{chosen_port}[/]")
    console.print("[#aaaaaa]Press Ctrl+C to stop the API server and release port.[/]\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[#aaaaaa]Shutting down API server...[/]")
    finally:
        httpd.server_close()
        console.print(f"[bold {palette.success}]✔ API server stopped. Port {chosen_port} released.[/]")


_global_server: Optional[ThreadingOpenAIServer] = None
_global_server_thread: Optional[threading.Thread] = None
_global_server_info: Dict[str, Any] = {}
_global_server_lock = threading.Lock()


def is_api_server_running() -> bool:
    """Return True if background API Gateway server is actively listening."""
    return _global_server is not None


def get_api_server_info() -> Dict[str, Any]:
    """Return runtime metadata about the active API Gateway server."""
    with _global_server_lock:
        return dict(_global_server_info)


def start_background_api_server(
    config: LocaLLMConfig,
    quiet: bool = False,
) -> Tuple[bool, str, int]:
    """Start the OpenAI-compatible HTTP server in a non-blocking background daemon thread."""
    global _global_server, _global_server_thread, _global_server_info

    with _global_server_lock:
        if _global_server is not None:
            port = _global_server_info.get("port", config.server_port)
            return True, f"API server is already running on port {port}.", port

        target_host = getattr(config, "server_host", "127.0.0.1")
        requested_port = getattr(config, "server_port", 8080)
        api_key = getattr(config, "server_api_key", "")
        workspace = getattr(config, "active_workspace", "default")
        model = config.default_model

        chosen_port, was_fallback = find_available_port(requested_port, target_host)
        server_address = (target_host, chosen_port)
        client = get_inference_client(config)

        try:
            httpd = ThreadingOpenAIServer(
                server_address,
                OpenAIAPIHandler,
                config=config,
                client=client,
                api_key=api_key,
                workspace=workspace,
                default_model=model,
                is_background=True,
            )
        except Exception as exc:
            return False, f"Failed to initialize server: {exc}", requested_port

        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        _global_server = httpd
        _global_server_thread = server_thread
        _global_server_info = {
            "host": target_host,
            "port": chosen_port,
            "requested_port": requested_port,
            "was_fallback": was_fallback,
            "api_key": api_key,
            "workspace": workspace,
            "model": model,
            "base_url": f"http://{target_host}:{chosen_port}/v1",
        }

        msg = f"API server active at http://{target_host}:{chosen_port}/v1"
        if was_fallback:
            msg += f" (auto-fallback from {requested_port})"
        return True, msg, chosen_port


def stop_background_api_server() -> Tuple[bool, str]:
    """Gracefully terminate the background API Gateway server."""
    global _global_server, _global_server_thread, _global_server_info

    with _global_server_lock:
        if _global_server is None:
            return False, "API server is not currently running."

        try:
            _global_server.shutdown()
            _global_server.server_close()
        except Exception:
            pass

        port = _global_server_info.get("port", "")
        _global_server = None
        _global_server_thread = None
        _global_server_info = {}
        return True, f"API server stopped. Port {port} released."


def run_api_server_menu(config: LocaLLMConfig) -> None:
    """Platform TUI menu for configuring and controlling the background API Server Gateway."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    while True:
        console.clear()
        host = getattr(config, "server_host", "127.0.0.1")
        port = getattr(config, "server_port", 8080)
        api_key = getattr(config, "server_api_key", "")
        status_key = f"[bold {palette.success}]Set[/]" if api_key else "[#aaaaaa]None (Open)[/]"

        running = is_api_server_running()
        info = get_api_server_info()
        active_port = info.get("port", port) if running else port

        if running:
            running_text = f"[bold {palette.success}]● RUNNING[/] [dim](http://{host}:{active_port}/v1)[/]"
            toggle_choice = "Stop API Server"
        else:
            running_text = "[#aaaaaa]○ STOPPED (Disabled)[/]"
            toggle_choice = "Start API Server"

        summary = (
            f"Server Status : {running_text}\n"
            f"Host Address  : [bold white]{host}[/]\n"
            f"Configured Port: [bold white]{port}[/] (with smart conflict fallback)\n"
            f"API Key Auth  : {status_key}\n"
            f"Active Backend: [bold {palette.success}]{config.active_backend}[/]\n"
            f"Default Model : [bold cyan]{config.default_model}[/]"
        )
        console.print(Panel(
            summary,
            title=f"[bold {palette.primary}]⟦{palette.icon} OPENAI-COMPATIBLE API GATEWAY⟧[/]",
            border_style=palette.border_style,
            box=palette.box_style,
        ))

        choice = questionary.select(
            "API Server Options:",
            choices=[
                toggle_choice,
                f"Configure Host & Port (Current: {host}:{port})",
                f"Configure API Key (Current: {'Configured' if api_key else 'None'})",
                "View Connection Info & Client Examples",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Start API Server":
            ok, msg, bound_port = start_background_api_server(config)
            if ok:
                config.server_enabled = True
                save_config(config)
                console.print(f"[bold {palette.success}]✔ {msg}[/]\n")
                console.print("[dim]The server is now running in the background. You can continue using locaLLM normally![/]\n")
            else:
                console.print(f"[bold red]✖ {msg}[/]\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()

        elif choice == "Stop API Server":
            ok, msg = stop_background_api_server()
            config.server_enabled = False
            save_config(config)
            if ok:
                console.print(f"[bold {palette.success}]✔ {msg}[/]\n")
            else:
                console.print(f"[#aaaaaa]{msg}[/]\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()

        elif choice.startswith("Configure Host & Port"):
            new_host = questionary.text(
                "Enter Host interface (127.0.0.1 for local, 0.0.0.0 for LAN):",
                default=host,
                style=QUESTIONARY_STYLE,
            ).ask()
            if new_host and new_host.strip():
                config.server_host = new_host.strip()

            new_port_str = questionary.text(
                "Enter Port number (1024-65535):",
                default=str(port),
                style=QUESTIONARY_STYLE,
            ).ask()
            if new_port_str and new_port_str.strip().isdigit():
                p_val = int(new_port_str.strip())
                if 1024 <= p_val <= 65535:
                    config.server_port = p_val

            save_config(config)
            if is_api_server_running():
                console.print("[yellow]▲ Note: Restart server to apply new host/port bindings.[/]")
            console.print(f"[bold {palette.success}]✔ Server host and port configuration saved.[/]\n")
            time.sleep(1.0)

        elif choice.startswith("Configure API Key"):
            new_key = questionary.password(
                "Enter Bearer API Key (leave empty to disable authentication):",
                style=QUESTIONARY_STYLE,
            ).ask()
            if new_key is not None:
                config.server_api_key = new_key.strip()
                save_config(config)
                if is_api_server_running():
                    console.print("[yellow]▲ Note: Restart server to apply new API key.[/]")
                console.print(f"[bold {palette.success}]✔ Server API key updated.[/]\n")
                time.sleep(1.0)

        elif choice == "View Connection Info & Client Examples":
            _display_server_client_info(config, host, active_port, api_key)


def build_request_logs_table(limit: int = 15, palette: Optional[Any] = None) -> Table:
    """Construct Rich Table displaying recent HTTP requests."""
    if palette is None:
        palette = get_theme_palette()

    table = Table(
        box=palette.box_style,
        border_style=palette.border_style,
        expand=True,
        header_style=f"bold {palette.primary}",
        show_header=True,
    )
    table.add_column("Time", style="dim", width=10)
    table.add_column("Method", style=f"bold {palette.primary}", width=8)
    table.add_column("Endpoint / Path", width=26)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Detail / Latency")

    logs = get_api_request_logs(limit=limit)
    if not logs:
        table.add_row(
            "-",
            "-",
            "[dim]No incoming requests recorded yet[/]",
            "[dim]-[/]",
            "[dim]Waiting for client requests...[/]",
        )
    else:
        for entry in reversed(logs):
            status = entry.get("status", 200)
            status_color = (
                palette.success
                if 200 <= status < 300
                else (palette.warning if 300 <= status < 500 else palette.danger)
            )
            table.add_row(
                entry.get("timestamp", "--:--:--"),
                entry.get("method", "GET"),
                entry.get("path", "/"),
                f"[{status_color}]{status}[/]",
                f"[dim]{entry.get('detail', '')}[/]" if entry.get("detail") else "",
            )
    return table


def _run_live_request_log_stream(
    config: LocaLLMConfig,
    host: str,
    port: int,
) -> None:
    """Run an auto-refreshing live request log HUD until user presses 'q' or Enter."""
    from locallm.modules.monitor import _check_exit_key

    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    base_url = f"http://{host}:{port}/v1"

    def _render() -> Panel:
        table = build_request_logs_table(limit=18, palette=palette)
        logs = get_api_request_logs()
        sub_info = f"[dim]Listening on {base_url} • {len(logs)} request(s) recorded • Press[/] [bold white]q[/] [dim]or[/] [bold white]Enter[/] [dim]to return[/]"
        return Panel(
            table,
            title=f"[bold {palette.primary}]⟦{palette.icon} LIVE API GATEWAY REQUEST MONITOR⟧[/]",
            subtitle=sub_info,
            box=palette.box_style,
            border_style=palette.border_style,
            padding=(0, 1),
        )

    console.clear()
    try:
        with Live(_render(), console=console, refresh_per_second=4, screen=False) as live:
            while True:
                time.sleep(0.2)
                if _check_exit_key():
                    break
                live.update(_render())
    except KeyboardInterrupt:
        pass
    finally:
        console.clear()


def _display_server_client_info(
    config: LocaLLMConfig,
    host: str,
    port: int,
    api_key: str,
) -> None:
    """Display copy-pasteable client snippets, endpoints card, and interactive request activity."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    base_url = f"http://{host}:{port}/v1"
    auth_str = f"[bold {palette.success}]Bearer Key Required[/]" if api_key else "[#aaaaaa]Open (No Key)[/]"

    while True:
        console.clear()
        table = Table(
            box=palette.box_style,
            border_style=palette.border_style,
            expand=True,
        )
        table.add_column("Endpoint / Tool", style=f"bold {palette.primary}", width=25)
        table.add_column("Value / URL")

        table.add_row("OpenAI Base URL", f"[bold {palette.accent}]{base_url}[/]")
        table.add_row("Chat Completions Endpoint", f"[bold white]{base_url}/chat/completions[/]")
        table.add_row("Models List Endpoint", f"[bold white]{base_url}/models[/]")
        table.add_row("Health Probe Endpoint", f"[bold white]http://{host}:{port}/health[/]")
        table.add_row("Authentication", auth_str)
        if api_key:
            table.add_row("Configured API Key", f"[bold]{api_key}[/]")

        console.print(Panel(
            table,
            title=f"[bold {palette.primary}]⟦{palette.icon} API GATEWAY CONNECTION INFO⟧[/]",
            border_style=palette.border_style,
            box=palette.box_style,
        ))

        # Recent request activity table
        log_count = len(get_api_request_logs())
        logs_table = build_request_logs_table(limit=10, palette=palette)
        console.print(Panel(
            logs_table,
            title=f"[bold {palette.primary}]⟦{palette.icon} RECENT REQUEST ACTIVITY ({log_count} recorded)⟧[/]",
            border_style=palette.border_style,
            box=palette.box_style,
        ))

        console.print("[dim]Client Configuration Examples:[/]")
        console.print(f"  [dim]• Open WebUI / Continue / Dify Base URL:[/] [bold]{base_url}[/]")
        console.print(
            f"  [dim]• Python OpenAI SDK Example:[/]\n"
            f"    [white]client = OpenAI(base_url=\"{base_url}\", api_key=\"{api_key or 'not-needed'}\")[/]\n"
            f"    [white]resp = client.chat.completions.create(model=\"{config.default_model}\", messages=[{{\"role\": \"user\", \"content\": \"Hi\"}}])[/]\n"
        )

        choice = questionary.select(
            "Connection & Log Actions:",
            choices=[
                "Refresh Logs",
                "Live Stream Logs (HUD)",
                "Clear Request Logs",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break
        elif choice == "Refresh Logs":
            continue
        elif choice == "Live Stream Logs (HUD)":
            _run_live_request_log_stream(config, host, port)
        elif choice == "Clear Request Logs":
            clear_api_request_logs()
            console.print(f"[bold {palette.success}]✔ Request logs cleared.[/]")
            time.sleep(0.5)
