"""Central tool registry and modular entrypoint for locaLLM function calling."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from locallm.core.tools.base import BaseTool, FunctionTool, ToolRegistry, registry, tool
import locallm.core.tools.filesystem  # noqa: F401
from locallm.core.tools.filesystem import resolve_smart_path
import locallm.core.tools.messaging  # noqa: F401
from locallm.core.tools.parser import extract_fallback_tool_calls
import locallm.core.tools.system  # noqa: F401
from locallm.core.tools.ui import describe_tool_action, format_live_tool_report
import locallm.core.tools.web  # noqa: F401
from locallm.core.tools.web import decode_bing_url, perform_web_search

# Backward-compatible global schemas
ASSISTANT_TOOLS: List[Dict[str, Any]] = registry.get_schemas("assistant")
TELEGRAM_TOOLS: List[Dict[str, Any]] = registry.get_schemas("telegram")
WHATSAPP_TOOLS: List[Dict[str, Any]] = registry.get_schemas("whatsapp")


def get_all_assistant_tools(workspace_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all assistant tools including dynamically loaded tools from enabled plugins and MCP servers."""
    tools = list(ASSISTANT_TOOLS)
    try:
        from locallm.core.plugin_manager import get_active_plugin_tools

        tools += get_active_plugin_tools(workspace_name)
    except Exception:
        pass

    try:
        from locallm.core.mcp import get_all_mcp_tools

        tools += get_all_mcp_tools(workspace_name)
    except Exception:
        pass

    return tools


def get_all_privileged_tools(workspace_name: Optional[str] = None) -> Set[str]:
    """Return set of all privileged tool names across built-in, plugin, and MCP tools."""
    privileged: Set[str] = registry.get_privileged_tool_names()
    try:
        from locallm.core.plugin_manager import get_plugin_privileged_tools

        privileged = privileged.union(get_plugin_privileged_tools(workspace_name))
    except Exception:
        pass

    try:
        from locallm.core.mcp import get_mcp_privileged_tools

        privileged = privileged.union(get_mcp_privileged_tools(workspace_name))
    except Exception:
        pass

    return privileged


