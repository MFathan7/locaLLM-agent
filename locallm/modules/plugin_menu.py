"""Interactive TUI menu for managing locaLLM plugins."""

from pathlib import Path
import questionary
from rich.panel import Panel
from rich.table import Table

from locallm.config import LocaLLMConfig
from locallm.core.plugin_manager import (
    create_plugin_scaffold,
    delete_plugin,
    disable_plugin,
    enable_plugin,
    get_global_plugins_dir,
    get_plugin,
    list_plugins,
)
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_plugin_menu(config: LocaLLMConfig) -> None:
    """Main interactive menu loop for managing plugins."""
    active_ws = getattr(config, "active_workspace", "default")

    while True:
        plugins = list_plugins(active_ws)
        enabled_count = len([p for p in plugins if p.enabled and not p.error])
        total_count = len(plugins)

        table = Table(title="Installed Plugins", border_style="cyan", header_style="bold cyan")
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
                st = "[bold #00ff87]ENABLED[/]"
            else:
                st = "[#aaaaaa]DISABLED[/]"

            tools_desc = f"{len(p.tools)} tool(s)"
            table.add_row(
                st,
                p.name,
                p.version,
                tools_desc,
                f"[{p.source}]",
                (p.description[:50] + "...") if len(p.description) > 50 else (p.description or "[dim]No description[/]"),
            )

        console.print(table)
        console.print(f"[#aaaaaa]Total: [bold white]{total_count}[/] plugin(s) installed, [bold #00ff87]{enabled_count}[/] active.[/]\n")

        choices = [
            "Inspect Plugin Details",
            "Toggle Enable/Disable",
            "Create New Plugin Scaffold",
            "Delete Plugin",
            "Back",
        ]

        choice = questionary.select(
            "Plugin Options:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Inspect Plugin Details":
            _inspect_plugin_details(plugins)
        elif choice == "Toggle Enable/Disable":
            _toggle_plugin(plugins, active_ws)
        elif choice == "Create New Plugin Scaffold":
            _create_plugin_wizard()
        elif choice == "Delete Plugin":
            _delete_plugin_dialog(plugins, active_ws)


def _inspect_plugin_details(plugins) -> None:
    """Display detailed info and tool list for a selected plugin."""
    if not plugins:
        console.print("[warning]No plugins installed to inspect.[/]\n")
        return

    plugin_names = [p.name for p in plugins]
    chosen_name = questionary.select(
        "Select Plugin to Inspect:",
        choices=plugin_names + ["Back"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen_name or chosen_name == "Back":
        return

    target = next((p for p in plugins if p.name == chosen_name), None)
    if not target:
        return

    status_str = "[bold #00ff87]ENABLED[/]" if target.enabled else "[#aaaaaa]DISABLED[/]"
    info_lines = [
        f"Name        : [bold white]{target.name}[/]",
        f"Version     : {target.version}",
        f"Author      : {target.author}",
        f"Status      : {status_str}",
        f"Source      : {target.source}",
        f"Directory   : [cyan]{target.dir_path}[/]",
        f"Description : {target.description or 'None'}",
    ]
    if target.error:
        info_lines.append(f"Error       : [bold red]{target.error}[/]")

    console.print(Panel("\n".join(info_lines), title=f"Plugin: {target.name}", border_style="cyan"))

    if target.tools:
        tools_table = Table(title=f"Tools in '{target.name}'", border_style="cyan", header_style="bold cyan")
        tools_table.add_column("Tool Name", style="bold cyan")
        tools_table.add_column("Mutating", justify="center")
        tools_table.add_column("Description")

        for t in target.tools:
            fname = t.get("function", {}).get("name", "")
            fdesc = t.get("function", {}).get("description", "")
            is_mut = "[bold yellow]YES[/]" if fname in target.mutating_tools else "[dim]NO[/]"
            tools_table.add_row(fname, is_mut, fdesc)

        console.print(tools_table)
    else:
        console.print("[#aaaaaa]This plugin does not declare any tools.[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _toggle_plugin(plugins, workspace_name: str) -> None:
    """Toggle a plugin between enabled and disabled."""
    if not plugins:
        console.print("[warning]No plugins installed.[/]\n")
        return

    plugin_names = [
        f"{p.name} ({'ENABLED' if p.enabled else 'DISABLED'})"
        for p in plugins
    ]
    chosen = questionary.select(
        "Select Plugin to Toggle:",
        choices=plugin_names + ["Back"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Back":
        return

    raw_name = chosen.split(" (")[0].strip()
    target = next((p for p in plugins if p.name == raw_name), None)
    if not target:
        return

    if target.enabled:
        ok, msg = disable_plugin(target.name, workspace_name)
    else:
        ok, msg = enable_plugin(target.name, workspace_name)

    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")


def _create_plugin_wizard() -> None:
    """Interactive wizard to scaffold a new plugin."""
    name = questionary.text(
        "Enter new plugin name (e.g. 'postgres_tools', 'slack_notifier'):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not name or not name.strip():
        return

    desc = questionary.text(
        "Enter brief description:",
        default=f"Custom {name.strip()} integration for locaLLM",
        style=QUESTIONARY_STYLE,
    ).ask()

    location_choice = questionary.select(
        "Where should the plugin be created?",
        choices=[
            "Global Plugins (~/.locallm/plugins/)",
            "Local Project (./plugins/)",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not location_choice or location_choice == "Cancel":
        return

    if location_choice.startswith("Global"):
        target_dir = get_global_plugins_dir()
    else:
        target_dir = Path.cwd() / "plugins"

    ok, msg, path = create_plugin_scaffold(name, target_dir=target_dir, description=desc)
    if ok:
        console.print(f"[success]{msg}[/]")
        console.print(f"[#aaaaaa]Edit [bold cyan]{path / 'main.py'}[/] and [bold cyan]{path / 'plugin.json'}[/] to add your custom tools![/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")


def _delete_plugin_dialog(plugins, workspace_name: str) -> None:
    """Prompt user to select and permanently delete an installed plugin."""
    if not plugins:
        console.print("[warning]No plugins installed to delete.[/]\n")
        return

    plugin_names = [f"{p.name} [{p.source}]" for p in plugins]
    chosen = questionary.select(
        "Select Plugin to Permanently Delete:",
        choices=plugin_names + ["Back"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Back":
        return

    raw_name = chosen.split()[0]
    target = next((p for p in plugins if p.name == raw_name), None)
    if not target:
        return

    confirm = questionary.confirm(
        f"Are you sure you want to permanently delete plugin '{target.name}' ({target.source}) at '{target.dir_path}'?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not confirm:
        console.print("[dim]Plugin deletion cancelled.[/]\n")
        return

    ok, msg = delete_plugin(target.name, workspace_name)
    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
