"""Brand header widget for locaLLM reactive TUI with auto-connectivity detection."""

from typing import Any, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label
from locallm.config import LocaLLMConfig, get_custom_platform
from locallm.core.hardware import get_gpu_info
from locallm.core.service_manager import is_custom_platform_reachable, is_ollama_running


class ExitRequested(Message):
    """Event posted when Exit button in header is clicked."""
    pass


class LocaLLMHeader(Widget):
    """Header bar displaying application branding, live connectivity, active model, and telemetry."""

    DEFAULT_CSS = """
    LocaLLMHeader {
        height: 3;
        dock: top;
        padding: 0 1;
        layout: vertical;
        border-bottom: solid;
    }

    #header-top-row {
        height: 1;
        layout: horizontal;
    }

    #header-bottom-row {
        height: 1;
        layout: horizontal;
    }

    #header-title {
        width: 1fr;
        text-style: bold;
    }

    #header-top-status {
        width: auto;
    }

    #header-sub-info {
        width: 1fr;
    }

    #header-exit-btn {
        width: auto;
        height: 1;
        min-width: 8;
        border: none;
        padding: 0 1;
        margin-left: 1;
    }
    """

    model_name: reactive[str] = reactive("Auto (Smart Router)")
    theme_badge: reactive[str] = reactive("⟦⚡ CYBER⟧")
    is_online: reactive[bool] = reactive(False)
    backend_title: reactive[str] = reactive("Ollama")
    version_str: reactive[str] = reactive("")
    endpoint_str: reactive[str] = reactive("http://127.0.0.1:11434")

    def __init__(
        self,
        config: Optional[LocaLLMConfig] = None,
        client: Optional[Any] = None,
        model_name: str = "auto",
        theme_badge: str = "⟦⚡ CYBER⟧",
        is_online: bool = False,
        **kwargs,
    ) -> None:
        kwargs.setdefault("id", "header-container")
        super().__init__(**kwargs)
        self.config = config
        self.client = client
        self.model_name = model_name
        self.theme_badge = theme_badge
        self.is_online = is_online
        self._detect_backend_status()

    def _detect_backend_status(self) -> None:
        if not self.config:
            return

        active = self.config.active_backend.strip().lower()
        if active == "ollama":
            self.backend_title = "Ollama"
            self.endpoint_str = self.config.ollama_host
            up = self.client.is_connected() if self.client else is_ollama_running(self.config.ollama_host)
            self.is_online = bool(up)
            version = None
            if self.is_online and self.client and hasattr(self.client, "get_version"):
                try:
                    version = self.client.get_version()
                except Exception:
                    pass
            self.version_str = f" (v{version})" if version else ""
        else:
            plat = get_custom_platform(self.config, active)
            if plat:
                self.backend_title = plat.name
                self.endpoint_str = plat.api_base
                up = self.client.is_connected() if self.client else is_custom_platform_reachable(plat.api_base, plat.api_key)
                self.is_online = bool(up)
                self.version_str = ""
            else:
                self.backend_title = self.config.active_backend
                self.endpoint_str = "N/A"
                self.is_online = False
                self.version_str = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="header-top-row"):
            yield Label(self._render_top_title(), id="header-title")
            with Horizontal(id="header-top-status"):
                yield Label(self._render_top_status(), id="header-status-lbl")
                yield Button("Exit", id="header-exit-btn", variant="error")

        with Horizontal(id="header-bottom-row"):
            yield Label(self._render_bottom_info(), id="header-sub-info")

    @property
    def backend_status(self) -> str:
        return "ONLINE" if self.is_online else "OFFLINE"

    def _render_title(self) -> str:
        return self._render_top_title()

    def _render_status(self) -> str:
        return self._render_top_status()

    def _render_top_title(self) -> str:
        model_disp = "Auto (Smart Router)" if (not self.model_name or self.model_name.lower() == "auto") else self.model_name
        return f"✦  ʟ ᴏ ᴄ ᴀ ʟ ʟ ᴍ  ✦   •   Model: {model_disp}"

    def _render_top_status(self) -> str:
        status_dot = "●" if self.is_online else "○"
        status_word = "ONLINE" if self.is_online else "OFFLINE"
        return f"{status_dot} {self.backend_title}: {status_word}{self.version_str}   {self.theme_badge}"

    def _render_bottom_info(self) -> str:
        ws_name = getattr(self.config, "active_workspace", "default") if self.config else "default"
        gpu = get_gpu_info()
        gpu_str = f"■ GPU: {gpu.name[:18]} ({gpu.used_vram_mb/1024:.1f}/{gpu.total_vram_mb/1024:.1f} GB)" if gpu else "■ CPU Mode"
        return f"⚡ Endpoint: {self.endpoint_str}   {gpu_str}   ▸ Workspace: {ws_name}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "header-exit-btn":
            self.post_message(ExitRequested())

    def update_model(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            self.query_one("#header-title", Label).update(self._render_top_title())
        except Exception:
            pass

    def update_status(self) -> None:
        self._detect_backend_status()
        try:
            self.query_one("#header-status-lbl", Label).update(self._render_top_status())
            self.query_one("#header-sub-info", Label).update(self._render_bottom_info())
        except Exception:
            pass
