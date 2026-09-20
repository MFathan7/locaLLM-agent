"""Unicode Header and status banner renderer."""

from typing import Any, Optional
from rich.panel import Panel
from rich.table import Table
from locallm.config import LocaLLMConfig, get_custom_platform
from locallm.core.hardware import get_gpu_info
from locallm.core.service_manager import is_custom_platform_reachable, is_ollama_running
from locallm.ui.theme import console


def render_banner(config: LocaLLMConfig, client: Optional[Any] = None) -> None:
    """Render the application header with system and backend status."""
    gpu = get_gpu_info()

    active = config.active_backend.strip().lower()
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

    status_str = f"[bold green]ONLINE[/]{version_str}" if is_online else "[bold red]OFFLINE[/]"

    if gpu:
        vram_free_gb = gpu.free_vram_mb / 1024
        vram_total_gb = gpu.total_vram_mb / 1024
        gpu_str = f"{gpu.name} ({vram_free_gb:.1f} GB Free / {vram_total_gb:.1f} GB Total)"
    else:
        gpu_str = "CPU Mode (No GPU detected)"

    features = (
        client.get_model_features(config.default_model)
        if (is_online and client and hasattr(client, "get_model_features"))
        else []
    )
    features_str = ", ".join(features) if features else "Text Generation"

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="right", ratio=1)

    grid.add_row(
        f"[dim]{backend_name} Service:[/] {status_str}",
        f"[dim]Endpoint:[/] [cyan]{endpoint}[/]",
    )
    grid.add_row(
        f"[dim]Active Model:[/] [bold cyan]{config.default_model}[/]",
        f"[dim]Model Features:[/] [bold green]{features_str}[/]",
    )
    active_ws = getattr(config, "active_workspace", "default")
    grid.add_row(
        f"[dim]Hardware:[/] [dim white]{gpu_str}[/]",
        f"[dim]Workspace:[/] [bold cyan]{active_ws}[/]",
    )

    header_title = "[bold cyan]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦[/]"

    panel = Panel(
        grid,
        title=header_title,
        title_align="center",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
