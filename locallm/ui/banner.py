"""Unicode Header, status banner, and VRAM visual gauge renderer."""

import time
from typing import Any, Optional
import psutil
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from locallm.config import LocaLLMConfig, get_custom_platform
from locallm.core.hardware import get_gpu_extended_info
from locallm.core.service_manager import is_custom_platform_reachable, is_ollama_running
from locallm.ui.theme import console, get_theme_palette


def format_vram_bar(used_gb: float, total_gb: float, width: int = 10) -> str:
    """Render a dynamic, color-coded VRAM progress bar (btop/htop aesthetic)."""
    if total_gb <= 0:
        return "[dim]N/A[/]"
    ratio = max(0.0, min(1.0, used_gb / total_gb))
    pct = ratio * 100
    filled = int(round(ratio * width))
    empty = width - filled
    bar_str = "█" * filled + "░" * empty

    if pct >= 90:
        bar_color = "bold red"
    elif pct >= 70:
        bar_color = "bold yellow"
    else:
        bar_color = "bold green"

    return f"[{bar_color}][{bar_str}][/] {used_gb:.1f}/{total_gb:.1f} GB ({pct:.0f}%)"


def render_banner(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
    """Render the application header with system and backend status."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    gpu = get_gpu_extended_info(force_refresh=True)

    active = config.active_backend.strip().lower()
    t0 = time.time()
    if active == "ollama":
        backend_name = "Ollama"
        endpoint = config.ollama_host
        is_online = client.is_connected() if client else is_ollama_running(config.ollama_host)
        version = client.get_version() if (is_online and client and hasattr(client, "get_version")) else None
        version_str = f" (v{version})" if version else ""
    else:
        custom_platform = get_custom_platform(config, active)
        if custom_platform:
            backend_name = custom_platform.name
            endpoint = custom_platform.api_base
            is_online = client.is_connected() if client else is_custom_platform_reachable(
                custom_platform.api_base, custom_platform.api_key
            )
            version_str = ""
        else:
            backend_name = config.active_backend
            endpoint = "N/A"
            is_online = False
            version_str = ""

    ping_ms = (time.time() - t0) * 1000.0 if is_online else 0.0
    status_str = f"[bold green]ONLINE[/] [dim]({ping_ms:.1f}ms){version_str}[/]" if is_online else "[bold red]OFFLINE[/]"

    if gpu:
        used_vram_gb = gpu.used_vram_mb / 1024.0
        total_vram_gb = gpu.total_vram_mb / 1024.0
        free_vram_gb = gpu.free_vram_mb / 1024.0
        short_gpu = gpu.name.replace("NVIDIA ", "").replace("GeForce ", "").replace("Corporation ", "").strip()
        gpu_label = f"[white]{short_gpu[:18]}[/] [dim]({gpu.utilization_pct}% load • {gpu.temperature_c}°C)[/]"
        vram_display = f"[dim]VRAM:[/] {format_vram_bar(used_vram_gb, total_vram_gb)} [dim](+{free_vram_gb:.1f}G free)[/]"
    else:
        gpu_label = "[dim]CPU Mode (No GPU)[/]"
        vram_display = "[dim]VRAM:[/] [dim]N/A (CPU Mode)[/]"

    # Host RAM and CPU telemetry
    mem = psutil.virtual_memory()
    ram_used_gb = (mem.total - mem.available) / (1024**3)
    ram_total_gb = mem.total / (1024**3)
    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True) or 1
    host_display = f"[white]RAM:[/] {format_vram_bar(ram_used_gb, ram_total_gb, width=8)} [dim]•[/] [white]CPU:[/] [{palette.primary}]{cpu_pct:.1f}%[/] [dim]({cpu_count}c)[/]"

    # Loaded models currently resident in VRAM
    resident_str = "[dim]Standby (Idle)[/]"
    if is_online and client and hasattr(client, "get_loaded_models"):
        try:
            loaded = client.get_loaded_models()
            if loaded:
                resident_str = f"[bold green]●[/] [bold cyan]{', '.join(loaded[:2])}[/]"
        except Exception:
            pass

    if config.default_model.lower() == "auto":
        model_display = f"[bold {palette.primary}]Auto (Smart Router)[/]"
        features_display = f"[bold {palette.success}]Dynamic Capability Dispatch[/]"
    elif is_online and client and hasattr(client, "get_model_features"):
        features = client.get_model_features(config.default_model)
        features_str = ", ".join(features) if features else "Text Generation"
        features_display = f"[bold {palette.success}]{features_str}[/]"
        model_display = f"[bold {palette.primary}]{config.default_model}[/]"
    else:
        features_display = f"[{palette.dim}]None (Offline)[/]"
        model_display = f"[dim]{config.default_model}[/] [dim red](Offline)[/]"

    active_ws = getattr(config, "active_workspace", "default")

    # Discover active plugins count
    plugins_summary = "[dim]0 Plugins[/]"
    try:
        from locallm.core.plugin_manager import list_plugins
        plugins = list_plugins(active_ws)
        active_count = len([p for p in plugins if p.enabled and not p.error])
        if active_count > 0:
            plugins_summary = f"[bold {palette.success}]{active_count} Plugins[/]"
    except Exception:
        pass

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="right")

    grid.add_row(
        f"[bold green]●[/] [dim]Service:[/] {status_str} [dim]({backend_name})[/]",
        f"[bold {palette.primary}]⚡[/] [dim]Endpoint:[/] [{palette.primary}]{endpoint}[/]",
    )
    grid.add_row(
        f"[bold {palette.primary}]◆[/] [dim]Model:[/] {model_display}",
        f"[bold {palette.success}]★[/] [dim]Features:[/] {features_display}",
    )
    grid.add_row(
        f"[white]■[/] [dim]GPU:[/] {gpu_label}",
        f"[bold {palette.accent}]▰[/] {vram_display}",
    )
    grid.add_row(
        f"[white]◈[/] [dim]Host:[/] {host_display}",
        f"[bold {palette.success}]●[/] [dim]VRAM Resident:[/] {resident_str}",
    )
    grid.add_row(
        f"[bold {palette.primary}]▸[/] [dim]Workspace:[/] [bold {palette.primary}]{active_ws}[/]",
        f"[bold {palette.accent}]{palette.icon} {palette.name}[/]  [dim]•[/]  [bold {palette.success}]✦[/] {plugins_summary}",
    )

    logo_text = (
        f"[{palette.primary}]█░░ █▀█ █▀▀ ▄▀█ █░░ █░░ █▀▄▀█[/]\n"
        f"[{palette.accent}]█▄▄ █▄█ █▄▄ █▀█ █▄▄ █▄▄ █░▀░█[/]"
    )

    content = Table.grid(expand=True)
    content.add_column(justify="center")
    content.add_row(Align.center(logo_text))
    content.add_row("")
    content.add_row(grid)

    header_title = f"[bold {palette.primary}]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦[/]"

    panel = Panel(
        content,
        title=header_title,
        title_align="center",
        box=palette.box_style,
        border_style=palette.border_style,
        padding=(1, 2),
    )
    console.print(panel)


