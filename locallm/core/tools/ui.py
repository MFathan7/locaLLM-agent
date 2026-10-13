"""Terminal UI action description and live tool execution report formatters."""

from pathlib import Path
import re
from typing import Any, Dict, Optional


def describe_tool_action(name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Generate clean, human-friendly action text for terminal spinners and notifications."""
    args = arguments or {}
    if name == "create_directory":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is creating folder '{name_str or path}'..." if (name_str or path) else "locaLLM is creating folder..."

    elif name == "search_web":
        query_text = args.get("query", "").strip()
        short_q = (query_text[:35] + "...") if len(query_text) > 35 else query_text
        return f"locaLLM is searching the web for '{short_q}'..." if short_q else "locaLLM is searching the web..."

    elif name == "search_knowledge":
        query_text = args.get("query", "").strip()
        short_q = (query_text[:35] + "...") if len(query_text) > 35 else query_text
        return f"locaLLM is searching knowledge base for '{short_q}'..." if short_q else "locaLLM is searching knowledge base..."

    elif name == "index_knowledge":
        return "locaLLM is indexing workspace knowledge base..."

    elif name == "dispatch_agent_team":
        task_text = args.get("task", "").strip()
        short_t = (task_text[:35] + "...") if len(task_text) > 35 else task_text
        return f"locaLLM is deploying Multi-Agent Team for '{short_t}'..." if short_t else "locaLLM is deploying Multi-Agent Team..."

    elif name == "write_file":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is writing file '{name_str or path}'..." if (name_str or path) else "locaLLM is writing file..."

    elif name == "patch_file":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is patching '{name_str or path}'..." if (name_str or path) else "locaLLM is patching file..."

    elif name == "check_syntax":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is checking syntax of '{name_str or path}'..." if (name_str or path) else "locaLLM is checking syntax..."

    elif name == "list_directory":
        path = args.get("path", ".")
        name_str = Path(path).name if path not in (".", "") else "workspace"
        return f"locaLLM is inspecting folder '{name_str}'..."

    elif name == "read_file":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is reading '{name_str or path}'..." if (name_str or path) else "locaLLM is reading file..."

    elif name == "resolve_path":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is locating path '{name_str or path}'..." if (name_str or path) else "locaLLM is locating path..."

    elif name == "execute_command":
        cmd_raw = args.get("command") or args.get("cmd") or args.get("cli") or ""
        cmd = str(cmd_raw).strip()
        short_cmd = (cmd[:35] + "...") if len(cmd) > 35 else cmd
        return f"locaLLM is running command: {short_cmd}..." if short_cmd else "locaLLM is running system command..."

    elif name == "fetch_web":
        url = args.get("url", "").strip()
        clean_url = re.sub(r"^https?://(www\.)?", "", url)
        short_url = (clean_url[:35] + "...") if len(clean_url) > 35 else clean_url
        return f"locaLLM is fetching web content ({short_url})..." if short_url else "locaLLM is fetching web content..."

    elif name == "get_weather":
        loc = args.get("location", "")
        return f"locaLLM is checking weather for '{loc}'..." if loc else "locaLLM is checking weather..."

    elif name == "get_current_time":
        return "locaLLM is checking current time..."

    elif name == "get_current_directory":
        return "locaLLM is checking working directory..."

    elif name == "list_skills":
        return "locaLLM is discovering available skills..."

    elif name == "read_skill":
        sname = args.get("skill_name", "")
        return f"locaLLM is reading skill instructions for '{sname}'..." if sname else "locaLLM is reading skill..."

    elif name == "complete_task":
        return "locaLLM is concluding task and finalizing answer..."

    elif name.startswith("telegram_"):
        return f"locaLLM is dispatching Telegram action: {name}..."

    elif name.startswith("whatsapp_"):
        return f"locaLLM is dispatching WhatsApp action: {name}..."

    elif name.startswith("mcp__"):
        parts = name.split("__", 2)
        srv = parts[1] if len(parts) >= 2 else "mcp"
        tool_raw = parts[2] if len(parts) >= 3 else parts[-1]
        return f"locaLLM is executing [{srv}] {tool_raw}..."

    return f"locaLLM is executing {name}..."


def format_live_tool_report(name: str, arguments: Optional[Dict[str, Any]], observation: str) -> str:
    """Format a persistent real-time completion report line for display in terminal/logs."""
    from locallm.ui.theme import get_theme_palette

    palette = get_theme_palette()

    args = arguments or {}
    obs_lower = observation.lower()
    is_error = obs_lower.startswith("error") or "permission denied" in obs_lower or "failed" in obs_lower

    if is_error:
        clean_obs = observation.replace("[Permission Denied] ", "")
        return f"  [bold red]✖[/] [red]{name} failed:[/] [dim]{clean_obs}[/]"

    if name == "create_directory":
        path = args.get("path", "")
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Created directory:[/] [bold {palette.primary}]{path}[/]"

    elif name == "write_file":
        path = args.get("path", "")
        content = args.get("content", "")
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Written file:[/] [bold {palette.primary}]{path}[/] [dim]({len(content)} chars)[/]"

    elif name == "patch_file":
        path = args.get("path", "")
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Patched file:[/] [bold {palette.primary}]{path}[/]"

    elif name == "check_syntax":
        path = args.get("path", "")
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Syntax check:[/] [bold {palette.primary}]{path}[/]"

    elif name == "list_directory":
        path = args.get("path", ".")
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Inspected directory:[/] [bold {palette.primary}]{path}[/]"

    elif name == "read_file":
        path = args.get("path", "")
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Read file:[/] [bold {palette.primary}]{path}[/]"

    elif name == "resolve_path":
        path = args.get("path", "")
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Resolved path:[/] [bold {palette.primary}]{path}[/]"

    elif name == "execute_command":
        cmd_raw = args.get("command") or args.get("cmd") or args.get("cli") or ""
        cmd = str(cmd_raw).strip()
        short_cmd = (cmd[:40] + "...") if len(cmd) > 40 else cmd
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Executed:[/] [bold {palette.primary}]{short_cmd}[/]"

    elif name == "fetch_web":
        url = args.get("url", "").strip()
        clean_url = re.sub(r"^https?://(www\.)?", "", url)
        short_url = (clean_url[:40] + "...") if len(clean_url) > 40 else clean_url
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Fetched web:[/] [dim {palette.primary}]{short_url}[/]"

    elif name == "search_web":
        query_text = args.get("query", "").strip()
        short_q = (query_text[:40] + "...") if len(query_text) > 40 else query_text
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Searched web:[/] [bold {palette.primary}]{short_q}[/]"

    elif name == "search_knowledge":
        query_text = args.get("query", "").strip()
        short_q = (query_text[:40] + "...") if len(query_text) > 40 else query_text
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Knowledge search:[/] [bold {palette.primary}]{short_q}[/]"

    elif name == "index_knowledge":
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Indexed knowledge base[/]"

    elif name == "dispatch_agent_team":
        task_text = args.get("task", "").strip()
        short_t = (task_text[:40] + "...") if len(task_text) > 40 else task_text
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Multi-Agent Team completed:[/] [bold {palette.primary}]{short_t}[/]"

    elif name == "get_weather":
        loc = args.get("location", "")
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Weather ({loc}):[/] [dim white]{observation}[/]"

    elif name == "get_current_time":
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Checked time:[/] [dim white]{observation}[/]"

    elif name == "get_current_directory":
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Working directory:[/] [dim white]{observation}[/]"

    elif name == "list_skills":
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Discovered skills[/]"

    elif name == "read_skill":
        sname = args.get("skill_name", "")
        return f"  [bold {palette.primary}]✔[/] [{palette.primary}]Loaded skill:[/] [dim {palette.primary}]{sname}[/]"

    elif name == "complete_task":
        ans_preview = args.get("final_answer", "")
        if len(ans_preview) > 60:
            ans_preview = ans_preview[:60] + "..."
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Task completed:[/] [dim]{ans_preview}[/]"

    elif name.startswith("mcp__"):
        parts = name.split("__", 2)
        srv = parts[1] if len(parts) >= 2 else "mcp"
        tool_raw = parts[2] if len(parts) >= 3 else parts[-1]
        return f"  [bold {palette.success}]✔[/] [{palette.success}]Executed MCP [{srv}]:[/] [bold {palette.primary}]{tool_raw}[/]"

    return f"  [bold {palette.success}]✔[/] [{palette.success}]Executed:[/] [bold {palette.primary}]{name}[/]"