def get_caller_tools(
    is_authorized: bool,
    workspace_name: Optional[str] = "default",
    category: str = "assistant",
    allowed_tools_override: Optional[Set[str]] = None,
    denied_tools_override: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Return tool schemas filtered by caller authorization status and workspace policy."""
    if category == "assistant":
        all_tools = get_all_assistant_tools(workspace_name)
    elif category == "telegram":
        all_tools = list(TELEGRAM_TOOLS)
        try:
            from locallm.core.plugin_manager import get_active_plugin_tools

            all_tools += get_active_plugin_tools(workspace_name)
        except Exception:
            pass
        try:
            from locallm.core.mcp import get_all_mcp_tools

            all_tools += get_all_mcp_tools(workspace_name)
        except Exception:
            pass
    elif category == "whatsapp":
        all_tools = list(WHATSAPP_TOOLS)
        try:
            from locallm.core.plugin_manager import get_active_plugin_tools

            all_tools += get_active_plugin_tools(workspace_name)
        except Exception:
            pass
        try:
            from locallm.core.mcp import get_all_mcp_tools

            all_tools += get_all_mcp_tools(workspace_name)
        except Exception:
            pass
    else:
        all_tools = registry.get_schemas(category)

    privileged_tools = get_all_privileged_tools(workspace_name)
    filtered: List[Dict[str, Any]] = []

    for t in all_tools:
        name = t.get("function", {}).get("name", "")
        if not name:
            continue

        # 1. Explicit denial takes absolute priority
        if denied_tools_override and name in denied_tools_override:
            continue

        # 2. If caller is authorized (master/admin)
        if is_authorized:
            filtered.append(t)
            continue

        # 3. Caller is unauthorized / public:
        # If an explicit whitelist override is provided, only allow those tools
        if allowed_tools_override:
            if name in allowed_tools_override:
                filtered.append(t)
            continue

        # Default public filter: exclude any privileged tool
        if name not in privileged_tools:
            filtered.append(t)

    return filtered


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    permission_policy: str = "always_allow",
    interactive: bool = True,
    session_state: Optional[Dict[str, Any]] = None,
    workspace_name: Optional[str] = "default",
) -> str:
    """Execute a requested tool with permission policy, boundary verification, and plugin delegation."""
    # 0. Authorization check: strictly reject privileged actions if caller is unauthorized
    is_caller_authorized = True
    if session_state and "is_authorized" in session_state:
        is_caller_authorized = bool(session_state["is_authorized"])

    privileged_tools = get_all_privileged_tools(workspace_name)
    if not is_caller_authorized and name in privileged_tools:
        return "Access denied. Administrative privileges required."

    mutating_tools: Set[str] = registry.get_mutating_tool_names()
    try:
        from locallm.core.plugin_manager import get_plugin_mutating_tools

        mutating_tools = mutating_tools.union(get_plugin_mutating_tools(workspace_name))
    except Exception:
        pass

    if name in mutating_tools:
        effective_policy = permission_policy.lower()
        if session_state and "permission_override" in session_state:
            effective_policy = session_state["permission_override"]

        if effective_policy == "deny":
            return f"[Permission Denied] Policy is set to 'deny'. Mutating action '{name}' was blocked."

        if effective_policy == "ask" and interactive:
            import questionary
            from locallm.ui.theme import QUESTIONARY_STYLE, console

            console.print(f"\n[bold yellow]✦ Permission Request:[/] Agent requests permission to execute [bold cyan]{name}[/]")
            if name == "write_file":
                console.print(f"  [#aaaaaa]Path:[/] [bold]{arguments.get('path', '')}[/]")
            elif name == "create_directory":
                console.print(f"  [#aaaaaa]Directory:[/] [bold]{arguments.get('path', '')}[/]")
            elif name == "execute_command":
                console.print(f"  [#aaaaaa]Command:[/] [bold]{arguments.get('command', '')}[/]")

            ans = questionary.select(
                f"Authorize agent to execute {name}?",
                choices=[
                    "Allow Once",
                    "Always Allow (this session)",
                    "Deny",
                ],
                style=QUESTIONARY_STYLE,
            ).ask()

            if ans == "Always Allow (this session)":
                if session_state is not None:
                    session_state["permission_override"] = "always_allow"
            elif ans != "Allow Once":
                return f"[Permission Denied] User rejected execution of '{name}'."

    # Context preparation (boundary, workspace, session)
    context: Dict[str, Any] = {
        "workspace_name": workspace_name,
        "session_state": session_state,
    }
    if session_state and "boundary_dir" in session_state:
        context["boundary_dir"] = session_state["boundary_dir"]

    # Execute from central registry
    tool_instance = registry.get(name)
    if tool_instance is not None:
        try:
            return tool_instance.execute(arguments, context=context)
        except Exception as exc:
            return f"Error executing tool '{name}': {exc}"

    # Dynamically dispatch to installed and enabled plugins
    try:
        from locallm.core.plugin_manager import execute_plugin_tool

        handled, obs = execute_plugin_tool(name, arguments, workspace_name=workspace_name)
        if handled:
            return obs
    except Exception as exc:
        return f"Error executing plugin tool '{name}': {exc}"

    # Dynamically dispatch to connected Model Context Protocol (MCP) servers
    try:
        from locallm.core.mcp import execute_mcp_tool

        handled, obs = execute_mcp_tool(name, arguments, workspace_name=workspace_name)
        if handled:
            return obs
    except Exception as exc:
        return f"Error executing MCP tool '{name}': {exc}"

    return f"Unknown tool: '{name}'"


__all__ = [
    "BaseTool",
    "FunctionTool",
    "ToolRegistry",
    "registry",
    "tool",
    "ASSISTANT_TOOLS",
    "TELEGRAM_TOOLS",
    "WHATSAPP_TOOLS",
    "get_all_assistant_tools",
    "get_all_privileged_tools",
    "get_caller_tools",
    "execute_tool",
    "resolve_smart_path",
    "perform_web_search",
    "decode_bing_url",
    "describe_tool_action",
    "format_live_tool_report",
    "extract_fallback_tool_calls",
]
