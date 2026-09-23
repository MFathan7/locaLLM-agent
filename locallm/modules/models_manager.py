"""Model management module supporting multiple local inference backends."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import questionary
from rich.live import Live
from rich.table import Table
from locallm.config import LocaLLMConfig, get_custom_platform, save_config
from locallm.core.hardware import calculate_vram_breakdown, check_vram_compatibility, get_gpu_info
from locallm.core.ollama_client import OllamaClient
from locallm.core.openai_client import OpenAIClient
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette


def run_models_manager(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
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


def _manage_ollama_models(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
    """Ollama models browser, hardware sizing, and pull manager."""
    ollama_client = OllamaClient(base_url=config.ollama_host)
    while True:
        if not ollama_client.is_connected():
            console.print(f"[danger]Ollama service is unreachable at[/] {config.ollama_host}")
            break

        models = ollama_client.list_models()
        is_ollama_active = (config.active_backend.strip().lower() == "ollama")
        _display_ollama_table(
            models,
            config.default_model,
            is_ollama_active=is_ollama_active,
            client=ollama_client,
            context_tokens=config.context_window,
            ui_theme=config.ui_theme,
        )

        action = questionary.select(
            "Ollama Actions:",
            choices=[
                "Set Active Model",
                "Pull New Model",
                "Delete Model",
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
            _pull_model_wizard(ollama_client)
        elif action == "Delete Model":
            _delete_model_wizard(ollama_client, config, platform_name="ollama")


def _display_ollama_table(
    models: List[Dict[str, Any]],
    active_model: str,
    is_ollama_active: bool = True,
    client: Optional[OllamaClient] = None,
    context_tokens: int = 8192,
    ui_theme: str = "cyber_neon",
) -> None:
    """Render Rich table of models with precision VRAM compatibility status."""
    gpu = get_gpu_info()
    palette = get_theme_palette(ui_theme)
    table = Table(
        title="Installed Local Models (Ollama)",
        border_style=palette.border_style,
        header_style=f"bold {palette.primary}",
        box=palette.box_style,
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

        arch: Dict[str, Any] = {}
        if client and hasattr(client, "get_model_architecture_info"):
            arch = client.get_model_architecture_info(name)

        res = calculate_vram_breakdown(
            model_size_bytes=size_bytes,
            context_tokens=context_tokens,
            layers=arch.get("layers"),
            kv_heads=arch.get("kv_heads"),
            head_dim=arch.get("head_dim"),
            sliding_window=arch.get("sliding_window"),
            swa_pattern=arch.get("swa_pattern"),
            head_dim_swa=arch.get("head_dim_swa"),
        )

        if not gpu:
            vram_display = f"[#aaaaaa]CPU Mode (~{res.total_vram_gb:.1f} GB RAM)[/]"
        elif res.is_fit:
            max_k = (
                f"~{res.max_context_tokens // 1000}k ctx"
                if res.max_context_tokens >= 1000
                else f"{res.max_context_tokens} ctx"
            )
            vram_display = (
                f"[bold #00ff87]100% GPU[/] [#00ff87](+{res.headroom_gb:.1f} GB Free, max {max_k})[/]"
            )
        else:
            vram_display = (
                f"[bold red]SPILLOVER[/] [red](Need {res.total_vram_gb:.1f} GB > {res.usable_vram_gb:.1f} GB)[/]"
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
            f"[#aaaaaa]Detected GPU: [bold white]{gpu.name}[/] | "
            f"VRAM: [bold #00ff87]{gpu.free_vram_mb / 1024:.1f} GB Free[/] / "
            f"[bold #00d7ff]{gpu.total_vram_mb / 1024:.1f} GB Total[/] | "
            f"Active Context: [bold #00d7ff]{context_tokens:,}[/] tokens[/]\n"
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

        palette = get_theme_palette(config.ui_theme)
        table = Table(
            title=f"Available Models ({platform.name})",
            border_style=palette.border_style,
            header_style=f"bold {palette.primary}",
            box=palette.box_style,
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
        console.print(f"[#aaaaaa]Endpoint: [{palette.dim}]{platform.api_base}[/][/]\n")

        action = questionary.select(
            f"{platform.name} Model Actions:",
            choices=[
                "Set Active Model",
                "Delete Model",
                "Refresh List",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if action is None or action == "Back":
            break

        if action == "Set Active Model":
            _select_active_model(models, config, platform_name=platform.name)
        elif action == "Delete Model":
            _delete_model_wizard(openai_client, config, platform_name=platform.name)


def _select_active_model(
    models: List[Dict[str, Any]],
    config: LocaLLMConfig,
    platform_name: str = "ollama",
) -> None:
    """Prompt user to set default active model and optionally switch active platform."""
    if not models:
        console.print("[warning]No models available to select.[/]")
        return

    model_names = [m.get("name") or m.get("id") for m in models]
    model_names = [c for c in model_names if c]
    choices = ["Auto (Smart Router)"] + model_names + ["Cancel"]

    chosen = questionary.select(
        "Choose model to set as default:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if chosen and chosen != "Cancel":
        palette = get_theme_palette(config.ui_theme)
        if chosen == "Auto (Smart Router)":
            config.default_model = "auto"
            if platform_name.lower() == "ollama":
                config.ollama_model = "auto"
                config.active_backend = "ollama"
            else:
                platform = get_custom_platform(config, platform_name)
                if platform:
                    platform.default_model = "auto"
                config.active_backend = platform_name
            save_config(config)
            console.print(f"[success]Default active model set to:[/] [bold {palette.primary}]Auto (Smart Router)[/]\n")
            return

        config.default_model = chosen
        if platform_name.lower() == "ollama":
            config.ollama_model = chosen
            config.active_backend = "ollama"
        else:
            platform = get_custom_platform(config, platform_name)
            if platform:
                platform.default_model = chosen
            config.active_backend = platform_name
        save_config(config)
        console.print(f"[success]Default active model set to:[/] [bold {palette.primary}]{chosen}[/]")
        if platform_name.lower() != "ollama":
            console.print(f"[success]Active backend switched to:[/] [bold {palette.primary}]{platform_name}[/]\n")


def _pull_model_wizard(client: OllamaClient) -> None:
    """Pull model from Ollama library with dynamic single-line progress output."""
    model_name = questionary.text(
        "Enter model tag to pull (e.g. qwen2.5:7b, mistral, llama3.2):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not model_name or not model_name.strip():
        return

    model_name = model_name.strip()
    console.print(f"\n[bold cyan]Initiating pull for model '{model_name}'...[/]")

    try:
        full_bar = "━" * 20
        with Live(console=console, refresh_per_second=12, transient=False) as live:
            for chunk in client.pull_model_stream(model_name):
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])

                status = chunk.get("status", "")
                completed = chunk.get("completed", 0)
                total = chunk.get("total", 0)

                if status == "success":
                    line = f"[bold cyan]Pulling {model_name}:[/] [#00ff87]Complete[/] [bold green]{full_bar}[/] [bold green](100.0%)[/]"
                elif total > 0:
                    pct = (completed / total) * 100
                    if total >= 1024**3:
                        size_str = f"{completed / (1024**3):.2f} GB / {total / (1024**3):.2f} GB"
                    else:
                        size_str = f"{completed / (1024**2):.1f} MB / {total / (1024**2):.1f} MB"

                    bar_len = 20
                    filled = int(bar_len * completed // total)
                    bar = "━" * filled + ("╸" if filled < bar_len else "")
                    bar = bar.ljust(bar_len, "─")

                    line = f"[bold cyan]Pulling {model_name}:[/] [#00d7ff]{status}[/] [bold green]{bar}[/] [#00ff87]{size_str}[/] ([bold cyan]{pct:.1f}%[/])"
                else:
                    line = f"[bold cyan]Pulling {model_name}:[/] [#bbbbbb]{status}[/]"

                live.update(line)

        console.print()
        console.print(f"[bold green]Successfully pulled model '{model_name}'.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
    except Exception as exc:
        console.print()
        console.print(f"[danger]Failed to pull model '{model_name}':[/] {exc}\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _handle_deleted_model_fallback(
    config: LocaLLMConfig,
    platform_name: str,
    deleted_model: str,
    remaining_models: List[Dict[str, Any]],
) -> None:
    """Safely fallback and re-sync active model if the deleted model was active."""
    remaining_names = [
        m.get("name") or m.get("id")
        for m in remaining_models
        if m.get("name") or m.get("id")
    ]
    remaining_names = [n for n in remaining_names if n != deleted_model]
    fallback_model = remaining_names[0] if remaining_names else ""

    is_ollama = platform_name.strip().lower() == "ollama"
    config_changed = False

    if is_ollama:
        if config.ollama_model == deleted_model:
            config.ollama_model = fallback_model or "gemma4:12b"
            config_changed = True
            console.print(f"[dim]Ollama default model set to:[/] [bold cyan]{config.ollama_model}[/]")
        if config.active_backend.strip().lower() == "ollama" and config.default_model == deleted_model:
            config.default_model = config.ollama_model
            config_changed = True
            console.print(f"[dim]Active session model set to:[/] [bold cyan]{config.default_model}[/]")
    else:
        platform = get_custom_platform(config, platform_name)
        if platform:
            if platform.default_model == deleted_model:
                platform.default_model = fallback_model
                config_changed = True
                console.print(f"[dim]{platform_name} default model set to:[/] [bold cyan]{platform.default_model or 'None'}[/]")
            if config.active_backend.strip().lower() == platform_name.strip().lower() and config.default_model == deleted_model:
                config.default_model = platform.default_model or fallback_model
                config_changed = True
                console.print(f"[dim]Active session model set to:[/] [bold cyan]{config.default_model or 'None'}[/]")

    if config_changed:
        save_config(config)


def _delete_model_wizard(
    client: Any,
    config: LocaLLMConfig,
    platform_name: str = "ollama",
) -> None:
    """General wizard to safely delete a model across any supported inference platform."""
    if not hasattr(client, "list_models") or not hasattr(client, "delete_model"):
        console.print("[danger]Platform client does not support model management.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    models = client.list_models()
    if not models:
        console.print(f"[warning]No models available to delete on {platform_name}.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    choices = [m.get("name") or m.get("id") for m in models]
    choices = [c for c in choices if c] + ["Cancel"]

    chosen = questionary.select(
        f"Select model to delete from {platform_name}:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    confirmed = questionary.confirm(
        f"Are you sure you want to delete model '{chosen}' from {platform_name}?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not confirmed:
        console.print("[dim]Deletion cancelled.[/]\n")
        return

    console.print(f"\n[bold cyan]Deleting model '{chosen}' from {platform_name}...[/]")
    try:
        success, message = client.delete_model(chosen)
        if success:
            console.print(f"[bold green]{message}[/]")
            remaining = client.list_models() or []
            _handle_deleted_model_fallback(config, platform_name, chosen, remaining)
        else:
            console.print(f"[danger]{message}[/]")
    except Exception as exc:
        console.print(f"[danger]Unexpected error deleting model '{chosen}':[/] {exc}")

    console.print()
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
