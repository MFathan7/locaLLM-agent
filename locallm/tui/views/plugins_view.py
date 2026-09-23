"""Interactive Plugins & Tools Manager view for locaLLM TUI."""

from typing import List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label
from locallm.config import LocaLLMConfig
from locallm.core.plugin_manager import (
    PluginInfo,
    create_plugin_scaffold,
    disable_plugin,
    enable_plugin,
    list_plugins,
)


class PluginsView(Widget):
    """View managing modular extensible plugins, connectors, and dynamic tool schemas."""

    DEFAULT_CSS = """
    PluginsView {
        height: 100%;
        padding: 1 2;
    }

    #plugins-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .plugin-card {
        margin-bottom: 1;
        padding: 1;
        border: round #555555;
        height: auto;
    }

    .plugin-card-enabled {
        border: round $primary;
    }

    .plugin-actions-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .plugin-actions-row Button {
        margin-right: 1;
    }

    #input-new-plug-name {
        width: 1fr;
        margin-right: 1;
    }
    """

    def __init__(self, config: LocaLLMConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.plugins: List[PluginInfo] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="plugins-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ MODULAR PLUGINS & CUSTOM TOOLS ✦", classes="stat-title")
                active_ws = getattr(self.config, "active_workspace", "default")
                yield Label(
                    f"Plugins extend the local assistant with custom tools and database connectors.\n"
                    f"Active Workspace: [bold cyan]{active_ws}[/]",
                    id="lbl-plugins-header-info",
                )
                with Horizontal(classes="plugin-actions-row"):
                    yield Button("Refresh Plugins", id="btn-refresh-plugins", variant="default")

            with Vertical(classes="stat-box", id="installed-plugins-wrapper"):
                yield Label("INSTALLED PLUGINS", classes="stat-title")
                yield Vertical(id="plugins-cards-box")

            with Vertical(classes="stat-box"):
                yield Label("CREATE NEW STARTER PLUGIN", classes="stat-title")
                yield Label("Generates a starter plugin directory with manifest (plugin.json) and entrypoint (main.py):", classes="stat-row")
                with Horizontal(classes="plugin-actions-row"):
                    yield Input(placeholder="e.g. sqlite_connector, weather_fetcher", id="input-new-plug-name")
                    yield Button("Scaffold Plugin", id="btn-create-plugin", variant="success")
                yield Label("", id="lbl-create-plug-status")

    def on_mount(self) -> None:
        self.refresh_plugins()

    def refresh_plugins(self) -> None:
        """Scan plugins and dynamically mount plugin cards."""
        try:
            active_ws = getattr(self.config, "active_workspace", "default")
            cards_box = self.query_one("#plugins-cards-box", Vertical)
            cards_box.remove_children()

            self.plugins = list_plugins(active_ws)

            if not self.plugins:
                cards_box.mount(
                    Label("[dim]No plugins currently discovered in ./plugins/, workspace, or ~/.locallm/plugins/.\nUse the form below to scaffold a starter plugin.[/]")
                )
                return

            for idx, p in enumerate(self.plugins):
                st_badge = "● [bold green]ENABLED[/]" if p.enabled else "○ [dim]DISABLED[/]"
                if p.error:
                    st_badge = f"✖ [bold red]ERROR: {p.error}[/]"

                tools_str = ", ".join(p.tools) if p.tools else "None"

                actions = []
                if p.enabled:
                    actions.append(Button("Disable Plugin", id=f"btn-plug-toggle---{idx}", variant="warning"))
                else:
                    actions.append(Button("Enable Plugin", id=f"btn-plug-toggle---{idx}", variant="success"))

                card_classes = "plugin-card plugin-card-enabled" if p.enabled else "plugin-card"
                card = Vertical(
                    Label(f"[bold cyan]{p.name}[/] (v{p.version}) - {st_badge}", classes="stat-title"),
                    Label(f"• Description: {p.description or 'No description provided.'}\n• Scope: [{p.source}]  • Tools ({len(p.tools)}): [bold cyan]{tools_str}[/]", classes="stat-row"),
                    Horizontal(*actions, classes="plugin-actions-row"),
                    classes=card_classes,
                )
                cards_box.mount(card)

        except Exception as ex:
            try:
                cards_box = self.query_one("#plugins-cards-box", Vertical)
                cards_box.remove_children()
                cards_box.mount(Label(f"[bold red]Error inspecting plugins: {ex}[/]"))
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        active_ws = getattr(self.config, "active_workspace", "default")

        if btn_id == "btn-refresh-plugins":
            self.refresh_plugins()
        elif btn_id == "btn-create-plugin":
            self._handle_create_plugin()
        elif btn_id.startswith("btn-plug-toggle---"):
            idx_str = btn_id.replace("btn-plug-toggle---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.plugins):
                    target_plugin = self.plugins[idx]
                    if target_plugin.enabled:
                        disable_plugin(target_plugin.name, active_ws)
                    else:
                        enable_plugin(target_plugin.name, active_ws)
                    self.refresh_plugins()
            except Exception:
                pass

    def _handle_create_plugin(self) -> None:
        inp = self.query_one("#input-new-plug-name", Input)
        name = inp.value.strip()
        if not name:
            self.query_one("#lbl-create-plug-status", Label).update("[red]Plugin name cannot be empty.[/]")
            return

        ok, msg, path = create_plugin_scaffold(name)
        if ok:
            inp.value = ""
            self.query_one("#lbl-create-plug-status", Label).update(f"[green]✔ Plugin '{name}' created at {path}![/]")
            self.refresh_plugins()
        else:
            self.query_one("#lbl-create-plug-status", Label).update(f"[red]✖ Failed to create plugin: {msg}[/]")
