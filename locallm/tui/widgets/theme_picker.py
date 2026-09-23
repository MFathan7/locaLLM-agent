"""Theme selection widgets and modal dialog for locaLLM TUI."""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Label
from locallm.tui.themes import TUI_THEME_SPECS, list_tui_themes


class ThemeSelected(Message):
    """Event posted when a new theme is selected."""

    def __init__(self, theme_key: str) -> None:
        super().__init__()
        self.theme_key = theme_key


class ThemeSwitcherWidget(Widget):
    """Sidebar tab component allowing instantaneous theme selection."""

    DEFAULT_CSS = """
    ThemeSwitcherWidget {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, active_theme: str = "cyber_neon", **kwargs) -> None:
        super().__init__(**kwargs)
        self.active_theme = active_theme

    def compose(self) -> ComposeResult:
        with Vertical(classes="stat-box"):
            yield Label("ACTIVE CONSOLE THEMES", classes="stat-title")
            yield Label("Click any theme to apply styling instantly:", classes="stat-row")

            for key, spec in TUI_THEME_SPECS.items():
                is_active = key == self.active_theme
                active_indicator = " ✔ ACTIVE" if is_active else ""
                btn_label = f"{spec.icon} {spec.name} {spec.badge}{active_indicator}"
                btn_cls = "theme-select-btn theme-select-btn-active" if is_active else "theme-select-btn"
                yield Button(btn_label, id=f"btn-theme-{key}", classes=btn_cls)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("btn-theme-"):
            theme_key = event.button.id.replace("btn-theme-", "")
            self.active_theme = theme_key
            self.post_message(ThemeSelected(theme_key))
            self._refresh_button_labels()

    def update_active_theme(self, theme_key: str) -> None:
        """Update active marker without re-triggering post_message."""
        self.active_theme = theme_key
        self._refresh_button_labels()

    def _refresh_button_labels(self) -> None:
        for key, spec in TUI_THEME_SPECS.items():
            btn_id = f"#btn-theme-{key}"
            try:
                btn = self.query_one(btn_id, Button)
                is_active = key == self.active_theme
                active_indicator = " ✔ ACTIVE" if is_active else ""
                btn.label = f"{spec.icon} {spec.name} {spec.badge}{active_indicator}"
                if is_active:
                    btn.add_class("theme-select-btn-active")
                else:
                    btn.remove_class("theme-select-btn-active")
            except Exception:
                pass


class ThemePickerModal(ModalScreen[Optional[str]]):
    """Floating modal dialog for cycling and choosing themes (invoked by Ctrl+T)."""

    DEFAULT_CSS = """
    ThemePickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #theme-modal-box {
        width: 55;
        height: auto;
        padding: 1 2;
        border: double $primary;
        background: $surface;
    }

    #modal-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        color: $primary;
    }

    #modal-close-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_modal", "Dismiss"),
        ("1", "select_theme('cyber_neon')", "Cyber Neon"),
        ("2", "select_theme('tokyo_night')", "Tokyo Night"),
        ("3", "select_theme('monokai')", "Monokai"),
        ("4", "select_theme('matrix')", "Matrix"),
        ("5", "select_theme('nordic_frost')", "Nordic Frost"),
    ]

    def __init__(self, active_theme: str = "cyber_neon") -> None:
        super().__init__()
        self.active_theme = active_theme

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-modal-box"):
            yield Label("✦ SELECT TUI THEME ✦", id="modal-title")
            themes = list_tui_themes()
            for idx, (key, name, badge) in enumerate(themes, start=1):
                marker = " ✔" if key == self.active_theme else ""
                yield Button(
                    f"[{idx}] {name} {badge}{marker}",
                    id=f"modal-theme-{key}",
                    classes="theme-select-btn",
                )
            yield Button("Close (Esc)", id="modal-close-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal-close-btn":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("modal-theme-"):
            key = event.button.id.replace("modal-theme-", "")
            self.dismiss(key)

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def action_select_theme(self, theme_key: str) -> None:
        self.dismiss(theme_key)
