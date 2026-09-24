"""Model Context Protocol (MCP) Client managing server lifecycle and function execution."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from locallm.core.mcp.models import MCPServerConfig, MCPServerStatus, MCPToolInfo
from locallm.core.mcp.transport import BaseTransport, SSETransport, StdioTransport


class MCPClient:
    """Client connection to an individual Model Context Protocol server."""

    def __init__(self, config: MCPServerConfig, cwd: Optional[Path] = None) -> None:
        self.config = config
        self.cwd = cwd or Path.cwd()
        self.server_info: Dict[str, Any] = {}
        self.server_capabilities: Dict[str, Any] = {}
        self.tools: Dict[str, MCPToolInfo] = {}  # namespaced_name -> MCPToolInfo
        self.raw_tool_names: Dict[str, str] = {}  # namespaced_name -> raw tool name
        self._initialized = False

        if config.transport == "sse":
            if not config.url:
                raise ValueError(f"MCP server '{config.name}' requires a 'url' for SSE transport.")
            self.transport: BaseTransport = SSETransport(url=config.url)
        else:
            if not config.command:
                raise ValueError(f"MCP server '{config.name}' requires a 'command' for stdio transport.")
            self.transport = StdioTransport(
                command=config.command,
                args=config.args,
                env=config.env,
                cwd=self.cwd,
            )

    def connect_and_initialize(self, timeout: float = 30.0) -> None:
        """Establish transport connection and execute standard MCP initialization handshake."""
        if self._initialized and self.transport.is_alive():
            return

        self.transport.connect()

        # Step 1: Send 'initialize' request
        init_params: Dict[str, Any] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "locaLLM",
                "version": "0.1.0",
            },
        }

        result = self.transport.send_request("initialize", params=init_params, timeout=timeout)
        self.server_info = result.get("serverInfo", {})
        self.server_capabilities = result.get("capabilities", {})

        # Step 2: Send 'notifications/initialized'
        self.transport.send_notification("notifications/initialized")
        self._initialized = True

        # Step 3: Fetch discovered tools
        self.refresh_tools(timeout=timeout)

    def refresh_tools(self, timeout: float = 15.0) -> List[MCPToolInfo]:
        """Query 'tools/list' and refresh discovered tool definitions."""
        if not self._initialized:
            self.connect_and_initialize()

        result = self.transport.send_request("tools/list", timeout=timeout)
        raw_tools = result.get("tools", [])

        self.tools.clear()
        self.raw_tool_names.clear()

        for t in raw_tools:
            raw_name = str(t.get("name", "")).strip()
            if not raw_name:
                continue

            # Generate namespaced identifier to prevent cross-server collisions
            namespaced = f"mcp__{self.config.name}__{raw_name}"
            desc = str(t.get("description", "")).strip()
            schema = t.get("inputSchema", {"type": "object", "properties": {}})

            # Determine whether tool is privileged
            is_priv = self.config.privileged or (raw_name in self.config.privileged_tools)

            tool_info = MCPToolInfo(
                server_name=self.config.name,
                name=raw_name,
                namespaced_name=namespaced,
                description=desc,
                input_schema=schema,
                is_privileged=is_priv,
            )
            self.tools[namespaced] = tool_info
            self.raw_tool_names[namespaced] = raw_name

        return list(self.tools.values())

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 60.0) -> str:
        """Execute a tool via 'tools/call' on this MCP server."""
        if not self._initialized or not self.transport.is_alive():
            self.connect_and_initialize()

        # Resolve raw tool name
        raw_name = self.raw_tool_names.get(tool_name, tool_name)
        if raw_name.startswith(f"mcp__{self.config.name}__"):
            raw_name = raw_name[len(f"mcp__{self.config.name}__") :]

        params: Dict[str, Any] = {
            "name": raw_name,
            "arguments": arguments,
        }

        try:
            result = self.transport.send_request("tools/call", params=params, timeout=timeout)
        except Exception as exc:
            return f"Error executing MCP tool '{raw_name}': {exc}"

        # Parse content blocks from response
        is_error = bool(result.get("isError", False))
        content_items = result.get("content", [])

        output_parts: List[str] = []
        for item in content_items:
            if isinstance(item, dict):
                item_type = item.get("type", "text")
                if item_type == "text":
                    output_parts.append(str(item.get("text", "")))
                elif item_type == "resource":
                    res = item.get("resource", {})
                    output_parts.append(f"[Resource {res.get('uri', '')}]: {res.get('text', '')}")
                else:
                    output_parts.append(json.dumps(item, ensure_ascii=False))
            else:
                output_parts.append(str(item))

        final_text = "\n".join(output_parts).strip()
        if not final_text:
            final_text = "(Action executed with no return content)"

        if is_error:
            return f"MCP Tool Error: {final_text}"

        return final_text

    def get_status(self) -> MCPServerStatus:
        """Return real-time diagnostic status of the connection."""
        is_connected = self._initialized and self.transport.is_alive()
        return MCPServerStatus(
            server_name=self.config.name,
            transport=self.config.transport,
            is_connected=is_connected,
            tools_count=len(self.tools),
            server_info=self.server_info,
        )

    def close(self) -> None:
        """Close connection and terminate server process."""
        self._initialized = False
        self.transport.close()
