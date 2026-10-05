"""OpenAI-compatible HTTP API Gateway server for locaLLM.

Exposes standard OpenAI endpoints (/v1/chat/completions, /v1/models, /health)
backed by locaLLM's local inference engines, smart routing, and workspace context.
"""

from collections import deque
from datetime import datetime
import http.server
import json
from pathlib import Path
import re
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
        self._config_mtime: float = 0.0
        self._client_cache: Dict[str, Any] = {}
        self._client_lock = threading.Lock()
        self._init_config_mtime()

    def _init_config_mtime(self) -> None:
        try:
            from locallm.config import get_config_file_path
            cfg_p = get_config_file_path()
            if cfg_p.exists():
                self._config_mtime = cfg_p.stat().st_mtime
        except Exception:
            pass

    def reload_config_if_needed(self) -> LocaLLMConfig:
        """Check if config.json on disk was modified, and hot-reload state if so."""
        try:
            from locallm.config import get_config_file_path, load_config
            cfg_p = get_config_file_path()
            if cfg_p.exists():
                mtime = cfg_p.stat().st_mtime
                if mtime > self._config_mtime:
                    fresh_cfg = load_config()
                    self.config = fresh_cfg
                    self.default_model = fresh_cfg.default_model
                    self.workspace = fresh_cfg.active_workspace
                    self._config_mtime = mtime
                    from locallm.core.openai_client import get_inference_client
                    with self._client_lock:
                        self.client = get_inference_client(fresh_cfg)
                        self._client_cache.clear()
        except Exception:
            pass
        return self.config

    def get_client_for_request(
        self,
        model: Optional[str] = None,
        backend: Optional[str] = None,
    ) -> Any:
        """Dynamically resolve and cache the inference client for a request."""
        self.reload_config_if_needed()
        config = self.config

        target_backend = (backend or "").strip().lower()

        if not target_backend and model:
            target_model = model.strip()
            from locallm.config import get_custom_platform
            for p in getattr(config, "custom_platforms", []):
                if target_model == p.default_model or target_model == p.name:
                    target_backend = p.name.lower()
                    break

            if not target_backend:
                active = config.active_backend.strip().lower()
                if active == "ollama":
                    target_backend = "ollama"
                else:
                    custom_p = get_custom_platform(config, active)
                    if custom_p and custom_p.default_model == target_model:
                        target_backend = active
                    else:
                        if ":" in target_model or "/" in target_model:
                            target_backend = "ollama"
                        else:
                            target_backend = active

        if not target_backend:
            target_backend = config.active_backend.strip().lower()

        # If target matches currently active backend and self.client is available, use it directly
        if target_backend == config.active_backend.strip().lower() and self.client:
            return self.client

        with self._client_lock:
            if target_backend == "ollama":
                cache_key = f"ollama:{config.ollama_host}"
                if cache_key not in self._client_cache:
                    from locallm.core.ollama_client import OllamaClient
                    self._client_cache[cache_key] = OllamaClient(base_url=config.ollama_host)
                return self._client_cache[cache_key]
            else:
                from locallm.config import get_custom_platform
                from locallm.core.openai_client import OpenAIClient
                plat = get_custom_platform(config, target_backend)
                if plat:
                    cache_key = f"openai:{plat.api_base}:{plat.api_key}"
                    if cache_key not in self._client_cache:
                        self._client_cache[cache_key] = OpenAIClient(
                            api_base=plat.api_base,
                            api_key=plat.api_key,
                        )
                    return self._client_cache[cache_key]

            from locallm.core.openai_client import get_inference_client
            return self.client or get_inference_client(config)


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

    def do_DELETE(self) -> None:
        """Handle DELETE requests (e.g. session deletion)."""
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/api/sessions", "/v1/sessions"):
            try:
                from urllib.parse import parse_qs, urlparse
                from locallm.core.workspace import delete_workspace_session
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target_ws = params.get("workspace", ["default"])[0]
                session_id = params.get("id", [""])[0]
                if session_id:
                    delete_workspace_session(target_ws, session_id)
                self._send_json_response(200, {"success": True})
                self._log_request_event("DELETE", path, 200, detail=f"Deleted session {session_id}")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
            return

        if path in ("/api/workspaces", "/v1/workspaces"):
            try:
                from urllib.parse import parse_qs, urlparse
                from locallm.core.workspace import delete_workspace
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target_ws = params.get("name", [""])[0]
                active_ws = self.server.workspace or "default"
                if not target_ws:
                    self._send_json_response(400, {"error": "Workspace name is required"})
                    return
                success, msg = delete_workspace(target_ws, active_ws)
                if not success:
                    self._send_json_response(400, {"error": msg})
                    return
                self._send_json_response(200, {"success": True, "message": msg})
                self._log_request_event("DELETE", path, 200, detail=f"Deleted workspace {target_ws}")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
            return

        self._send_openai_error(404, f"The requested endpoint '{path}' was not found.")
        self._log_request_event("DELETE", path, 404)

    def do_PUT(self) -> None:
        """Handle PUT requests (e.g. workspace updates)."""
        path = self.path.split("?")[0].rstrip("/")
        if path in ("/api/workspaces", "/v1/workspaces"):
            try:
                import json
                from locallm.core.workspace import get_workspace_path, get_workspace_agents_path, rename_workspace

                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                body = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                raw_name = body.get("name", "").strip()
                old_name = (body.get("oldName") or body.get("old_name") or "").strip()
                new_name = (body.get("newName") or raw_name).strip()

                # If oldName is specified and differs from new_name, perform workspace rename
                if old_name and new_name and old_name != new_name:
                    active_ws = getattr(self.server, "workspace", None)
                    ok, msg = rename_workspace(old_name, new_name, active_ws)
                    if not ok:
                        self._send_json_response(400, {"error": msg})
                        return
                    if active_ws == old_name:
                        self.server.workspace = new_name

                ws_name = new_name or raw_name or old_name
                if not ws_name:
                    self._send_json_response(400, {"error": "Workspace name is required"})
                    return

                ws_path = get_workspace_path(ws_name)
                if not ws_path.exists():
                    self._send_json_response(404, {"error": f"Workspace '{ws_name}' not found"})
                    return

                meta_file = ws_path / "workspace.json"
                meta = {}
                if meta_file.exists():
                    try:
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    except Exception:
                        meta = {}

                if "description" in body:
                    meta["description"] = body["description"]
                if "icon" in body:
                    meta["icon"] = body["icon"]
                if "color" in body:
                    meta["color"] = body["color"]
                if "custom_instructions" in body:
                    meta["custom_instructions"] = body["custom_instructions"]
                    agents_file = get_workspace_agents_path(ws_name)
                    agents_file.write_text(f"# Workspace Instructions: {ws_name}\n\n{body['custom_instructions']}\n", encoding="utf-8")

                meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

                if "skills" in body and isinstance(body["skills"], list):
                    skills_dir = ws_path / "skills"
                    skills_dir.mkdir(exist_ok=True)
                    for s in body["skills"]:
                        s_id = (s.get("id") or s.get("name", "skill")).lower().replace(" ", "-")
                        s_file = skills_dir / f"{s_id}.md"
                        s_content = s.get("content") or f"# Skill: {s.get('name')}\n{s.get('description', '')}\n"
                        s_file.write_text(s_content, encoding="utf-8")

                self._send_json_response(200, {
                    "name": ws_name,
                    "description": meta.get("description", ""),
                    "icon": meta.get("icon", "Folder"),
                    "color": meta.get("color", "#3B82F6"),
                    "custom_instructions": meta.get("custom_instructions", ""),
                    "skills": body.get("skills", []),
                })
                self._log_request_event("PUT", path, 200, detail=f"Updated workspace {ws_name}")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
            return

        self._send_openai_error(404, f"The requested endpoint '{path}' was not found.")
        self._log_request_event("PUT", path, 404)

    def do_GET(self) -> None:
        """Handle GET requests for health diagnostics and model listings."""
        path = self.path.split("?")[0].rstrip("/")

        if path in ("", "/health", "/v1/health"):
            self.server.reload_config_if_needed()
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

        if path in ("/api/config", "/v1/config"):
            try:
                from locallm.config import load_config
                cfg = load_config()
                data = cfg.model_dump()
                data["model"] = getattr(cfg, "default_model", "gemma4:12b")
                data["provider"] = "ollama" if cfg.active_backend == "ollama" else "openai"
                data["contextLength"] = getattr(cfg, "context_window", 8192)
                self._send_json_response(200, data)
                self._log_request_event("GET", path, 200)
            except Exception as exc:
                self._send_openai_error(500, f"Failed to retrieve config: {exc}")
            return

        if path in ("/api/workspaces", "/v1/workspaces"):
            try:
                from locallm.core.workspace import list_workspaces
                workspaces = list_workspaces()
                self._send_json_response(200, workspaces)
                self._log_request_event("GET", path, 200, detail=f"{len(workspaces)} workspaces")
            except Exception as exc:
                self._send_openai_error(500, f"Failed to retrieve workspaces: {exc}")
            return

        if path in ("/api/sessions", "/v1/sessions"):
            try:
                from urllib.parse import parse_qs, urlparse
                from locallm.core.workspace import list_workspace_sessions, load_workspace_session
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target_ws = params.get("workspace", ["default"])[0]
                summary_sessions = list_workspace_sessions(target_ws)
                detailed_sessions = []
                for s in summary_sessions:
                    sess_id = s.get("session_id")
                    mem = load_workspace_session(target_ws, sess_id)
                    msgs = []
                    if mem and getattr(mem, "history", None):
                        for idx, h in enumerate(mem.history):
                            msgs.append({
                                "id": f"{sess_id}-{idx}",
                                "role": h.get("role", "user"),
                                "content": h.get("content", ""),
                                "timestamp": int(time.time() * 1000),
                                "files": h.get("files"),
                                "sources": h.get("sources"),
                                "options": h.get("options"),
                            })
                    raw_title = s.get("title") or s.get("last_snippet") or "New Chat"
                    clean_title = re.sub(r"<(?:think|thought)>[\s\S]*?(?:</(?:think|thought)>|$)", "", raw_title, flags=re.IGNORECASE).strip()
                    clean_title = re.sub(r"^[\"\'«»“”\s*#`_-]+|[\"\'«»“”\s*#`_-]+$", "", clean_title).strip()
                    clean_title = re.sub(r"^(?:Title|Judul|Topic|Subjek)\s*:\s*", "", clean_title, flags=re.IGNORECASE).strip()
                    if clean_title and "\n" in clean_title:
                        clean_title = clean_title.split("\n")[0].strip()
                    detailed_sessions.append({
                        "id": sess_id,
                        "title": clean_title or "New Chat",
                        "workspace": target_ws,
                        "updatedAt": s.get("updated_at"),
                        "messages": msgs
                    })
                self._send_json_response(200, detailed_sessions)
                self._log_request_event("GET", path, 200, detail=f"{len(detailed_sessions)} sessions")
            except Exception as exc:
                self._send_openai_error(500, f"Failed to retrieve sessions: {exc}")
            return

        if path in ("/v1/models", "/models", "/api/models"):
            try:
                self.server.reload_config_if_needed()
                from urllib.parse import parse_qs, urlparse
                parsed_url = urlparse(self.path)
                params = parse_qs(parsed_url.query)
                target_backend = params.get("backend", [""])[0] or self.headers.get("X-Backend", "")
                effective_client = self.server.get_client_for_request(backend=target_backend)

                raw_models: List[Dict[str, Any]] = []
                if hasattr(effective_client, "list_models"):
                    raw_models = effective_client.list_models() or []

                model_entries: List[Dict[str, Any]] = [
                    {
                        "id": "locallm-agent",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "locallm",
                        "permission": [],
                        "root": "locallm-agent",
                        "parent": None,
                        "capabilities": {"files": True, "webSearch": True, "tools": True},
                    },
                    {
                        "id": "auto",
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "locallm",
                        "permission": [],
                        "root": "auto",
                        "parent": None,
                        "capabilities": {"files": True, "webSearch": True, "tools": True},
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
                            "capabilities": {"files": True, "webSearch": True, "tools": True},
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

        # 1. Configuration sync endpoint
        if path in ("/api/config", "/v1/config"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                from locallm.config import load_config, save_config, LocaLLMConfig
                current_cfg = load_config()
                current_dict = current_cfg.model_dump()
                current_dict.update({k: v for k, v in payload.items() if k in current_dict})
                if "model" in payload and "default_model" not in payload:
                    current_dict["default_model"] = payload["model"]
                new_cfg = LocaLLMConfig(**current_dict)
                save_config(new_cfg)
                self.server.config = new_cfg
                self.server.default_model = new_cfg.default_model
                self.server.workspace = new_cfg.active_workspace
                from locallm.core.openai_client import get_inference_client
                with self.server._client_lock:
                    self.server.client = get_inference_client(new_cfg)
                from locallm.config import get_config_file_path
                cfg_p = get_config_file_path()
                if cfg_p.exists():
                    self.server._config_mtime = cfg_p.stat().st_mtime
                self._send_json_response(200, {"success": True, "config": new_cfg.model_dump()})
                self._log_request_event("POST", path, 200, detail="Config updated & hot-reloaded")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
                self._log_request_event("POST", path, 500, detail=str(exc))
            return

        # 2. Workspace creation endpoint
        if path in ("/api/workspaces", "/v1/workspaces"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                from locallm.core.workspace import create_workspace
                name = str(payload.get("name", "")).strip()
                desc = str(payload.get("description", "")).strip()
                if not name:
                    self._send_json_response(400, {"error": "Workspace name is required"})
                    return
                ws_path = create_workspace(name, description=desc)
                self._send_json_response(200, {"name": name, "description": desc, "path": str(ws_path)})
                self._log_request_event("POST", path, 200, detail=f"Created workspace {name}")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
            return

        # 3. Session saving endpoint
        if path in ("/api/sessions", "/v1/sessions"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                from locallm.core.workspace import save_workspace_session
                from locallm.core.memory import ConversationMemory
                ws_name = payload.get("workspace", "default")
                session_id = payload.get("id", str(int(time.time())))
                memory = ConversationMemory()
                clean_history = []
                for msg in payload.get("messages", []):
                    item = {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                    if msg.get("sources"):
                        item["sources"] = msg.get("sources")
                    if msg.get("files"):
                        item["files"] = msg.get("files")
                    if msg.get("options"):
                        item["options"] = msg.get("options")
                    clean_history.append(item)
                raw_title = payload.get("title", "New Chat")
                clean_title = re.sub(r"<(?:think|thought)>[\s\S]*?(?:</(?:think|thought)>|$)", "", raw_title, flags=re.IGNORECASE).strip()
                clean_title = re.sub(r"^[\"\'«»“”\s*#`_-]+|[\"\'«»“”\s*#`_-]+$", "", clean_title).strip()
                clean_title = re.sub(r"^(?:Title|Judul|Topic|Subjek)\s*:\s*", "", clean_title, flags=re.IGNORECASE).strip()
                if clean_title and "\n" in clean_title:
                    clean_title = clean_title.split("\n")[0].strip()
                save_workspace_session(ws_name, session_id, memory, metadata={
                    "title": clean_title or "New Chat",
                    "session_id": session_id,
                    "workspace": ws_name,
                    "model": payload.get("model", "-")
                })
                self._send_json_response(200, {"success": True})
                self._log_request_event("POST", path, 200, detail=f"Saved session {session_id}")
            except Exception as exc:
                self._send_json_response(500, {"error": str(exc)})
            return

        # 3.5 File parsing endpoint for .docx, .pdf, txt, etc.
        if path in ("/api/parse-file", "/v1/parse-file"):
            try:
                import base64
                from locallm.core.file_parser import parse_attachment_file
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                filename = payload.get("filename", "file.txt")
                raw_b64 = payload.get("data", "")
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                file_bytes = base64.b64decode(raw_b64) if raw_b64 else b""

                success, extracted_text, err = parse_attachment_file(filename, file_bytes)
                if not success:
                    self._send_json_response(400, {"success": False, "error": err, "text": ""})
                    return
                self._send_json_response(200, {"success": True, "text": extracted_text, "filename": filename})
                self._log_request_event("POST", path, 200, detail=f"Parsed file {filename}")
            except Exception as exc:
                self._send_json_response(500, {"success": False, "error": str(exc), "text": ""})
            return
        # 4. GitHub Skill inspection endpoint
        if path in ("/api/skills/inspect", "/v1/skills/inspect"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                from locallm.core.workspace import inspect_github_skills
                source = str(payload.get("source", "")).strip()
                if not source:
                    self._send_json_response(400, {"success": False, "error": "Source repository or URL is required."})
                    return
                ok, msg, available, zip_bytes, target_subpath = inspect_github_skills(source)
                self._send_json_response(200 if ok else 400, {
                    "success": ok,
                    "message": msg,
                    "skills": available,
                    "count": len(available),
                })
                self._log_request_event("POST", path, 200 if ok else 400, detail=f"Inspected {source}: {len(available)} skills")
            except Exception as exc:
                self._send_json_response(500, {"success": False, "error": str(exc)})
            return

        # 5. GitHub Skill installation endpoint
        if path in ("/api/skills/install", "/v1/skills/install"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8")) if content_length > 0 else {}
                from locallm.core.workspace import install_skill_from_source
                source = str(payload.get("source", "")).strip()
                target_ws = str(payload.get("workspace", "")).strip() or self.server.workspace or "default"
                selected_skills = payload.get("skills", None)
                if not source:
                    self._send_json_response(400, {"success": False, "error": "Source repository or URL is required."})
                    return
                ok, msg, installed = install_skill_from_source(target_ws, source, selected_skills)
                self._send_json_response(200 if ok else 400, {
                    "success": ok,
                    "message": msg,
                    "installed": installed,
                    "count": len(installed),
                })
                self._log_request_event("POST", path, 200 if ok else 400, detail=f"Installed to {target_ws}: {len(installed)} skills")
            except Exception as exc:
                self._send_json_response(500, {"success": False, "error": str(exc)})
            return

        if path not in ("/v1/chat/completions", "/chat/completions", "/api/chat"):
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

        # Extract options from request body
        options = payload.get("options", {})
        web_search_enabled = bool(options.get("webSearch", False))
        tools_enabled = bool(options.get("tools", False))

        # Extract last user prompt
        last_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_prompt = str(m.get("content", ""))
                break

        # Check universal web search invocation: UI options flag, command tags, or URL targets
        is_explicit_search = bool(
            re.match(r"^(?:@web|/web|/search|web:|search:)\b", last_prompt.strip(), re.IGNORECASE)
        )
        should_search_web = web_search_enabled or is_explicit_search

        if tools_enabled:
            base_directive = (
                "\n\nDirectives (Tools Enabled): Workspace agent tools, skills, and internet access are enabled for this session. "
                "Never say you cannot perform tasks because you are 'just an AI'. "
                "Consult the workspace skills catalogue and guidelines above to formulate practical execution steps, scripts, or recommended solutions."
            )
        elif not should_search_web:
            base_directive = (
                "\n\nDirectives: You are operating in conversational assistant mode. You have complete awareness of the active workspace context, persona, and skills catalogue listed above. "
                "When answering inquiries or advising the user, refer to and explain any relevant workspace skills. "
                "Do NOT output automated tool-call execution blocks or JSON commands unless tools are specifically enabled for this turn."
            )
        else:
            base_directive = (
                "\n\nDirectives: You have active live internet browsing capabilities. Synthesize the web search findings into a comprehensive, direct answer. "
                "Do not state that you cannot access the web or are just an AI."
            )

        # Resolve active workspace context
        req_ws = self.headers.get("X-Workspace", "").strip() or self.server.workspace
        ws_context = load_workspace_context(req_ws) + base_directive

        # Inject workspace context into system messages
        processed_messages = self._prepare_messages_with_context(messages, ws_context)

        # Resolve target model & backend
        self.server.reload_config_if_needed()
        backend_req = str(payload.get("backend", "") or payload.get("provider", "") or self.headers.get("X-Backend", "")).strip()

        # Intelligent Router resolution
        target_model = model_req
        if model_req.lower() in ("auto", "locallm-agent", ""):
            last_prompt_route = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_prompt_route = str(m.get("content", ""))
                    break
            temp_client = self.server.get_client_for_request(model=self.server.default_model, backend=backend_req)
            if last_prompt_route:
                route_res = route_prompt(last_prompt_route, self.server.config, temp_client)
                target_model = route_res.selected_model
            else:
                target_model = self.server.default_model

        inference_client = self.server.get_client_for_request(model=target_model, backend=backend_req)

        if stream_requested:
            self._handle_streaming_completion(
                target_model=target_model,
                messages=processed_messages,
                temperature=temperature,
                context_window=context_window,
                start_time=start_time,
                path=path,
                client=inference_client,
                should_search_web=should_search_web,
                tools_enabled=tools_enabled,
                last_prompt=last_prompt,
                workspace_name=req_ws,
            )
        else:
            self._handle_non_streaming_completion(
                target_model=target_model,
                messages=processed_messages,
                temperature=temperature,
                context_window=context_window,
                start_time=start_time,
                path=path,
                client=inference_client,
                should_search_web=should_search_web,
                tools_enabled=tools_enabled,
                last_prompt=last_prompt,
                workspace_name=req_ws,
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

    def _inject_search_context(
        self,
        messages: List[Dict[str, Any]],
        search_directive: str,
    ) -> List[Dict[str, Any]]:
        """Append real-time search results and web directives to the system prompt."""
        if not search_directive:
            return list(messages)

        result: List[Dict[str, Any]] = []
        has_system = False

        for msg in messages:
            if msg.get("role") == "system" and not has_system:
                existing = str(msg.get("content", ""))
                combined = f"{existing}\n\n{search_directive}"
                result.append({"role": "system", "content": combined})
                has_system = True
            else:
                result.append(dict(msg))

        if not has_system:
            result.insert(0, {
                "role": "system",
                "content": search_directive,
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
        client: Optional[Any] = None,
        should_search_web: bool = False,
        tools_enabled: bool = False,
        last_prompt: str = "",
        workspace_name: str = "default",
    ) -> None:
        """Execute non-streaming chat turn and deliver standard OpenAI completion response."""
        stats: Dict[str, Any] = {}
        active_client = client or self.server.client
        try:
            if should_search_web and last_prompt:
                search_directive = ""
                try:
                    from locallm.core.tools.web import extract_search_query, perform_web_search
                    clean_query = extract_search_query(last_prompt) or last_prompt.strip()
                    search_res = perform_web_search(clean_query, max_results=5)
                    if search_res and not search_res.startswith("Error:"):
                        search_directive = (
                            f"\n\n[Web Search Results for '{clean_query}']:\n{search_res}\n\n"
                            "Directives: You HAVE real-time internet search capabilities provided directly by the host environment. "
                            "The above verified live search results were retrieved for this query. "
                            "Never state that you are 'just an AI', 'do not have internet access', or 'cannot browse the web'. "
                            "Thoroughly answer the user's inquiry using these search results and cite your sources using markdown links [Source Title](URL) directly in your response."
                        )
                    else:
                        search_directive = (
                            f"\n\n[Web Search Notice for '{clean_query}']:\n(Pencarian web real-time telah dijalankan namun tidak menemukan hasil spesifik atau terjadi kendala jaringan sementara).\n"
                            "Directives: Real-time web search was actively performed by the system for this query. "
                            "Never claim you cannot browse the web or lack internet access. "
                            "Answer the inquiry as accurately as possible using your knowledge base while explaining that live search returned no direct results for the specific query."
                        )
                except Exception as exc:
                    self._log_request_event("WARN", path, 500, detail=f"Web search error: {exc}")
                    search_directive = (
                        f"\n\n[Web Search Notice]: Gagal menghubungi penyedia pencarian web ({exc}). "
                        "Jawab pertanyaan user sebaik mungkin menggunakan basis pengetahuan Anda dan sebutkan bahwa pencarian web sedang mengalami kendala jaringan. "
                        "Jangan mengklaim bahwa Anda tidak memiliki kemampuan pencarian web karena Anda hanyalah model AI."
                    )
                messages = self._inject_search_context(messages, search_directive)

            turn_msg: Optional[Dict[str, Any]] = None
            if hasattr(active_client, "chat_turn"):
                turn_msg = active_client.chat_turn(
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
        client: Optional[Any] = None,
        should_search_web: bool = False,
        tools_enabled: bool = False,
        last_prompt: str = "",
        workspace_name: str = "default",
    ) -> None:
        """Stream completion tokens via Server-Sent Events (SSE) with dynamic thought progress."""
        active_client = client or self.server.client
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

        def _send_delta(content_str: str) -> None:
            if not content_str:
                return
            delta_chunk = {
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created_ts,
                "model": target_model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content_str},
                        "finish_reason": None,
                    }
                ],
            }
            _send_chunk(f"data: {json.dumps(delta_chunk)}\n\n".encode("utf-8"))

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

            # Dynamic live progress: Stream thought step tokens before model inference
            if should_search_web and last_prompt:
                _send_delta("<think>\nRefining user inquiry...\n")
                search_directive = ""
                try:
                    from locallm.core.tools.web import extract_search_query, perform_web_search
                    clean_query = extract_search_query(last_prompt) or last_prompt.strip()
                    _send_delta(f"Searching web for '{clean_query}'...\n")

                    search_res = perform_web_search(clean_query, max_results=5)
                    _send_delta("Synthesizing verified findings...\n</think>\n\n")

                    if search_res and not search_res.startswith("Error:"):
                        search_directive = (
                            f"\n\n[Web Search Results for '{clean_query}']:\n{search_res}\n\n"
                            "Directives: You HAVE real-time internet search capabilities provided directly by the host environment. "
                            "The above verified live search results were retrieved for this query. "
                            "Never state that you are 'just an AI', 'do not have internet access', or 'cannot browse the web'. "
                            "Thoroughly answer the user's inquiry using these search results and cite your sources using markdown links [Source Title](URL) directly in your response."
                        )
                    else:
                        search_directive = (
                            f"\n\n[Web Search Notice for '{clean_query}']:\n(Pencarian web real-time telah dijalankan namun tidak menemukan hasil spesifik atau terjadi kendala jaringan sementara).\n"
                            "Directives: Real-time web search was actively performed by the system for this query. "
                            "Never claim you cannot browse the web or lack internet access. "
                            "Answer the inquiry as accurately as possible using your knowledge base while explaining that live search returned no direct results for the specific query."
                        )
                except Exception as exc:
                    self._log_request_event("WARN", path, 500, detail=f"Web search error: {exc}")
                    _send_delta("Synthesizing response...\n</think>\n\n")
                    search_directive = (
                        f"\n\n[Web Search Notice]: Gagal menghubungi penyedia pencarian web ({exc}). "
                        "Jawab pertanyaan user sebaik mungkin menggunakan basis pengetahuan Anda dan sebutkan bahwa pencarian web sedang mengalami kendala jaringan. "
                        "Jangan mengklaim bahwa Anda tidak memiliki kemampuan pencarian web karena Anda hanyalah model AI."
                    )
                messages = self._inject_search_context(messages, search_directive)

            elif tools_enabled:
                _send_delta("<think>\nEvaluating workspace skills & tools...\n")
                try:
                    from locallm.core.tools import get_all_assistant_tools, execute_tool
                    available_tools = get_all_assistant_tools(workspace_name)
                    if available_tools and hasattr(active_client, "chat_turn"):
                        planning_msg = active_client.chat_turn(
                            model=target_model,
                            messages=messages,
                            tools=available_tools,
                            temperature=temperature,
                            num_ctx=context_window,
                        )
                        tool_calls = planning_msg.get("tool_calls") if isinstance(planning_msg, dict) else None
                        if tool_calls:
                            for tc in tool_calls:
                                fn_call = tc.get("function", {}) if isinstance(tc, dict) else {}
                                fn_name = fn_call.get("name", "")
                                fn_args = fn_call.get("arguments", {})
                                if isinstance(fn_args, str):
                                    try:
                                        fn_args = json.loads(fn_args)
                                    except Exception:
                                        fn_args = {}
                                _send_delta(f"Executing tool '{fn_name}'...\n")
                                tool_res = execute_tool(fn_name, fn_args, workspace_name=workspace_name)
                                messages.append({
                                    "role": "tool",
                                    "name": fn_name,
                                    "content": str(tool_res),
                                })
                            _send_delta("Synthesizing findings...\n</think>\n\n")
                        else:
                            _send_delta("Formulating response...\n</think>\n\n")
                    else:
                        _send_delta("Formulating response...\n</think>\n\n")
                except Exception as tool_exc:
                    self._log_request_event("WARN", path, 500, detail=f"Tool evaluation error: {tool_exc}")
                    _send_delta("Formulating response...\n</think>\n\n")
            else:
                # Immediate initial thought chunk so user sees instant feedback during model prefill
                _send_delta("<think>\nRefining user inquiry...\n</think>\n\n")

            # Stream generated tokens
            if hasattr(active_client, "chat_stream"):
                for token in active_client.chat_stream(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    num_ctx=context_window,
                ):
                    if not token:
                        continue
                    token_count += 1
                    _send_delta(token)

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
            try:
                err_msg = str(exc)
                if "Inference execution failed" in err_msg and "{" in err_msg:
                    import re
                    m = re.search(r"'message':\s*'([^']+)'", err_msg)
                    if m:
                        err_msg = m.group(1).split("\n")[0]
                err_chunk = {
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created_ts,
                    "model": target_model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": f"\n\n[Gagal memproses respon: {err_msg}]"},
                            "finish_reason": "error",
                        }
                    ],
                }
                _send_chunk(f"data: {json.dumps(err_chunk)}\n\n".encode("utf-8"))
                _send_chunk(b"data: [DONE]\n\n")
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass

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
