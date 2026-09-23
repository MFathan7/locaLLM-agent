"""Interactive Services & Platform Manager view for locaLLM TUI."""

from typing import Any, List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from locallm.config import (
    CustomPlatformConfig,
    LocaLLMConfig,
    add_custom_platform,
    remove_custom_platform,
    save_config,
    switch_active_backend,
)
from locallm.core.service_manager import (
    is_custom_platform_reachable,
    is_ollama_running,
    start_ollama_service,
    stop_ollama_service,
)


class BackendChanged(Message):
    """Event posted when active backend platform is switched."""

    def __init__(self, backend_name: str) -> None:
        super().__init__()
        self.backend_name = backend_name


class ServicesView(Widget):
    """View managing background daemons (Ollama) and custom OpenAI-compatible platforms."""

    DEFAULT_CSS = """
    ServicesView {
        height: 100%;
        padding: 1 2;
    }

    #services-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .service-btn-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .service-btn-row Button {
        margin-right: 1;
    }

    .plat-card {
        margin-bottom: 1;
        padding: 1;
        border: round #555555;
        height: auto;
    }

    .plat-card-active {
        border: round $primary;
    }

    .form-input {
        margin-bottom: 1;
    }
    """

    def __init__(self, config: LocaLLMConfig, client: Any, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.client = client

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="services-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ ACTIVE INFERENCE BACKEND ✦", classes="stat-title")
                yield Label(self._render_active_backend_text(), id="lbl-active-backend-status")

            with Vertical(classes="stat-box"):
                yield Label("OLLAMA SERVICE DAEMON", classes="stat-title")
                yield Label("Inspecting Ollama daemon...", id="lbl-ollama-daemon-status")
                with Horizontal(classes="service-btn-row"):
                    yield Button("Start Ollama Daemon", id="btn-start-ollama", variant="success")
                    yield Button("Stop Ollama Daemon", id="btn-stop-ollama", variant="error")
                    yield Button("Set Active: Ollama", id="btn-set-ollama-active", variant="primary")
                    yield Button("Refresh Status", id="btn-refresh-services", variant="default")

            with Vertical(classes="stat-box", id="custom-platforms-wrapper"):
                yield Label("CUSTOM OPENAI-COMPATIBLE PLATFORMS", classes="stat-title")
                yield Vertical(id="custom-platforms-cards-box")

            with Vertical(classes="stat-box"):
                yield Label("REGISTER NEW PLATFORM", classes="stat-title")
                yield Input(placeholder="Platform Name (e.g. vLLM, LMStudio, LocalAI)", id="input-new-plat-name", classes="form-input")
                yield Input(placeholder="Endpoint API Base (e.g. http://127.0.0.1:8000/v1)", id="input-new-plat-url", classes="form-input")
                yield Input(placeholder="API Key (optional)", id="input-new-plat-key", classes="form-input", password=True)
                yield Button("Register Platform", id="btn-add-platform", variant="success")
                yield Label("", id="lbl-add-plat-status")

    def on_mount(self) -> None:
        self.refresh_services()

    def _render_active_backend_text(self) -> str:
        backend = self.config.active_backend.upper()
        if self.config.active_backend.lower() == "ollama":
            up = is_ollama_running(self.config.ollama_host)
            up_str = "[bold green]ONLINE[/]" if up else "[bold red]OFFLINE[/]"
            return f"Current Backend: [bold cyan]OLLAMA[/]  • Endpoint: {self.config.ollama_host}  • Status: {up_str}"
        else:
            return f"Current Backend: [bold cyan]{backend}[/]"

    def refresh_services(self) -> None:
        """Query Ollama and custom platforms connectivity."""
        try:
            # Check Ollama
            running = is_ollama_running(self.config.ollama_host)
            status_dot = "● [bold green]ONLINE / RUNNING[/]" if running else "○ [bold red]OFFLINE / STOPPED[/]"
            self.query_one("#lbl-ollama-daemon-status", Label).update(
                f"• Status: {status_dot}\n• Endpoint: {self.config.ollama_host}"
            )
            self.query_one("#lbl-active-backend-status", Label).update(self._render_active_backend_text())

            # Check custom platforms cards
            cards_box = self.query_one("#custom-platforms-cards-box", Vertical)
            cards_box.remove_children()

            if not self.config.custom_platforms:
                cards_box.mount(
                    Label("[dim]No custom platforms registered. You can add one below (vLLM, LMStudio, LocalAI).[/]")
                )
            else:
                for idx, p in enumerate(self.config.custom_platforms):
                    is_active = (self.config.active_backend.lower() == p.name.lower())
                    is_up = is_custom_platform_reachable(p.api_base, p.api_key)
                    up_str = "● [bold green]ONLINE[/]" if is_up else "○ [bold red]OFFLINE[/]"
                    active_marker = "  [bold cyan]★ ACTIVE PLATFORM[/]" if is_active else ""
                    key_preview = "Configured (masked)" if p.api_key else "None"

                    row_buttons = []
                    if is_active:
                        row_buttons.append(Button("Active Platform", disabled=True, variant="default"))
                    else:
                        row_buttons.append(Button("Set Active", id=f"btn-plat-act---{idx}", variant="primary"))

                    row_buttons.append(Button("Remove", id=f"btn-plat-del---{idx}", variant="error"))

                    card_classes = "plat-card plat-card-active" if is_active else "plat-card"
                    card = Vertical(
                        Label(f"[bold cyan]{p.name}[/]{active_marker} - {up_str}", classes="stat-title"),
                        Label(f"• Endpoint API Base: [bold white]{p.api_base}[/]\n• API Key: {key_preview}", classes="stat-row"),
                        Horizontal(*row_buttons, classes="service-btn-row"),
                        classes=card_classes,
                    )
                    cards_box.mount(card)

        except Exception as ex:
            try:
                cards_box = self.query_one("#custom-platforms-cards-box", Vertical)
                cards_box.remove_children()
                cards_box.mount(Label(f"[bold red]Error inspecting services: {ex}[/]"))
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-refresh-services":
            self.refresh_services()
        elif btn_id == "btn-start-ollama":
            ok, msg = start_ollama_service()
            self.query_one("#lbl-ollama-daemon-status", Label).update(f"Start result: {msg}")
            self.set_timer(1.0, self.refresh_services)
        elif btn_id == "btn-stop-ollama":
            ok, msg = stop_ollama_service(self.config.ollama_host)
            self.query_one("#lbl-ollama-daemon-status", Label).update(f"Stop result: {msg}")
            self.set_timer(1.0, self.refresh_services)
        elif btn_id == "btn-set-ollama-active":
            switch_active_backend(self.config, "ollama")
            self.post_message(BackendChanged("ollama"))
            self.refresh_services()
        elif btn_id == "btn-add-platform":
            self._handle_add_platform()
        elif btn_id.startswith("btn-plat-act---"):
            idx_str = btn_id.replace("btn-plat-act---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.config.custom_platforms):
                    p = self.config.custom_platforms[idx]
                    switch_active_backend(self.config, p.name)
                    self.post_message(BackendChanged(p.name))
                    self.refresh_services()
            except Exception:
                pass
        elif btn_id.startswith("btn-plat-del---"):
            idx_str = btn_id.replace("btn-plat-del---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.config.custom_platforms):
                    p = self.config.custom_platforms[idx]
                    remove_custom_platform(self.config, p.name)
                    if self.config.active_backend.lower() == p.name.lower():
                        switch_active_backend(self.config, "ollama")
                        self.post_message(BackendChanged("ollama"))
                    self.refresh_services()
            except Exception:
                pass

    def _handle_add_platform(self) -> None:
        name_inp = self.query_one("#input-new-plat-name", Input)
        url_inp = self.query_one("#input-new-plat-url", Input)
        key_inp = self.query_one("#input-new-plat-key", Input)

        name = name_inp.value.strip()
        url = url_inp.value.strip()
        key = key_inp.value.strip()

        if not name or not url:
            self.query_one("#lbl-add-plat-status", Label).update("[red]Name and Endpoint URL are required.[/]")
            return

        new_plat = CustomPlatformConfig(name=name, api_base=url, api_key=key)
        ok, msg = add_custom_platform(self.config, new_plat)
        if ok:
            name_inp.value = ""
            url_inp.value = ""
            key_inp.value = ""
            self.query_one("#lbl-add-plat-status", Label).update(f"[green]✔ {msg}[/]")
            self.refresh_services()
        else:
            self.query_one("#lbl-add-plat-status", Label).update(f"[red]✖ {msg}[/]")
