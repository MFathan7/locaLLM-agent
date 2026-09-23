"""Real-time hardware, VRAM, and context window telemetry widget for locaLLM TUI."""

from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static
from locallm.core.hardware import get_system_resources


class TelemetryPane(Widget):
    """Sidebar widget rendering live model specs, VRAM usage, and context token telemetry."""

    DEFAULT_CSS = """
    TelemetryPane {
        height: auto;
        padding: 0 1;
    }
    """

    model_name: reactive[str] = reactive("default")
    backend_info: reactive[str] = reactive("Ollama (127.0.0.1:11434)")
    capabilities: reactive[str] = reactive("Tools")
    context_tokens: reactive[int] = reactive(0)
    context_limit: reactive[int] = reactive(8192)
    speed_tok_s: reactive[float] = reactive(0.0)

    def __init__(
        self,
        model_name: str = "default",
        backend_info: str = "Ollama",
        capabilities: Optional[List[str]] = None,
        context_limit: int = 8192,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name
        self.backend_info = backend_info
        caps = capabilities or ["Tools"]
        self.capabilities = ", ".join(caps)
        self.context_limit = context_limit

    def compose(self) -> ComposeResult:
        with Vertical(classes="stat-box"):
            yield Label("MODEL SPECIFICATIONS", classes="stat-title")
            yield Label(f"• Model: {self.model_name}", id="telemetry-model-lbl", classes="stat-row")
            yield Label(f"• Backend: {self.backend_info}", id="telemetry-backend-lbl", classes="stat-row")
            yield Label(f"• Features: {self.capabilities}", id="telemetry-caps-lbl", classes="stat-row")

        with Vertical(classes="stat-box"):
            yield Label("HARDWARE & VRAM", classes="stat-title")
            yield Label("Detecting hardware...", id="telemetry-vram-lbl", classes="stat-row")
            yield ProgressBar(total=100, id="telemetry-vram-bar", show_eta=False)

        with Vertical(classes="stat-box"):
            yield Label("CONTEXT WINDOW", classes="stat-title")
            yield Label("• Context: 0 / 8,192 (0.0%)", id="telemetry-ctx-lbl", classes="stat-row")
            yield ProgressBar(total=100, id="telemetry-ctx-bar", show_eta=False)
            yield Label("• Speed: -- tok/s", id="telemetry-speed-lbl", classes="stat-row")

    def on_mount(self) -> None:
        self.refresh_hardware()
        self.set_interval(10.0, self.refresh_hardware)

    def refresh_hardware(self) -> None:
        """Query GPU and RAM telemetry and update progress bar."""
        try:
            res = get_system_resources()
            if res.gpu:
                used_gb = res.gpu.used_vram_mb / 1024.0
                total_gb = res.gpu.total_vram_mb / 1024.0
                pct = (used_gb / total_gb * 100.0) if total_gb > 0 else 0.0
                lbl_text = f"• GPU: {res.gpu.name[:22]}\n• VRAM: {used_gb:.1f} / {total_gb:.1f} GB ({pct:.1f}%)"
            else:
                used_ram = res.ram_total_gb - res.ram_available_gb
                pct = (used_ram / res.ram_total_gb * 100.0) if res.ram_total_gb > 0 else 0.0
                lbl_text = f"• System RAM (CPU Mode)\n• RAM: {used_ram:.1f} / {res.ram_total_gb:.1f} GB ({pct:.1f}%)"

            self.query_one("#telemetry-vram-lbl", Label).update(lbl_text)
            self.query_one("#telemetry-vram-bar", ProgressBar).progress = min(100.0, max(0.0, pct))
        except Exception:
            pass

    def update_metrics(self, context_tokens: int, limit: int = 8192, speed: float = 0.0) -> None:
        """Update active session token count, limit, and generation speed."""
        self.context_tokens = context_tokens
        self.context_limit = max(1, limit)
        self.speed_tok_s = speed

        pct = (self.context_tokens / self.context_limit) * 100.0
        pct_clamped = min(100.0, max(0.0, pct))

        try:
            self.query_one("#telemetry-ctx-lbl", Label).update(
                f"• Context: {self.context_tokens:,} / {self.context_limit:,} ({pct:.1f}%)"
            )
            self.query_one("#telemetry-ctx-bar", ProgressBar).progress = pct_clamped
            speed_text = f"• Speed: {speed:.1f} tok/s" if speed > 0 else "• Speed: idle"
            self.query_one("#telemetry-speed-lbl", Label).update(speed_text)
        except Exception:
            pass

    def update_model(self, model_name: str, backend_info: str = "", capabilities: Optional[List[str]] = None) -> None:
        """Update active model metadata."""
        self.model_name = model_name
        if backend_info:
            self.backend_info = backend_info
        if capabilities:
            self.capabilities = ", ".join(capabilities)

        try:
            self.query_one("#telemetry-model-lbl", Label).update(f"• Model: {self.model_name}")
            self.query_one("#telemetry-backend-lbl", Label).update(f"• Backend: {self.backend_info}")
            self.query_one("#telemetry-caps-lbl", Label).update(f"• Features: {self.capabilities}")
        except Exception:
            pass
