"""Interactive Settings view for locaLLM TUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from locallm.config import LocaLLMConfig, save_config
from locallm.tui.themes import TUI_THEME_SPECS
from locallm.tui.widgets.theme_picker import ThemeSelected


class UiModeChanged(Message):
    """Event posted when UI mode is switched from settings."""

    def __init__(self, mode: str) -> None:
        super().__init__()
        self.mode = mode


class SettingsView(Widget):
    """View managing UI mode, theme, and inference parameters."""

    DEFAULT_CSS = """
    SettingsView {
        height: 100%;
        padding: 1 2;
    }

    #settings-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .settings-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .theme-buttons-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .theme-buttons-row Button {
        margin-right: 1;
        margin-bottom: 1;
        width: auto;
    }

    .settings-inputs-grid {
        layout: horizontal;
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    .settings-col {
        width: 1fr;
        margin-right: 1;
        height: auto;
    }

    .settings-input {
        width: 1fr;
        margin-bottom: 1;
    }
    """

    def __init__(self, config: LocaLLMConfig, active_theme: str = "cyber_neon", **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.active_theme = active_theme

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="settings-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ INTERFACE STYLE (UI MODE) ✦", classes="stat-title")
                curr_mode_label = "Modern TUI (Reactive Full-Screen)" if getattr(self.config, "ui_mode", "classic") == "modern" else "Default CLI (Traditional Scrolling)"
                yield Label(f"Current UI Mode: [bold cyan]{curr_mode_label}[/]", id="lbl-ui-mode-status", classes="stat-row")
                yield Label("Switching to Default CLI will launch the traditional terminal menu next time locaLLM runs.", classes="stat-row")
                with Horizontal(classes="settings-row"):
                    yield Button("Switch to Default CLI", id="btn-set-mode-classic", variant="warning")
                    yield Button("Keep Modern TUI (Active)", id="btn-set-mode-modern", variant="success")
                yield Label("", id="lbl-mode-feedback")

            with Vertical(classes="stat-box"):
                yield Label("ACTIVE CONSOLE THEME", classes="stat-title")
                yield Label("Click any theme to repaint all borders and colors instantaneously:", classes="stat-row")
                with Horizontal(classes="theme-buttons-row"):
                    for key, spec in TUI_THEME_SPECS.items():
                        is_active = (key == self.active_theme)
                        marker = " ✔ ACTIVE" if is_active else ""
                        yield Button(
                            f"{spec.icon} {spec.name} {spec.badge}{marker}",
                            id=f"btn-settings-theme-{key}",
                            classes="theme-select-btn theme-select-btn-active" if is_active else "theme-select-btn",
                        )

            with Vertical(classes="stat-box"):
                yield Label("INFERENCE & AGENT PARAMETERS", classes="stat-title")
                with Horizontal(classes="settings-inputs-grid"):
                    with Vertical(classes="settings-col"):
                        yield Label("Sampling Temp (0.0 to 2.0):", classes="stat-row")
                        yield Input(value=str(self.config.temperature), id="input-temp")
                    with Vertical(classes="settings-col"):
                        yield Label("Context Window (tokens):", classes="stat-row")
                        yield Input(value=str(getattr(self.config, "context_window", 8192)), id="input-ctx")
                    with Vertical(classes="settings-col"):
                        yield Label("Agent Max Steps (1 to 100):", classes="stat-row")
                        yield Input(value=str(getattr(self.config, "agent_max_steps", 25)), id="input-steps")

                yield Button("Save Inference Settings", id="btn-save-inference", variant="primary")
                yield Label("", id="lbl-inference-feedback")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-set-mode-classic":
            self.config.ui_mode = "classic"
            save_config(self.config)
            self.query_one("#lbl-ui-mode-status", Label).update("Current UI Mode: [bold yellow]Default CLI[/]")
            self.query_one("#lbl-mode-feedback", Label).update("[yellow]✔ UI Mode saved as Default CLI! When you exit or run 'locallm', the classic menu will launch.[/]")
            self.post_message(UiModeChanged("classic"))
        elif btn_id == "btn-set-mode-modern":
            self.config.ui_mode = "modern"
            save_config(self.config)
            self.query_one("#lbl-ui-mode-status", Label).update("Current UI Mode: [bold cyan]Modern TUI[/]")
            self.query_one("#lbl-mode-feedback", Label).update("[green]✔ UI Mode saved as Modern TUI![/]")
            self.post_message(UiModeChanged("modern"))
        elif btn_id and btn_id.startswith("btn-settings-theme-"):
            theme_key = btn_id.replace("btn-settings-theme-", "")
            self.active_theme = theme_key
            self.post_message(ThemeSelected(theme_key))
            self._update_theme_buttons()
        elif btn_id == "btn-save-inference":
            self._handle_save_inference()

    def _update_theme_buttons(self) -> None:
        for key, spec in TUI_THEME_SPECS.items():
            try:
                btn = self.query_one(f"#btn-settings-theme-{key}", Button)
                is_active = (key == self.active_theme)
                marker = " ✔ ACTIVE" if is_active else ""
                btn.label = f"{spec.icon} {spec.name} {spec.badge}{marker}"
                if is_active:
                    btn.add_class("theme-select-btn-active")
                else:
                    btn.remove_class("theme-select-btn-active")
            except Exception:
                pass

    def _handle_save_inference(self) -> None:
        try:
            temp_str = self.query_one("#input-temp", Input).value.strip()
            ctx_str = self.query_one("#input-ctx", Input).value.strip()
            steps_str = self.query_one("#input-steps", Input).value.strip()

            self.config.temperature = max(0.0, min(2.0, float(temp_str)))
            self.config.context_window = max(512, min(262144, int(ctx_str)))
            self.config.agent_max_steps = max(1, min(100, int(steps_str)))

            save_config(self.config)
            self.query_one("#lbl-inference-feedback", Label).update("[green]✔ Inference settings saved successfully![/]")
        except Exception as ex:
            self.query_one("#lbl-inference-feedback", Label).update(f"[red]Error saving settings: {ex}[/]")
