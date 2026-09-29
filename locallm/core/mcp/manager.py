"""Multi-server Model Context Protocol (MCP) Manager for locaLLM."""

import json
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from locallm.core.mcp.client import MCPClient
from locallm.core.mcp.models import MCPServerConfig, MCPServerStatus, MCPToolInfo


def get_global_mcp_config_path() -> Path:
    """Return path to global MCP configuration (~/.locallm/mcp_servers.json)."""
    base = Path.home() / ".locallm"
    base.mkdir(parents=True, exist_ok=True)
    return base / "mcp_servers.json"


def get_workspace_mcp_config_path(workspace_name: Optional[str] = None) -> Optional[Path]:
    """Return path to workspace-specific MCP configuration (<workspace>/mcp.json)."""
    if not workspace_name:
        return None
    try:
        from locallm.core.workspace import get_workspace_path

        ws_dir = get_workspace_path(workspace_name)
        if ws_dir.exists():
            return ws_dir / "mcp.json"
    except Exception:
        pass
    return None


class MCPManager:
    """Central pool manager coordinating multiple concurrent MCP server connections."""

    _instance: Optional["MCPManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MCPManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._clients: Dict[str, MCPClient] = {}
        self._tool_to_server: Dict[str, str] = {}  # tool_name -> server_name
        self._pool_lock = threading.Lock()
        self._initialized = True

    def load_configs(self, workspace_name: Optional[str] = None) -> Dict[str, MCPServerConfig]:
        """Load and merge MCP server configurations from global and workspace scopes."""
        configs: Dict[str, MCPServerConfig] = {}

        # 1. Global configurations (~/.locallm/mcp_servers.json)
        global_path = get_global_mcp_config_path()
        if global_path.is_file():
            try:
                data = json.loads(global_path.read_text(encoding="utf-8"))
                servers_dict = data.get("mcpServers", data)
                if isinstance(servers_dict, dict):
                    for name, s_data in servers_dict.items():
                        if isinstance(s_data, dict):
                            configs[name] = MCPServerConfig.from_dict(name, s_data, scope="global")
            except Exception:
                pass

        # 2. Workspace-specific configurations (<workspace>/mcp.json)
        ws_path = get_workspace_mcp_config_path(workspace_name)
        if ws_path and ws_path.is_file():
            try:
                data = json.loads(ws_path.read_text(encoding="utf-8"))
                servers_dict = data.get("mcpServers", data)
                if isinstance(servers_dict, dict):
                    for name, s_data in servers_dict.items():
                        if isinstance(s_data, dict):
                            configs[name] = MCPServerConfig.from_dict(name, s_data, scope="workspace")
            except Exception:
                pass

        return configs

    def save_config(self, config: MCPServerConfig, workspace_name: Optional[str] = None) -> None:
        """Persist an MCP server configuration to the appropriate JSON file."""
        if config.scope == "workspace":
            target_path = get_workspace_mcp_config_path(workspace_name)
            if not target_path:
                target_path = get_global_mcp_config_path()
                config.scope = "global"
        else:
            target_path = get_global_mcp_config_path()

        target_path.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {"mcpServers": {}}
        if target_path.is_file():
            try:
                raw = json.loads(target_path.read_text(encoding="utf-8"))
                data = {"mcpServers": raw.get("mcpServers", raw)}
            except Exception:
                data = {"mcpServers": {}}

        data["mcpServers"][config.name] = config.to_dict()
        target_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # Invalidate active client if running
        with self._pool_lock:
            old_client = self._clients.pop(config.name, None)
            if old_client:
                old_client.close()

    def remove_config(self, name: str, scope: str = "global", workspace_name: Optional[str] = None) -> bool:
        """Delete an MCP server from configuration and terminate any active process."""
        target_path = (
            get_workspace_mcp_config_path(workspace_name)
            if scope == "workspace"
            else get_global_mcp_config_path()
        )
        if not target_path or not target_path.is_file():
            return False

        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            servers_dict = data.get("mcpServers", data)
            if name in servers_dict:
                del servers_dict[name]
                data["mcpServers"] = servers_dict
                target_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

                with self._pool_lock:
                    client = self._clients.pop(name, None)
                    if client:
                        client.close()
                return True
        except Exception:
            pass
        return False

    def get_client(self, name: str, workspace_name: Optional[str] = None) -> Optional[MCPClient]:
        """Retrieve or create an active MCPClient for a configured server."""
        with self._pool_lock:
            if name in self._clients:
                client = self._clients[name]
                if client.transport.is_alive():
                    return client

            configs = self.load_configs(workspace_name)
            config = configs.get(name)
            if not config or not config.enabled:
                return None

            try:
                client = MCPClient(config)
                client.connect_and_initialize()
                self._clients[name] = client
                return client
            except Exception:
                return None

    def test_server(
        self,
        name: str,
        workspace_name: Optional[str] = None,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Test connection to an MCP server, execute handshake, and fetch tool schemas."""
        configs = self.load_configs(workspace_name)
        config = configs.get(name)
        if not config:
            return False, f"Server '{name}' is not configured.", []

        test_client: Optional[MCPClient] = None
        try:
            test_client = MCPClient(config)
            test_client.connect_and_initialize(timeout=15.0)
            tools = test_client.refresh_tools(timeout=10.0)
            schemas = [t.to_openai_schema() for t in tools]
            info = test_client.server_info
            name_str = info.get("name", name)
            ver_str = info.get("version", "unknown")
            msg = f"Connected successfully to '{name_str}' (v{ver_str}). Discovered {len(tools)} tool(s)."
            return True, msg, schemas
        except Exception as exc:
            return False, f"Connection failed: {exc}", []
        finally:
            if test_client:
                test_client.close()

    def get_all_tools(self, workspace_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Collect all exposed tools from all enabled MCP servers in OpenAI format."""
        configs = self.load_configs(workspace_name)
        aggregated_tools: List[Dict[str, Any]] = []

        with self._pool_lock:
            for name, cfg in configs.items():
                if not cfg.enabled:
                    continue

                client = self._clients.get(name)
                if not client or not client.transport.is_alive():
                    try:
                        client = MCPClient(cfg)
                        client.connect_and_initialize(timeout=10.0)
                        self._clients[name] = client
                    except Exception:
                        continue

                for namespaced_name, tool_info in client.tools.items():
                    self._tool_to_server[namespaced_name] = name
                    # Also register clean alias if non-colliding
                    if tool_info.name not in self._tool_to_server:
                        self._tool_to_server[tool_info.name] = name

                    aggregated_tools.append(tool_info.to_openai_schema())

        return aggregated_tools

    def get_privileged_tool_names(self, workspace_name: Optional[str] = None) -> Set[str]:
        """Return all tool names across enabled MCP servers that require administrative privilege."""
        configs = self.load_configs(workspace_name)
        priv_names: Set[str] = set()

        with self._pool_lock:
            for name, cfg in configs.items():
                if not cfg.enabled:
                    continue

                client = self._clients.get(name)
                if client:
                    for namespaced, tool_info in client.tools.items():
                        if tool_info.is_privileged:
                            priv_names.add(namespaced)
                            priv_names.add(tool_info.name)
                elif cfg.privileged:
                    # If whole server is privileged, mark any namespaced tools
                    priv_names.add(f"mcp__{name}__*")

        return priv_names

    def execute_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        workspace_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Determine if tool belongs to an MCP server, execute it, and return (handled, observation)."""
        server_name: Optional[str] = None

        if name.startswith("mcp__"):
            parts = name.split("__", 2)
            if len(parts) >= 2:
                server_name = parts[1]

        if not server_name:
            server_name = self._tool_to_server.get(name)

        if not server_name:
            return False, ""

        client = self.get_client(server_name, workspace_name=workspace_name)
        if not client:
            return True, f"Error: MCP server '{server_name}' is offline or not configured."

        obs = client.call_tool(name, arguments)
        return True, obs

    def get_statuses(self, workspace_name: Optional[str] = None) -> List[MCPServerStatus]:
        """Return diagnostic statuses for all configured MCP servers."""
        configs = self.load_configs(workspace_name)
        statuses: List[MCPServerStatus] = []

        with self._pool_lock:
            for name, cfg in configs.items():
                client = self._clients.get(name)
                if client and client.transport.is_alive():
                    statuses.append(client.get_status())
                else:
                    statuses.append(
                        MCPServerStatus(
                            server_name=name,
                            transport=cfg.transport,
                            is_connected=False,
                            tools_count=0,
                        )
                    )

        return statuses

    def close_all(self) -> None:
        """Cleanly shutdown and release all active MCP connections and child processes."""
        with self._pool_lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._tool_to_server.clear()


# Global Singleton Manager
mcp_manager = MCPManager()
