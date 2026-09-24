"""Model Context Protocol (MCP) modular package for locaLLM."""

from typing import Any, Dict, List, Optional, Set, Tuple

from locallm.core.mcp.client import MCPClient
from locallm.core.mcp.manager import MCPManager, mcp_manager
from locallm.core.mcp.models import MCPServerConfig, MCPServerStatus, MCPToolInfo


def get_all_mcp_tools(workspace_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all tools exposed across all active Model Context Protocol servers."""
    try:
        return mcp_manager.get_all_tools(workspace_name=workspace_name)
    except Exception:
        return []


def get_mcp_privileged_tools(workspace_name: Optional[str] = None) -> Set[str]:
    """Return all privileged tool names across active Model Context Protocol servers."""
    try:
        return mcp_manager.get_privileged_tool_names(workspace_name=workspace_name)
    except Exception:
        return set()


def execute_mcp_tool(
    name: str,
    arguments: Dict[str, Any],
    workspace_name: Optional[str] = None,
) -> Tuple[bool, str]:
    """Delegate tool execution to an active Model Context Protocol server."""
    try:
        return mcp_manager.execute_tool(name, arguments, workspace_name=workspace_name)
    except Exception as exc:
        return True, f"Error executing MCP tool '{name}': {exc}"


__all__ = [
    "MCPManager",
    "mcp_manager",
    "MCPClient",
    "MCPServerConfig",
    "MCPToolInfo",
    "MCPServerStatus",
    "get_all_mcp_tools",
    "get_mcp_privileged_tools",
    "execute_mcp_tool",
]
