"""Model management module supporting multiple local inference backends."""

from datetime import datetime
from typing import Any, Dict, List
import questionary
from rich.table import Table
from locallm.config import LocaLLMConfig, get_custom_platform, save_config
from locallm.core.hardware import check_vram_compatibility, get_gpu_info
from locallm.core.ollama_client import OllamaClient
from locallm.core.openai_client import OpenAIClient
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_models_manager(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Entry point for model management across backends."""
    while True:
        choices = ["Ollama"]
        for p in config.custom_platforms:
            choices.append(p.name)
        choices.extend(["Add Custom Platform", "Back"])

        choice = questionary.select(
            "Select Inference Platform:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Ollama":
            _manage_ollama_models(config, client)
        elif choice == "Add Custom Platform":
            from locallm.modules.service_manager import _add_custom_platform_wizard
            _add_custom_platform_wizard(config)
        else:
            _manage_custom_platform_models(config, choice)


def _manage_ollama_models(config: LocaLLMConfig, client: OllamaClient) -> None:
    """Ollama models browser, hardware sizing, and pull manager."""
    while True:
        if not client.is_connected():
            console.print(f"[danger]Ollama service is unreachable at[/] {config.ollama_host}")
            break

        models = client.list_models()
        _display_ollama_table(models, config.default_model, is_ollama_active=(config.active_backend == "ollama"))

        action = questionary.select(
            "Ollama Actions:",
            choices=[
                "Set Active Model",
                "Pull New Model",
                "Refresh List",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "Set Active Model":
            _select_active_model(models, config, platform_name="ollama")
        elif action == "Pull New Model":
            _pull_model_wizard(client)


def _display_ollama_table(models: List[Dict[str, Any]], active_model: str, is_ollama_active: bool = True) -> None:
    """Render Rich table of models with VRAM compatibility status."""
    gpu = get_gpu_info()
    table = Table(
        title="Installed Local Models (Ollama)",
        border_style="cyan",
        header_style="bold cyan",
    )
    table.add_column("Status", style="bold", width=8)
    table.add_column("Model Name", style="bold white")
    table.add_column("Size", justify="right")
    table.add_column("Family", justify="center")
    table.add_column("VRAM Compatibility")

    if not models:
        table.add_row("-", "No models found", "-", "-", "N/A")
        console.print(table)
        return

    for m in models:
        name = m.get("name", "unknown")
        size_bytes = m.get("size", 0)
        size_gb = size_bytes / (1024**3)
        details = m.get("details", {})
        family = details.get("family", "-")

        is_active = (
            "[bold green]ACTIVE[/]"
            if (name == active_model and is_ollama_active)
            else "[dim]INACTIVE[/]"
        )

        is_ok, status_msg = check_vram_compatibility(size_bytes)
        vram_display = (
            f"[green]{status_msg}[/]" if is_ok else f"[yellow]{status_msg}[/]"
        )

        table.add_row(
            is_active,
            name,
            f"{size_gb:.2f} GB",
            family,
            vram_display,
        )

    console.print()
    console.print(table)
    if gpu:
        console.print(
            f"[dim]Detected GPU: [bold white]{gpu.name}[/] | "
            f"VRAM: [bold green]{gpu.free_vram_mb / 1024:.1f} GB Free[/] / "
            f"[bold cyan]{gpu.total_vram_mb / 1024:.1f} GB Total[/][/]\n"
        )


def _manage_custom_platform_models(config: LocaLLMConfig, platform_name: str) -> None:
    """Manage models for an OpenAI-compatible custom platform."""
    platform = get_custom_platform(config, platform_name)
    if not platform:
        console.print(f"[warning]Platform '{platform_name}' not found.[/]\n")
        return

    openai_client = OpenAIClient(api_base=platform.api_base, api_key=platform.api_key)

    while True:
        if not openai_client.is_connected():
            console.print(f"\n[danger]Platform '{platform.name}' is unreachable at[/] {platform.api_base}")
            console.print("[#aaaaaa]Ensure the server daemon is running and reachable.[/]\n")
            action = questionary.select(
                f"{platform.name} Actions:",
                choices=["Refresh", "Back"],
                style=QUESTIONARY_STYLE,
            ).ask()
            if action == "Refresh":
                continue
            break

        models = openai_client.list_models()
        is_platform_active = (config.active_backend.strip().lower() == platform.name.strip().lower())

        table = Table(
            title=f"Available Models ({platform.name})",
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("Status", style="bold", width=8)
        table.add_column("Model ID", style="bold white")
        table.add_column("Owned By", justify="center")

        if not models:
            table.add_row("-", "No models returned by endpoint", "-")
        else:
            for m in models:
                m_id = m.get("id", "")
                is_active = (
                    "[bold green]ACTIVE[/]"
                    if (m_id == config.default_model and is_platform_active)
                    else "[dim]INACTIVE[/]"
                )
                table.add_row(
                    is_active,
                    m_id,
                    str(m.get("owned_by", "-")),
                )

        console.print()
        console.print(table)
        console.print(f"[#aaaaaa]Endpoint: [cyan]{platform.api_base}[/][/]\n")

        action = questionary.select(
            f"{platform.name} Model Actions:",
            choices=[
                "Set Active Model",
                "Refresh List",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "Set Active Model":
            _select_active_model(models, config, platform_name=platform.name)


def _select_active_model(
    models: List[Dict[str, Any]],
    config: LocaLLMConfig,
    platform_name: str = "ollama",
) -> None:
    """Prompt user to set default active model and optionally switch active platform."""
    if not models:
        console.print("[warning]No models available to select.[/]")
        return

    choices = [m.get("name") or m.get("id") for m in models]
    choices = [c for c in choices if c] + ["Cancel"]

    chosen = questionary.select(
        "Choose model to set as default:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if chosen and chosen != "Cancel":
        config.default_model = chosen
        if platform_name != "ollama":
            config.active_backend = platform_name
        save_config(config)
        console.print(f"[success]Default active model set to:[/] [bold cyan]{chosen}[/]")
        if platform_name != "ollama":
            console.print(f"[success]Active backend switched to:[/] [bold cyan]{platform_name}[/]\n")


def _pull_model_wizard(client: OllamaClient) -> None:
    """Pull model from Ollama library with status output."""
    model_name = questionary.text(
        "Enter model tag to pull (e.g. qwen2.5:7b, mistral, llama3.2):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not model_name or not model_name.strip():
        return

    model_name = model_name.strip()
    console.print(f"[bold cyan]Pulling model '{model_name}' from Ollama...[/]")

    try:
        last_status = ""
        for chunk in client.pull_model_stream(model_name):
            status = chunk.get("status", "")
            completed = chunk.get("completed", 0)
            total = chunk.get("total", 0)

            if total > 0:
                pct = (completed / total) * 100
                display_msg = f"{status}: {completed / (1024**2):.1f} MB / {total / (1024**2):.1f} MB ({pct:.1f}%)"
            else:
                display_msg = status

            if display_msg != last_status:
                console.print(f"[dim info]>[/] {display_msg}")
                last_status = display_msg

        console.print(f"[bold green]Successfully pulled '{model_name}'.[/]")
    except Exception as exc:
        console.print(f"[danger]Failed to pull model:[/] {exc}")
