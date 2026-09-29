"""Live system and GPU monitor for locaLLM."""

import sys
import time
from typing import Any, List, Optional
import psutil
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from locallm.config import LocaLLMConfig
from locallm.core.hardware import get_gpu_extended_info
from locallm.core.openai_client import get_inference_client
from locallm.ui.theme import console, get_theme_palette


def _make_progress_bar(used: float, total: float, width: int = 24) -> str:
    """Generate a clean ASCII progress bar with filled and empty blocks."""
    if total <= 0:
        return "[" + ("░" * width) + "]"
    ratio = max(0.0, min(1.0, used / total))
    filled_len = int(round(ratio * width))
    empty_len = width - filled_len
    return "[" + ("█" * filled_len) + ("░" * empty_len) + "]"


def build_monitor_renderable(
    config: LocaLLMConfig,
    client: Optional[Any] = None,
) -> Panel:
    """Build a rich, real-time telemetry HUD panel for system, GPU, and VRAM status."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    # Service & Latency Telemetry
    backend_name = getattr(config, "active_backend", "ollama").upper()
    active_model = getattr(config, "model", "locaLLM")
    active_ws = getattr(config, "active_workspace", "default")

    if client is None:
        client = get_inference_client(config)

    ping_ms = 0.0
    is_online = False
    if client and hasattr(client, "is_connected"):
        t0 = time.time()
        try:
            is_online = bool(client.is_connected(max_cache_age=0.5))
            ping_ms = (time.time() - t0) * 1000.0
        except Exception:
            is_online = False

    status_tag = f"[{palette.success}]ONLINE[/] [dim]({ping_ms:.1f}ms)[/]" if is_online else f"[{palette.danger}]OFFLINE[/]"

    # Hardware Metrics
    gpu = get_gpu_extended_info(force_refresh=True)
    mem = psutil.virtual_memory()
    cpu_pct = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True) or 1

    # Header Grid
    header_grid = Table.grid(expand=True, padding=(0, 1))
    header_grid.add_column(justify="left")
    header_grid.add_column(justify="right")
    header_grid.add_row(
        f"[{palette.primary}]◆ Backend:[/] [white]{backend_name}[/] [dim]•[/] {status_tag}",
        f"[{palette.accent}]▸ Workspace:[/] [white]{active_ws}[/]",
    )
    header_grid.add_row(
        f"[{palette.primary}]◆ Active Model:[/] [bold cyan]{active_model}[/]",
        f"[{palette.dim}]Refresh:[/] [white]1.0s[/] [dim]• Press[/] [bold white]q[/] [dim]to return[/]",
    )

    # Resource Grid
    res_table = Table(
        box=palette.box_style,
        border_style=palette.border_style,
        expand=True,
        header_style=f"bold {palette.primary}",
        show_header=True,
    )
    res_table.add_column("Subsystem", style=f"bold {palette.primary}", width=18)
    res_table.add_column("Utilization Bar", justify="left")
    res_table.add_column("Memory / Usage", justify="right")
    res_table.add_column("Telemetry", justify="center")

    # GPU Row
    if gpu:
        gpu_used_gb = gpu.used_vram_mb / 1024.0
        gpu_total_gb = gpu.total_vram_mb / 1024.0
        gpu_pct = (gpu.used_vram_mb / gpu.total_vram_mb * 100.0) if gpu.total_vram_mb > 0 else 0.0
        bar = _make_progress_bar(gpu_used_gb, gpu_total_gb, width=22)
        pct_color = palette.success if gpu_pct < 70 else (palette.warning if gpu_pct < 90 else palette.danger)
        res_table.add_row(
            f"GPU VRAM\n[dim]{gpu.name[:18]}[/]",
            f"[{pct_color}]{bar}[/]\n[{pct_color}]{gpu_pct:.1f}% used[/]",
            f"[bold white]{gpu_used_gb:.2f}[/] / [white]{gpu_total_gb:.2f} GB[/]\n[dim]+{(gpu.free_vram_mb / 1024.0):.2f} GB free[/]",
            f"Load: [{palette.primary}]{gpu.utilization_pct}%[/]\nTemp: [white]{gpu.temperature_c}°C[/]",
        )
    else:
        res_table.add_row(
            "GPU VRAM",
            f"[{palette.dim}]" + _make_progress_bar(0, 100, width=22) + "[/]",
            "[dim]No GPU Detected[/]",
            "[dim]CPU Mode[/]",
        )

    # Host RAM Row
    ram_used_gb = (mem.total - mem.available) / (1024**3)
    ram_total_gb = mem.total / (1024**3)
    ram_pct = mem.percent
    ram_bar = _make_progress_bar(ram_used_gb, ram_total_gb, width=22)
    ram_pct_color = palette.success if ram_pct < 70 else (palette.warning if ram_pct < 90 else palette.danger)
    res_table.add_row(
        "Host RAM",
        f"[{ram_pct_color}]{ram_bar}[/]\n[{ram_pct_color}]{ram_pct:.1f}% used[/]",
        f"[bold white]{ram_used_gb:.2f}[/] / [white]{ram_total_gb:.2f} GB[/]\n[dim]+{(mem.available / (1024**3)):.2f} GB avail[/]",
        f"CPU: [{palette.primary}]{cpu_pct:.1f}%[/]\n[dim]{cpu_count} cores[/]",
    )

    # Resident Models in VRAM
    loaded_models: List[str] = []
    if client and hasattr(client, "get_loaded_models"):
        try:
            loaded_models = client.get_loaded_models()
        except Exception:
            loaded_models = []

    models_table = Table(
        box=palette.box_style,
        border_style=palette.border_style,
        expand=True,
        header_style=f"bold {palette.primary}",
        show_header=True,
    )
    models_table.add_column("Loaded Resident Model", style="bold white")
    models_table.add_column("State", justify="center", width=16)

    if loaded_models:
        for m in loaded_models:
            models_table.add_row(
                m,
                f"[{palette.success}]● ACTIVE IN VRAM[/]",
            )
    else:
        models_table.add_row(
            "[dim]No models currently resident in VRAM[/]",
            f"[{palette.dim}]STANDBY / IDLE[/]",
        )

    # Master Layout
    layout = Table.grid(expand=True)
    layout.add_column()
    layout.add_row(header_grid)
    layout.add_row("")
    layout.add_row(f"[bold {palette.primary}]⟦ HARDWARE & RUNTIME RESOURCES ⟧[/]")
    layout.add_row(res_table)
    layout.add_row("")
    layout.add_row(f"[bold {palette.primary}]⟦ RESIDENT MEMORY ALLOCATION ⟧[/]")
    layout.add_row(models_table)

    return Panel(
        layout,
        title=f"[bold {palette.primary}]✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ   s ʏ s ᴛ ᴇ ᴍ   ᴍ ᴏ ɴ ɪ ᴛ ᴏ ʀ  ✦[/]",
        subtitle="[#aaaaaa]Real-Time VRAM & Hardware HUD[/]",
        box=palette.box_style,
        border_style=palette.border_style,
        padding=(1, 2),
    )


def _check_exit_key() -> bool:
    """Check if user pressed 'q', Enter, Esc, or Ctrl+C in a non-blocking way."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b"q", b"Q", b"\r", b"\n", b"\x1b", b"\x03"):
                return True
    except ImportError:
        import select
        if sys.stdin.isatty():
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                if ch in ("q", "Q", "\n", "\x1b"):
                    return True
    return False


def run_live_monitor(
    config: LocaLLMConfig,
    client: Optional[Any] = None,
    refresh_interval: float = 1.0,
    max_iterations: Optional[int] = None,
) -> None:
    """Run interactive real-time system monitor loop."""
    console.clear()
    iteration = 0

    try:
        with Live(
            build_monitor_renderable(config, client),
            console=console,
            refresh_per_second=4,
            screen=False,
        ) as live:
            while True:
                time.sleep(0.2)
                iteration += 1

                if _check_exit_key():
                    break

                if iteration % int(max(1, refresh_interval / 0.2)) == 0:
                    live.update(build_monitor_renderable(config, client))

                if max_iterations is not None and iteration >= max_iterations:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        console.clear()
