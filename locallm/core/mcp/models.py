"""Model Context Protocol (MCP) data models and server configuration schemas."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class MCPServerConfig:
    """Configuration for an individual Model Context Protocol server."""

    name: str
    transport: str = "stdio"  # "stdio" or "sse"
    command: Optional[str] = None  # e.g. "npx", "python", "node", "uvx"
    args: List[str] = field(default_factory=list)  # e.g. ["-y", "@modelcontextprotocol/server-filesystem"]
    env: Dict[str, str] = field(default_factory=dict)  # environment variables
    url: Optional[str] = None  # for SSE transport: e.g. "http://127.0.0.1:8000/sse"
    enabled: bool = True
    privileged: bool = False  # whether all tools from this server require administrative privileges
    privileged_tools: List[str] = field(default_factory=list)  # specific tool names that require privilege
    description: str = ""
    scope: str = "global"  # "global" or "workspace"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation matching Claude Desktop / standard schema."""
        data: Dict[str, Any] = {
            "transport": self.transport,
            "enabled": self.enabled,
        }
        if self.transport == "stdio":
            if self.command:
                data["command"] = self.command
            if self.args:
                data["args"] = self.args
            if self.env:
                data["env"] = self.env
        elif self.transport == "sse":
            if self.url:
                data["url"] = self.url

        if self.privileged:
            data["privileged"] = True
        if self.privileged_tools:
            data["privileged_tools"] = self.privileged_tools
        if self.description:
            data["description"] = self.description

        return data

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any], scope: str = "global") -> "MCPServerConfig":
        """Construct MCPServerConfig from dictionary representation."""
        transport = str(data.get("transport", "stdio")).strip().lower()
        if not data.get("command") and data.get("url"):
            transport = "sse"

        return cls(
            name=name.strip(),
            transport=transport,
            command=data.get("command"),
            args=list(data.get("args", [])),
            env=dict(data.get("env", {})),
            url=data.get("url"),
            enabled=bool(data.get("enabled", True)),
            privileged=bool(data.get("privileged", False)),
            privileged_tools=list(data.get("privileged_tools", [])),
            description=str(data.get("description", "")),
            scope=scope,
        )


@dataclass
class MCPToolInfo:
    """Discovered tool definition exposed by an MCP server."""

    server_name: str
    name: str  # Original tool name in MCP server
    namespaced_name: str  # Unique identifier, e.g. "mcp__github__search_issues"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    is_privileged: bool = False

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert MCP tool definition into OpenAI/Ollama function calling schema."""
        desc = self.description.strip() if self.description else f"Tool from MCP server '{self.server_name}'"
        annotated_desc = f"[MCP: {self.server_name}] {desc}"

        return {
            "type": "function",
            "function": {
                "name": self.namespaced_name,
                "description": annotated_desc,
                "parameters": self.input_schema,
            },
        }


@dataclass
class MCPServerStatus:
    """Runtime health and diagnostics for a connected MCP server."""

    server_name: str
    transport: str
    is_connected: bool
    tools_count: int = 0
    server_info: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
