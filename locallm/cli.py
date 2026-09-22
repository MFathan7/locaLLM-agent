"""Command Line Interface entry point for locaLLM."""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from locallm.config import load_config
from locallm.core.ollama_client import OllamaClient
from locallm.core.openai_client import get_inference_client
from locallm.modules.agent import AgentEngine, run_agent_interactive
from locallm.modules.assistant import run_assistant
from locallm.modules.automation import execute_prompt
from locallm.modules.models_manager import run_models_manager
from locallm.modules.settings import run_settings
from locallm.modules.telegram_bot import run_telegram_bot
from locallm.modules.whatsapp_bot import run_whatsapp_bot
from locallm.ui.banner import render_banner
from locallm.ui.chat_view import print_conversational_cli_help
from locallm.ui.menu import start_main_menu
from locallm.ui.theme import console


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="locaLLM",
        description="Local LLM CLI & Interactive TUI Platform for Ollama",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Override active model for this execution",
    )
    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Override active workspace for this execution",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Override Ollama API endpoint URL",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Interactive Assistant
    subparsers.add_parser(
        "chat",
        help="Start interactive conversational assistant with built-in tools",
        description="Launch an interactive chat session with Ollama. Supports streaming Markdown, slash commands (/model, /clear, /stats, /system), and native function calling (time, directories, files, weather).",
    )

    # Telegram bot
    subparsers.add_parser(
        "telegram",
        help="Run Telegram bot integration daemon (24/7)",
        description="Connect and run your local model as a 24/7 Telegram bot. Automatically prompts for bot token if not yet configured.",
    )

    # WhatsApp bot
    wa_parser = subparsers.add_parser(
        "whatsapp",
        help="Run WhatsApp bot integration daemon (24/7)",
        description="Connect and run your local model as a WhatsApp bot. Features terminal QR pairing, number whitelist, and workspace session persistence.",
    )
    wa_parser.add_argument(
        "--script",
        "--show-script",
        action="store_true",
        help="Display the Node.js Baileys bridge script and manual execution guide",
    )

    # Agent
    agent_parser = subparsers.add_parser(
        "agent",
        help="Run autonomous agent loop with tools (file, shell, web)",
        description="Execute multi-step autonomous tasks using a ReAct reasoning loop. The model can plan, read/write files, fetch web content, and execute shell commands with security confirmation.",
    )
    agent_parser.add_argument("--task", "-t", type=str, default=None, help="Agent task instruction to run non-interactively")

    # One-shot run
    run_parser = subparsers.add_parser(
        "run",
        help="Execute single prompt and stream response to console",
        description="Execute a one-shot query against the active local model and stream the result directly to stdout. Ideal for quick scripting, automation, or piping.",
    )
    run_parser.add_argument("prompt", type=str, help="Prompt text to run")

    # Models manager
    subparsers.add_parser(
        "models",
        help="Inspect, manage, and pull local inference models",
        description="View installed local models, inspect parameter sizes, check GPU VRAM compatibility (precision architecture-aware GQA & SWA formula), switch active default, and manage models.",
    )

    # Settings
    subparsers.add_parser(
        "config",
        help="View or modify application settings",
        description="Open settings menu to configure active backend, temperature, system prompt, Telegram token, and agent permissions.",
    )

    # Status
    subparsers.add_parser(
        "status",
        help="Display connection, hardware, and model diagnostics",
        description="Check backend service connectivity (Ollama / LM Studio), active model, detected features (Tools, Vision, Reasoning), and NVIDIA GPU VRAM metrics.",
    )

    # Service manager commands
    svc_parser = subparsers.add_parser(
        "service",
        help="Manage local backend services (start, stop, status)",
        description="Control background inference services without automatic launches. Check status or control services.",
    )
    svc_parser.add_argument("action", choices=["start", "stop", "status"], help="Action to perform: start, stop, or status")
    svc_parser.add_argument("target", nargs="?", default="ollama", help="Target inference service or platform (default: ollama)")

    start_parser = subparsers.add_parser(
        "start",
        help="Start local LLM service in background (default: ollama)",
        description="Start local inference service process explicitly in the background upon command.",
    )
    start_parser.add_argument("target", nargs="?", default="ollama", help="Service to start (default: ollama)")

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop local LLM service process (default: ollama)",
        description="Stop active inference service processes cleanly.",
    )
    stop_parser.add_argument("target", nargs="?", default="ollama", help="Service to stop (default: ollama)")

    # Platform manager
    plat_parser = subparsers.add_parser(
        "platform",
        help="Manage custom OpenAI-compatible platforms (list, add, remove, use)",
        description="Inspect, list, register, remove, or switch custom OpenAI-compatible inference platforms.",
    )
    plat_sub = plat_parser.add_subparsers(dest="plat_action", help="Platform actions")
    plat_sub.add_parser("list", help="List all registered platforms")
    plat_use = plat_sub.add_parser("use", help="Switch active platform")
    plat_use.add_argument("name", type=str, help="Platform name to activate")
    plat_add = plat_sub.add_parser("add", help="Register a new custom platform")
    plat_add.add_argument("name", type=str, help="Platform name")
    plat_add.add_argument("--endpoint", "-e", type=str, default="http://127.0.0.1:8000/v1", help="API base URL")
    plat_add.add_argument("--key", "-k", type=str, default="", help="Optional API key")
    plat_remove = plat_sub.add_parser("remove", help="Remove a custom platform")
    plat_remove.add_argument("name", type=str, help="Platform name to remove")

    # Workspace manager
    ws_parser = subparsers.add_parser(
        "workspace",
        help="Manage isolated workspaces, knowledge, and skills",
        description="Inspect, list, create, switch, or delete isolated workspaces with custom knowledge and skills.",
    )
    ws_sub = ws_parser.add_subparsers(dest="ws_action", help="Workspace actions")
    ws_sub.add_parser("list", help="List all available workspaces")
    ws_use = ws_sub.add_parser("use", help="Switch active workspace")
    ws_use.add_argument("name", type=str, help="Workspace name to activate")
    ws_create = ws_sub.add_parser("create", help="Create a new isolated workspace")
    ws_create.add_argument("name", type=str, help="Name of new workspace")
    ws_create.add_argument("--desc", "-d", type=str, default="", help="Optional description")
    ws_delete = ws_sub.add_parser("delete", help="Delete a custom workspace")
    ws_delete.add_argument("name", type=str, help="Name of workspace to delete")

    # Workspace instructions
    ws_instruct = ws_sub.add_parser("instruct", help="Set or update custom instructions for a workspace")
    ws_instruct.add_argument("instructions", type=str, help="Custom instructions text")
    ws_instruct.add_argument("--workspace", "-w", type=str, default=None, help="Target workspace (defaults to active workspace)")

    # Add knowledge document
    ws_add_k = ws_sub.add_parser("add-knowledge", help="Add markdown or text knowledge document to workspace")
    ws_add_k.add_argument("title", type=str, help="Document title or filename (e.g. faq.md)")
    ws_add_k.add_argument("--content", "-c", type=str, default=None, help="Document content string")
    ws_add_k.add_argument("--file", "-f", type=str, default=None, help="Local file path to read content from")
    ws_add_k.add_argument("--workspace", "-w", type=str, default=None, help="Target workspace (defaults to active workspace)")

    # Add skill manually
    ws_add_s = ws_sub.add_parser("add-skill", help="Add manual skill markdown or text to workspace")
    ws_add_s.add_argument("title", type=str, help="Skill name or filename")
    ws_add_s.add_argument("--content", "-c", type=str, default=None, help="Skill instructions content string")
    ws_add_s.add_argument("--file", "-f", type=str, default=None, help="Local file path to read content from")
    ws_add_s.add_argument("--workspace", "-w", type=str, default=None, help="Target workspace (defaults to active workspace)")

    # Install skill from GitHub or URL
    ws_install = ws_sub.add_parser("install", help="Install agent skill from GitHub repo or URL into workspace")
    ws_install.add_argument("source", type=str, help="GitHub repo (owner/repo), URL, or subpath")
    ws_install.add_argument("--skill", "-s", type=str, action="append", default=None, help="Specific skill name(s) to install (can be specified multiple times)")
    ws_install.add_argument("--workspace", "-w", type=str, default=None, help="Target workspace (defaults to active workspace)")

    # Plugin manager
    plug_parser = subparsers.add_parser(
        "plugin",
        help="Manage customizable modular plugins and tools",
        description="Inspect, list, enable, disable, or scaffold customizable modular plugins and tools.",
    )
    plug_sub = plug_parser.add_subparsers(dest="plug_action", help="Plugin actions")
    plug_sub.add_parser("list", help="List all installed plugins and their tools")
    plug_enable = plug_sub.add_parser("enable", help="Enable a plugin")
    plug_enable.add_argument("name", type=str, help="Plugin name to enable")
    plug_disable = plug_sub.add_parser("disable", help="Disable a plugin")
    plug_disable.add_argument("name", type=str, help="Plugin name to disable")
    plug_create = plug_sub.add_parser("create", help="Create a new starter plugin scaffold")
    plug_create.add_argument("name", type=str, help="Plugin name")
    plug_create.add_argument("--desc", "-d", type=str, default="", help="Optional description")
    plug_del = plug_sub.add_parser("delete", help="Permanently delete an installed plugin")
    plug_del.add_argument("name", type=str, help="Plugin name to delete")
    plug_del.add_argument("--yes", "-y", action="store_true", help="Confirm deletion without prompting")
    plug_rm = plug_sub.add_parser("remove", help="Permanently delete an installed plugin (alias for delete)")
    plug_rm.add_argument("name", type=str, help="Plugin name to remove")
    plug_rm.add_argument("--yes", "-y", action="store_true", help="Confirm deletion without prompting")

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Main CLI execution router."""
    KNOWN_SUBCOMMANDS = {
        "chat", "telegram", "whatsapp", "agent", "run", "models", "config",
        "status", "service", "start", "stop", "workspace", "platform", "plugin",
    }

    if argv is None:
        argv = list(sys.argv[1:])

    # Conversational help interceptor for top-level help requests
    if argv and len(argv) == 1 and argv[0].lower() in ("--help", "-h", "help"):
        print_conversational_cli_help()
        return

    # Normalize help requests for subcommands: e.g. "locallm --help service" or "locallm help service"
    if argv:
        if argv[0].lower() == "help":
            if len(argv) > 1 and argv[1].lower() in KNOWN_SUBCOMMANDS:
                argv = [argv[1].lower(), "--help"]
            else:
                argv = ["--help"]
        elif argv[0] in ("--help", "-h") and len(argv) > 1:
            for arg in argv[1:]:
                if arg.lower() in KNOWN_SUBCOMMANDS:
                    argv = [arg.lower(), "--help"]
                    break

    parser = build_parser()
    args = parser.parse_args(argv)

    config = load_config()

    if getattr(args, "host", None):
        config.ollama_host = args.host
    if getattr(args, "model", None):
        config.default_model = args.model
    if getattr(args, "workspace", None):
        config.active_workspace = args.workspace

    client = get_inference_client(config)

    # Automatically unload models from VRAM whenever locaLLM session terminates
    import atexit

    def _auto_unload_on_exit() -> None:
        try:
            client.unload_all_models(fallback_model=config.default_model)
        except Exception:
            pass

    atexit.register(_auto_unload_on_exit)

    if not args.command:
        # No subcommand passed: open interactive TUI menu
        start_main_menu(config, client)
        return

    cmd = args.command.lower()
    if cmd == "chat":
        render_banner(config, client)
        run_assistant(config, client)
    elif cmd == "telegram":
        render_banner(config, client)
        run_telegram_bot(config, client)
    elif cmd == "whatsapp":
        render_banner(config, client)
        if getattr(args, "script", False):
            from locallm.modules.whatsapp_bot import _display_bridge_script
            _display_bridge_script()
        else:
            run_whatsapp_bot(config, client)
    elif cmd == "agent":
        render_banner(config, client)
        if args.task:
            engine = AgentEngine(config, client)
            engine.run_task(args.task)
        else:
            run_agent_interactive(config, client)
    elif cmd == "run":
        execute_prompt(args.prompt, config, client)
    elif cmd == "models":
        run_models_manager(config, client)
    elif cmd == "config":
        run_settings(config)
    elif cmd == "workspace":
        _handle_workspace_cli(args, config)
    elif cmd == "platform":
        _handle_platform_cli(args, config)
    elif cmd == "plugin":
        _handle_plugin_cli(args, config)
    elif cmd == "status":
        render_banner(config, client)
    elif cmd == "start":
        _handle_service_cli("start", args.target, config)
    elif cmd == "stop":
        _handle_service_cli("stop", args.target, config)
    elif cmd == "service":
        _handle_service_cli(args.action, args.target, config)
    else:
        parser.print_help()


def _handle_plugin_cli(args, config) -> None:
    """Execute plugin management commands from CLI."""
    from rich.table import Table
    from locallm.core.plugin_manager import (
        create_plugin_scaffold,
        delete_plugin,
        disable_plugin,
        enable_plugin,
        list_plugins,
    )

    action = getattr(args, "plug_action", None) or "list"
    active_ws = getattr(config, "active_workspace", "default")

    if action == "list":
        plugins = list_plugins(active_ws)
        table = Table(title="Installed locaLLM Plugins", border_style="cyan", header_style="bold cyan")
        table.add_column("Status", style="bold", width=10)
        table.add_column("Plugin Name", style="bold white")
        table.add_column("Version", justify="center")
        table.add_column("Tools", justify="center")
        table.add_column("Source", justify="center")
        table.add_column("Description")

        for p in plugins:
            if p.error:
                st = "[bold red]ERROR[/]"
            elif p.enabled:
                st = "[bold green]ENABLED[/]"
            else:
                st = "[dim]DISABLED[/]"
            table.add_row(
                st,
                p.name,
                p.version,
                f"{len(p.tools)} tool(s)",
                f"[{p.source}]",
                p.description or "[dim]No description[/]",
            )
        console.print(table)
        return

    if action == "enable":
        ok, msg = enable_plugin(args.name, active_ws)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "disable":
        ok, msg = disable_plugin(args.name, active_ws)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "create":
        ok, msg, path = create_plugin_scaffold(args.name, description=args.desc)
        if ok and path:
            console.print(f"[success]{msg}[/]")
            console.print(f"[#aaaaaa]Created entrypoint at: [bold cyan]{path / 'main.py'}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action in ("delete", "remove"):
        if not getattr(args, "yes", False):
            import questionary
            from locallm.ui.theme import QUESTIONARY_STYLE
            confirm = questionary.confirm(
                f"Are you sure you want to permanently delete plugin '{args.name}'?",
                default=False,
                style=QUESTIONARY_STYLE,
            ).ask()
            if not confirm:
                console.print("[dim]Plugin deletion cancelled.[/]")
                return
        ok, msg = delete_plugin(args.name, active_ws)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")


def _handle_workspace_cli(args, config) -> None:
    """Execute workspace commands from CLI."""
    from rich.table import Table
    from locallm.config import save_config
    from locallm.core.workspace import (
        add_workspace_document,
        add_workspace_skill,
        create_workspace,
        delete_workspace,
        install_skill_from_source,
        list_workspaces,
        update_workspace_instructions,
    )

    action = getattr(args, "ws_action", None) or "list"
    ws_target = getattr(args, "workspace", None) or getattr(config, "active_workspace", "default")

    if action == "list":
        workspaces = list_workspaces()
        active = getattr(config, "active_workspace", "default")
        table = Table(title="Installed Workspaces", border_style="cyan", header_style="bold cyan")
        table.add_column("Status", style="bold", width=8)
        table.add_column("Workspace Name", style="bold white")
        table.add_column("Knowledge", justify="center")
        table.add_column("Skills", justify="center")
        table.add_column("Description")
        for ws in workspaces:
            name = ws["name"]
            st = "[bold green]ACTIVE[/]" if name == active else "[dim]INACTIVE[/]"
            desc = ws["description"] or "[dim]No description[/]"
            table.add_row(st, name, f"{ws['knowledge_count']} file(s)", f"{ws['skills_count']} file(s)", desc)
        console.print(table)
        return

    if action == "use":
        target = args.name.strip().lower()
        workspaces = [ws["name"] for ws in list_workspaces()]
        if target not in workspaces:
            console.print(f"[danger]Workspace '{target}' does not exist.[/]")
            return
        config.active_workspace = target
        save_config(config)
        console.print(f"[success]Active workspace switched to:[/] [bold cyan]{target}[/]")

    elif action == "create":
        ok, msg = create_workspace(args.name, description=args.desc)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "delete":
        active = getattr(config, "active_workspace", "default")
        ok, msg = delete_workspace(args.name, active)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "instruct":
        ok, msg = update_workspace_instructions(ws_target, args.instructions)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "add-knowledge":
        content = args.content
        if not content and args.file:
            try:
                content = Path(args.file).read_text(encoding="utf-8")
            except Exception as exc:
                console.print(f"[danger]Failed to read file '{args.file}': {exc}[/]")
                return
        if not content:
            console.print("[danger]Error: Must provide --content <text> or --file <path>.[/]")
            return
        ok, msg = add_workspace_document(ws_target, args.title, content)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "add-skill":
        content = args.content
        if not content and args.file:
            try:
                content = Path(args.file).read_text(encoding="utf-8")
            except Exception as exc:
                console.print(f"[danger]Failed to read file '{args.file}': {exc}[/]")
                return
        if not content:
            console.print("[danger]Error: Must provide --content <text> or --file <path>.[/]")
            return
        ok, msg = add_workspace_skill(ws_target, args.title, content)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "install":
        selected = args.skill
        console.print(f"[bold cyan]Inspecting and installing skill from:[/] [#bbbbbb]{args.source}[/]")
        ok, msg, installed = install_skill_from_source(ws_target, args.source, selected_skills=selected)
        if ok:
            console.print(f"[success]{msg}[/]")
            if installed:
                console.print(f"[#aaaaaa]Installed skills:[/] [bold green]{', '.join(installed)}[/]")
        else:
            console.print(f"[danger]{msg}[/]")


def _handle_service_cli(action: str, target: str, config) -> None:
    """Execute service start/stop actions from CLI."""
    from locallm.core.service_manager import (
        get_all_services_status,
        start_ollama_service,
        stop_ollama_service,
    )

    if action == "status":
        statuses = get_all_services_status(config.ollama_host, config.custom_platforms)
        for name, running in statuses.items():
            st = "[bold green]ONLINE[/]" if running else "[bold red]OFFLINE[/]"
            console.print(f"{name}: {st}")
        return

    if action == "start":
        if target in ("ollama", "all"):
            ok, msg = start_ollama_service()
            console.print(f"[bold cyan][Ollama][/] {msg}")
        else:
            console.print(f"[#aaaaaa]Service '{target}' is an external or custom platform. Start it via its daemon executable or container.[/]")

    elif action == "stop":
        if target in ("ollama", "all"):
            ok, msg = stop_ollama_service(config.ollama_host)
            console.print(f"[bold cyan][Ollama][/] {msg}")
        else:
            console.print(f"[#aaaaaa]Service '{target}' is an external or custom platform. Stop it via its daemon process or container.[/]")


def _handle_platform_cli(args, config) -> None:
    """Execute custom platform commands from CLI."""
    from rich.table import Table
    from locallm.config import (
        CustomPlatformConfig,
        add_custom_platform,
        get_custom_platform,
        remove_custom_platform,
        save_config,
        switch_active_backend,
    )
    from locallm.core.service_manager import is_custom_platform_reachable, is_ollama_running

    action = getattr(args, "plat_action", None)
    if not action or action == "list":
        table = Table(title="Inference Platforms", border_style="cyan", header_style="bold cyan")
        table.add_column("Status", style="bold", width=8)
        table.add_column("Platform", style="bold white")
        table.add_column("Type", justify="center")
        table.add_column("Endpoint", style="cyan")
        table.add_column("State", justify="center")

        ollama_active = "[bold green]ACTIVE[/]" if config.active_backend == "ollama" else "[dim]INACTIVE[/]"
        ollama_up = "[bold green]ONLINE[/]" if is_ollama_running(config.ollama_host) else "[bold red]OFFLINE[/]"
        table.add_row(ollama_active, "Ollama", "Native Ollama", config.ollama_host, ollama_up)

        for p in config.custom_platforms:
            is_active = "[bold green]ACTIVE[/]" if config.active_backend.lower() == p.name.lower() else "[dim]INACTIVE[/]"
            is_up = "[bold green]ONLINE[/]" if is_custom_platform_reachable(p.api_base, p.api_key) else "[bold red]OFFLINE[/]"
            table.add_row(is_active, p.name, "OpenAI-Compatible", p.api_base, is_up)

        console.print(table)

    elif action == "add":
        new_plat = CustomPlatformConfig(
            name=args.name.strip(),
            api_base=args.endpoint.strip(),
            api_key=args.key.strip() if args.key else "",
        )
        ok, msg = add_custom_platform(config, new_plat)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "remove":
        ok, msg = remove_custom_platform(config, args.name.strip())
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")

    elif action == "use":
        target = args.name.strip()
        ok, msg = switch_active_backend(config, target)
        if ok:
            console.print(f"[success]{msg}[/]")
        else:
            console.print(f"[danger]{msg}[/]")


if __name__ == "__main__":
    main()
