"""Interactive TUI menu for managing Model Context Protocol (MCP) server connections."""

import json
from pathlib import Path
import shlex
from typing import Any, Dict, List, Optional
import questionary
from rich.panel import Panel
from rich.table import Table

from locallm.config import LocaLLMConfig
from locallm.core.mcp.manager import (
    get_global_mcp_config_path,
    get_workspace_mcp_config_path,
    mcp_manager,
)
from locallm.core.mcp.models import MCPServerConfig
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette


def run_mcp_menu(config: LocaLLMConfig) -> None:
    """Main interactive menu loop for managing multi-server Model Context Protocol (MCP) connections."""
    active_ws = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    while True:
        configs = mcp_manager.load_configs(active_ws)
        statuses = mcp_manager.get_statuses(active_ws)
        status_map = {s.server_name: s for s in statuses}

        table = Table(
            title="Model Context Protocol (MCP) Multi-Server Pool",
            border_style=palette.border_style,
            header_style=f"bold {palette.primary}",
            box=palette.box_style,
        )
        table.add_column("Status", style="bold", width=12)
        table.add_column("Server Name", style=f"bold {palette.primary}")
        table.add_column("Transport", justify="center")
        table.add_column("Scope", justify="center")
        table.add_column("Target (Command / URL)")
        table.add_column("Tools", justify="center")
        table.add_column("Privileged", justify="center")

        if not configs:
            table.add_row(
                "[dim]NO SERVERS[/]",
                "[dim]None configured[/]",
                "-",
                "-",
                "[dim]Add a server via 'Add MCP Server' below[/]",
                "0",
                "-",
            )
        else:
            for name, cfg in sorted(configs.items()):
                st_info = status_map.get(name)
                if not cfg.enabled:
                    st_str = "[#aaaaaa]DISABLED[/]"
                elif st_info and st_info.is_connected:
                    st_str = f"[bold {palette.success}]CONNECTED[/]"
                else:
                    st_str = f"[bold {palette.primary}]IDLE[/]"

                target_str = ""
                if cfg.transport == "stdio":
                    args_preview = " ".join(cfg.args[:3])
                    target_str = f"{cfg.command or ''} {args_preview}".strip()
                    if len(target_str) > 40:
                        target_str = target_str[:37] + "..."
                elif cfg.transport == "sse":
                    target_str = cfg.url or ""

                tools_count = str(st_info.tools_count) if (st_info and st_info.is_connected) else "-"
                priv_str = "[bold yellow]YES[/]" if cfg.privileged else "[#aaaaaa]NO[/]"

                table.add_row(
                    st_str,
                    name,
                    cfg.transport.upper(),
                    f"[{cfg.scope}]",
                    target_str or "[dim]None[/]",
                    tools_count,
                    priv_str,
                )

        console.print()
        console.print(table)
        console.print(
            f"[dim]Active Workspace:[/] [bold cyan]{active_ws}[/] • "
            f"[dim]Total Servers:[/] [bold white]{len(configs)}[/] • "
            f"[dim]Global Config:[/] [dim]{get_global_mcp_config_path()}[/]\n"
        )

        choice = questionary.select(
            "MCP Server Actions:",
            choices=[
                "Test Server Connection & Tools",
                "Add MCP Server (stdio)",
                "Add MCP Server (SSE / HTTP)",
                "Toggle Enable / Disable Server",
                "Remove MCP Server",
                "Open Configuration in Editor",
                "View Configuration JSON",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Test Server Connection & Tools":
            _test_server_action(configs, active_ws)
        elif choice == "Add MCP Server (stdio)":
            _add_stdio_server_action(active_ws)
        elif choice == "Add MCP Server (SSE / HTTP)":
            _add_sse_server_action(active_ws)
        elif choice == "Toggle Enable / Disable Server":
            _toggle_server_action(configs, active_ws)
        elif choice == "Remove MCP Server":
            _remove_server_action(configs, active_ws)
        elif choice == "Open Configuration in Editor":
            _open_in_editor_action()
        elif choice == "View Configuration JSON":
            _view_config_action(active_ws)


def _test_server_action(configs: Dict[str, MCPServerConfig], active_ws: str) -> None:
    """Prompt user to choose a server and execute live diagnostic test."""
    if not configs:
        console.print("[yellow]No MCP servers configured yet.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    names = list(configs.keys())
    choice = questionary.select(
        "Select server to test:",
        choices=names + ["Cancel"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not choice or choice == "Cancel":
        return

    console.print(f"\n[dim cyan]Connecting and executing MCP handshake for '{choice}'...[/]")
    success, msg, tools = mcp_manager.test_server(choice, workspace_name=active_ws)

    if success:
        console.print(f"[bold green]✔[/] {msg}\n")
        if tools:
            tool_table = Table(
                title=f"Discovered Tools ({choice})",
                header_style="bold cyan",
            )
            tool_table.add_column("Function Name", style="bold white")
            tool_table.add_column("Description")
            tool_table.add_column("Parameters", justify="center")

            for t in tools:
                func = t.get("function", {})
                params = func.get("parameters", {}).get("properties", {})
                param_names = ", ".join(params.keys()) if params else "None"
                tool_table.add_row(
                    func.get("name", ""),
                    func.get("description", ""),
                    param_names,
                )
            console.print(tool_table)
    else:
        console.print(f"[bold red]✖[/] {msg}\n")

    console.print()
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _add_stdio_server_action(active_ws: str) -> None:
    """Interactive streamlined wizard to register a new stdio MCP server."""
    console.print("\n[bold cyan]Add Stdio MCP Server (Subprocess)[/]")
    console.print("[dim]Examples: <package_name> (if installed globally)[/]")
    console.print("[dim]          npx -y @modelcontextprotocol/server-filesystem D:\\Data[/]")
    console.print("[dim]          python -m mcp_server_sqlite --db-path mydb.sqlite[/]\n")

    cmd_line = questionary.text(
        "Executable command and arguments:",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not cmd_line or not cmd_line.strip():
        return

    parts = shlex.split(cmd_line.strip(), posix=False)
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    # Auto-derive default server name
    RUNNER_COMMANDS = {"npx", "python", "node", "uvx", "uv", "docker"}
    default_name = ""
    if command.lower() in RUNNER_COMMANDS and args:
        for tok in reversed(args):
            if not tok.startswith("-") and not tok.startswith("/"):
                base_tok = tok.split("/")[-1].replace("@", "")
                if base_tok:
                    default_name = base_tok
                    break
    if not default_name:
        default_name = command.lower().replace(".exe", "").replace(".cmd", "")

    # Quick confirm or advanced options
    advanced = questionary.confirm(
        f"Configure advanced settings (custom name '{default_name}', env vars, privilege gating)?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    clean_name = default_name
    env_dict: Dict[str, str] = {}
    is_privileged = False
    scope = "global"
    desc = ""

    if advanced:
        name_input = questionary.text(
            f"Server unique identifier (press Enter to keep '{default_name}'):",
            default=default_name,
            style=QUESTIONARY_STYLE,
        ).ask()
        if name_input and name_input.strip():
            clean_name = name_input.strip().lower()

        env_input = questionary.text(
            "Optional environment variables (KEY=VAL, comma-separated, or leave blank):",
            style=QUESTIONARY_STYLE,
        ).ask()
        if env_input and env_input.strip():
            for pair in env_input.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    env_dict[k.strip()] = v.strip()

        is_privileged = questionary.confirm(
            "Require administrative privilege for all tools from this server? (Recommended for filesystem/database)",
            default=False,
            style=QUESTIONARY_STYLE,
        ).ask()

        scope_choice = questionary.select(
            "Configuration scope:",
            choices=["Global (~/.locallm/mcp_servers.json)", f"Workspace ({active_ws})"],
            style=QUESTIONARY_STYLE,
        ).ask()
        scope = "workspace" if "Workspace" in (scope_choice or "") else "global"

        desc_input = questionary.text(
            "Optional description for this server:",
            style=QUESTIONARY_STYLE,
        ).ask()
        if desc_input:
            desc = desc_input.strip()

    new_cfg = MCPServerConfig(
        name=clean_name,
        transport="stdio",
        command=command,
        args=args,
        env=env_dict,
        enabled=True,
        privileged=bool(is_privileged),
        description=desc,
        scope=scope,
    )

    mcp_manager.save_config(new_cfg, workspace_name=active_ws)
    console.print(f"\n[bold green]✔ MCP Server '{clean_name}' saved successfully in {scope} scope.[/]")
    console.print(f"[dim]Command: {command} {' '.join(args)}[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _add_sse_server_action(active_ws: str) -> None:
    """Interactive wizard to register a remote SSE / HTTP MCP server."""
    console.print("\n[bold cyan]Add Remote SSE / HTTP MCP Server[/]")
    console.print("[dim]Example: http://127.0.0.1:8000/sse[/]\n")

    name = questionary.text(
        "Server unique identifier (e.g. 'remote_api', 'cloud_tools'):",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not name or not name.strip():
        return
    clean_name = name.strip().lower()

    url = questionary.text(
        "Server SSE Endpoint URL:",
        default="http://127.0.0.1:8000/sse",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not url or not url.strip():
        return

    is_privileged = questionary.confirm(
        "Require administrative privilege for this server?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    scope_choice = questionary.select(
        "Configuration scope:",
        choices=["Global (~/.locallm/mcp_servers.json)", f"Workspace ({active_ws})"],
        style=QUESTIONARY_STYLE,
    ).ask()
    scope = "workspace" if "Workspace" in (scope_choice or "") else "global"

    new_cfg = MCPServerConfig(
        name=clean_name,
        transport="sse",
        url=url.strip(),
        enabled=True,
        privileged=bool(is_privileged),
        scope=scope,
    )

    mcp_manager.save_config(new_cfg, workspace_name=active_ws)
    console.print(f"[bold green]✔ Remote MCP Server '{clean_name}' saved successfully.[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _toggle_server_action(configs: Dict[str, MCPServerConfig], active_ws: str) -> None:
    """Toggle enabled/disabled state of a server."""
    if not configs:
        console.print("[yellow]No MCP servers configured yet.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    names = list(configs.keys())
    choice = questionary.select(
        "Select server to toggle:",
        choices=names + ["Cancel"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not choice or choice == "Cancel":
        return

    cfg = configs[choice]
    cfg.enabled = not cfg.enabled
    mcp_manager.save_config(cfg, workspace_name=active_ws)
    new_state = "ENABLED" if cfg.enabled else "DISABLED"
    console.print(f"[bold green]✔ Server '{choice}' is now {new_state}.[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _remove_server_action(configs: Dict[str, MCPServerConfig], active_ws: str) -> None:
    """Prompt user to delete an MCP server configuration."""
    if not configs:
        console.print("[yellow]No MCP servers configured yet.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    names = list(configs.keys())
    choice = questionary.select(
        "Select server to delete:",
        choices=names + ["Cancel"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not choice or choice == "Cancel":
        return

    cfg = configs[choice]
    confirm = questionary.confirm(
        f"Permanently delete MCP server '{choice}' from {cfg.scope} configuration?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if confirm:
        mcp_manager.remove_config(choice, scope=cfg.scope, workspace_name=active_ws)
        console.print(f"[bold green]✔ Server '{choice}' deleted successfully.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _open_in_editor_action() -> None:
    """Open global mcp_servers.json configuration file in editor or default app."""
    import os
    import shutil
    import subprocess

    target = get_global_mcp_config_path()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"mcpServers": {}}, indent=2), encoding="utf-8")

    console.print(f"\n[dim cyan]Opening configuration file:[/] [bold white]{target}[/]")
    try:
        if shutil.which("code"):
            subprocess.run(["code", str(target)], check=False)
            console.print("[bold green]✔ Opened in VS Code.[/]\n")
        elif os.name == "nt":
            os.startfile(str(target))
            console.print("[bold green]✔ Opened with default system editor.[/]\n")
        else:
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(target)], check=False)
    except Exception as exc:
        console.print(f"[yellow]Could not open editor automatically: {exc}[/]")
        console.print(f"[dim]File path:[/] [bold white]{target}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _view_config_action(active_ws: str) -> None:
    """Display raw configuration JSON."""
    global_path = get_global_mcp_config_path()
    ws_path = get_workspace_mcp_config_path(active_ws)

    console.print(f"\n[bold cyan]Global Configuration ({global_path}):[/]")
    if global_path.is_file():
        console.print(global_path.read_text(encoding="utf-8"))
    else:
        console.print("[dim](Empty / Not created yet)[/]")

    if ws_path:
        console.print(f"\n[bold cyan]Workspace Configuration ({ws_path}):[/]")
        if ws_path.is_file():
            console.print(ws_path.read_text(encoding="utf-8"))
        else:
            console.print("[dim](Empty / Not created yet)[/]")

    console.print()
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


