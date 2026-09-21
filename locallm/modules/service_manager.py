"""Interactive TUI module for controlling local LLM platform services."""

import questionary
from rich.panel import Panel
from locallm.config import (
    CustomPlatformConfig,
    LocaLLMConfig,
    add_custom_platform,
    get_custom_platform,
    remove_custom_platform,
    save_config,
    switch_active_backend,
    update_custom_platform,
)
from locallm.core.service_manager import (
    is_custom_platform_reachable,
    is_ollama_installed,
    is_ollama_running,
    start_ollama_service,
    stop_ollama_service,
)
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_service_manager(config: LocaLLMConfig) -> None:
    """Platform selection menu for service management."""
    while True:
        choices = ["Ollama"]
        for p in config.custom_platforms:
            choices.append(p.name)
        choices.extend(["Add Custom Platform", "Back"])

        choice = questionary.select(
            "Service Platforms:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Ollama":
            _manage_ollama_platform(config)
        elif choice == "Add Custom Platform":
            _add_custom_platform_wizard(config)
        else:
            _manage_custom_platform(config, choice)


def _manage_ollama_platform(config: LocaLLMConfig) -> None:
    """Ollama service control and endpoint configuration."""
    while True:
        running = is_ollama_running(config.ollama_host)
        installed = is_ollama_installed()
        if running:
            status_text = "[bold green]RUNNING[/]"
        elif not installed:
            status_text = "[bold red]STOPPED (Not Installed in PATH)[/]"
        else:
            status_text = "[bold red]STOPPED[/]"
        is_active = (config.active_backend.strip().lower() == "ollama")
        active_text = "[bold green]ACTIVE BACKEND[/]" if is_active else "[dim]INACTIVE[/]"

        panel_content = (
            f"Service Status : {status_text}\n"
            f"Backend State  : {active_text}\n"
            f"API Endpoint   : [cyan]{config.ollama_host}[/]"
        )
        console.print(Panel(panel_content, title="Ollama Platform", border_style="cyan"))

        action = questionary.select(
            "Ollama Service Action:",
            choices=[
                "Set as Active Backend",
                "Start Server",
                "Stop Server",
                f"Configure Endpoint (Current: {config.ollama_host})",
                "Refresh Status",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "Set as Active Backend":
            ok, msg = switch_active_backend(config, "ollama")
            console.print(f"[success]{msg}[/]\n")
        elif action == "Start Server":
            ok, msg = start_ollama_service()
            _show_result(ok, msg)
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        elif action == "Stop Server":
            ok, msg = stop_ollama_service(config.ollama_host)
            _show_result(ok, msg)
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        elif action.startswith("Configure Endpoint"):
            _edit_ollama_endpoint(config)


def _manage_custom_platform(config: LocaLLMConfig, platform_name: str) -> None:
    """Manage a user-configured OpenAI-compatible custom platform."""
    while True:
        platform = get_custom_platform(config, platform_name)
        if not platform:
            console.print(f"[warning]Platform '{platform_name}' no longer exists.[/]\n")
            break

        reachable = is_custom_platform_reachable(platform.api_base, platform.api_key)
        status_text = "[bold green]ONLINE[/]" if reachable else "[bold red]OFFLINE[/]"
        is_active = (config.active_backend.strip().lower() == platform.name.strip().lower())
        active_text = "[bold green]ACTIVE BACKEND[/]" if is_active else "[dim]INACTIVE[/]"
        key_masked = "Configured" if platform.api_key else "None (Unauthenticated)"

        panel_content = (
            f"Platform Name  : [bold cyan]{platform.name}[/]\n"
            f"Service Status : {status_text}\n"
            f"Backend State  : {active_text}\n"
            f"API Endpoint   : [cyan]{platform.api_base}[/]\n"
            f"API Key        : [#aaaaaa]{key_masked}[/]"
        )
        console.print(Panel(panel_content, title=f"Platform: {platform.name}", border_style="cyan"))

        action = questionary.select(
            f"{platform.name} Service Action:",
            choices=[
                "Set as Active Backend",
                f"Configure Endpoint (Current: {platform.api_base})",
                f"Configure API Key (Current: {key_masked})",
                "Delete Platform",
                "Refresh Status",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "Set as Active Backend":
            ok, msg = switch_active_backend(config, platform.name)
            if ok:
                console.print(f"[success]{msg}[/]\n")
            else:
                console.print(f"[danger]{msg}[/]\n")
        elif action.startswith("Configure Endpoint"):
            new_url = questionary.text(
                "Enter OpenAI-compatible API base URL:",
                default=platform.api_base,
                style=QUESTIONARY_STYLE,
            ).ask()
            if new_url and new_url.strip():
                update_custom_platform(config, platform.name, api_base=new_url.strip())
                console.print(f"[success]Endpoint updated for '{platform.name}'.[/]\n")
        elif action.startswith("Configure API Key"):
            new_key = questionary.password(
                "Enter API Key (leave empty for none):",
                style=QUESTIONARY_STYLE,
            ).ask()
            if new_key is not None:
                update_custom_platform(config, platform.name, api_key=new_key.strip())
                console.print(f"[success]API Key updated for '{platform.name}'.[/]\n")
        elif action == "Delete Platform":
            confirm = questionary.confirm(
                f"Are you sure you want to delete custom platform '{platform.name}'?",
                default=False,
                style=QUESTIONARY_STYLE,
            ).ask()
            if confirm:
                ok, msg = remove_custom_platform(config, platform.name)
                if ok:
                    console.print(f"[success]{msg}[/]\n")
                else:
                    console.print(f"[danger]{msg}[/]\n")
                break


def _add_custom_platform_wizard(config: LocaLLMConfig) -> None:
    """Interactive wizard to register a new OpenAI-compatible platform."""
    console.print("\n[bold cyan]Add Custom Inference Platform (OpenAI-Compatible)[/]")
    console.print("[#aaaaaa]Connect any local or remote OpenAI-compatible server (vLLM, LocalAI, etc.)[/]\n")

    name = questionary.text(
        "Platform Name (e.g. vLLM, LocalAI, CustomAPI):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not name or not name.strip():
        console.print("[#aaaaaa]Addition cancelled.[/]\n")
        return

    name = name.strip()
    if name.lower() == "ollama":
        console.print(f"[danger]Error: Platform name '{name}' is reserved.[/]\n")
        return

    if get_custom_platform(config, name):
        console.print(f"[danger]Error: Platform '{name}' already exists.[/]\n")
        return

    endpoint = questionary.text(
        "API Base URL:",
        default="http://127.0.0.1:8000/v1",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not endpoint or not endpoint.strip():
        endpoint = "http://127.0.0.1:8000/v1"
    endpoint = endpoint.strip()

    api_key = questionary.password(
        "API Key (optional, press Enter to skip):",
        style=QUESTIONARY_STYLE,
    ).ask() or ""

    new_platform = CustomPlatformConfig(
        name=name,
        api_base=endpoint,
        api_key=api_key.strip(),
    )

    ok, msg = add_custom_platform(config, new_platform)
    if ok:
        console.print(f"[success]{msg}[/]")
        set_active = questionary.confirm(
            f"Set '{name}' as the active backend now?",
            default=True,
            style=QUESTIONARY_STYLE,
        ).ask()
        if set_active:
            ok_sw, msg_sw = switch_active_backend(config, name)
            console.print(f"[success]{msg_sw}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")


def _edit_ollama_endpoint(config: LocaLLMConfig) -> None:
    new_url = questionary.text(
        "Enter Ollama API Endpoint URL:",
        default=config.ollama_host,
        style=QUESTIONARY_STYLE,
    ).ask()
    if new_url and new_url.strip():
        config.ollama_host = new_url.strip()
        save_config(config)
        console.print("[success]Ollama endpoint updated.[/]\n")


def _show_result(success: bool, message: str) -> None:
    if success:
        console.print(f"[success][*] {message}[/]\n")
    else:
        console.print(f"[warning][!] {message}[/]\n")
