"""locaLLM Master Reactive TUI Application built on Textual."""

from typing import Any, Optional
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, TabbedContent, TabPane
from locallm.config import LocaLLMConfig, save_config
from locallm.tui.themes import build_app_tcss, get_tui_theme
from locallm.tui.views import (
    IntegrationsView,
    ModelsView,
    PluginsView,
    ServicesView,
    SettingsView,
    WorkspacesView,
)
from locallm.tui.views.integrations_view import RunAgentTaskRequested
from locallm.tui.views.models_view import ModelChanged
from locallm.tui.views.services_view import BackendChanged
from locallm.tui.views.settings_view import UiModeChanged
from locallm.tui.views.workspaces_view import WorkspaceChanged
from locallm.tui.widgets import (
    ChatMessageWidget,
    ChatScrollContainer,
    LocaLLMHeader,
    PromptBox,
    TelemetryPane,
    ThemePickerModal,
    ToolCardWidget,
    WorkspacePane,
)
from locallm.tui.widgets.header import ExitRequested
from locallm.tui.widgets.theme_picker import ThemeSelected
from locallm.tui.worker import TuiInferenceSession
from locallm.ui.chat_view import render_application_farewell
from locallm.ui.theme import apply_active_theme, get_theme_palette


class LocaLLMApp(App):
    """Full-screen reactive desktop-grade terminal application for locaLLM."""

    CSS = build_app_tcss()

    BINDINGS = [
        ("ctrl+q", "quit_app", "Quit"),
        ("ctrl+t", "open_theme_picker", "Themes"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("f2", "nav_tab('tab-assistant')", "Assistant"),
        ("f3", "nav_tab('tab-workspaces')", "Workspaces"),
        ("f4", "nav_tab('tab-integrations')", "Integrations"),
        ("f5", "nav_tab('tab-models')", "Models"),
        ("f6", "nav_tab('tab-plugins')", "Plugins"),
        ("f7", "nav_tab('tab-services')", "Services"),
        ("f8", "nav_tab('tab-settings')", "Settings"),
        ("ctrl+1", "nav_tab('tab-assistant')", "Assistant"),
        ("ctrl+2", "nav_tab('tab-workspaces')", "Workspaces"),
        ("ctrl+3", "nav_tab('tab-integrations')", "Integrations"),
        ("ctrl+4", "nav_tab('tab-models')", "Models"),
        ("ctrl+5", "nav_tab('tab-plugins')", "Plugins"),
        ("ctrl+6", "nav_tab('tab-services')", "Services"),
        ("ctrl+7", "nav_tab('tab-settings')", "Settings"),
        ("f1", "show_help", "Help"),
    ]

    def __init__(
        self,
        config: LocaLLMConfig,
        client: Any,
        initial_theme: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.client = client
        self.active_theme = (initial_theme or getattr(config, "ui_theme", "cyber_neon")).strip().lower()
        self.session = TuiInferenceSession(config, client)
        self.is_busy = False
        self.unloaded_count = 0

    def compose(self) -> ComposeResult:
        theme_spec = get_tui_theme(self.active_theme)
        is_up = self.client.is_connected() if self.client else False

        yield LocaLLMHeader(
            config=self.config,
            client=self.client,
            model_name=getattr(self.config, "default_model", "auto"),
            theme_badge=theme_spec.badge,
            is_online=is_up,
            id="header-container",
        )

        with TabbedContent(id="main-app-tabs"):
            with TabPane("💬 Assistant", id="tab-assistant"):
                with Horizontal(id="main-body"):
                    with Vertical(id="left-pane"):
                        with ChatScrollContainer(id="chat-scroll"):
                            yield Vertical(id="chat-messages-container")
                        yield PromptBox(id="prompt-container")

                    with Vertical(id="right-pane"):
                        yield TelemetryPane(
                            model_name=getattr(self.config, "default_model", "auto"),
                            backend_info=f"{self.config.active_backend.upper()}",
                            context_limit=getattr(self.config, "context_window", 8192),
                            id="telemetry-pane",
                        )
                        yield WorkspacePane(
                            workspace_name=getattr(self.config, "active_workspace", "default"),
                            id="workspace-pane",
                        )

            with TabPane("📁 Workspaces", id="tab-workspaces"):
                yield WorkspacesView(config=self.config, id="view-workspaces")

            with TabPane("🤖 Integrations", id="tab-integrations"):
                yield IntegrationsView(config=self.config, client=self.client, id="view-integrations")

            with TabPane("🧠 Models", id="tab-models"):
                yield ModelsView(config=self.config, client=self.client, id="view-models")

            with TabPane("🧩 Plugins", id="tab-plugins"):
                yield PluginsView(config=self.config, id="view-plugins")

            with TabPane("⚡ Services", id="tab-services"):
                yield ServicesView(config=self.config, client=self.client, id="view-services")

            with TabPane("⚙ Settings", id="tab-settings"):
                yield SettingsView(config=self.config, active_theme=self.active_theme, id="view-settings")

        yield Label(
            "F2-F8: Tabs (or Ctrl+1-7)  •  Ctrl+T: Themes  •  Ctrl+L: Clear Chat  •  Ctrl+Q: Quit & Release VRAM  •  F1: Help",
            id="footer-container",
        )

    def on_mount(self) -> None:
        self.set_theme(self.active_theme, persist=False)
        self._show_welcome_message()
        try:
            prompt_box = self.query_one("#prompt-container", PromptBox)
            prompt_box.focus_input()
        except Exception:
            pass

    def _show_welcome_message(self) -> None:
        palette = get_theme_palette(self.active_theme)
        model_display = getattr(self.config, "default_model", "auto")
        backend_name = self.config.active_backend.upper()
        active_ws = getattr(self.config, "active_workspace", "default")
        is_up = self.client.is_connected() if self.client and hasattr(self.client, "is_connected") else False
        status_disp = "🟢 Online" if is_up else "🔴 Offline (Press F7 for Services)"
        welcome_md = (
            f"### ✦ Welcome to locaLLM Reactive Platform ✦\n"
            f"**Model:** `{model_display}` • **Backend:** `{backend_name}` ({status_disp}) • **Workspace:** `{active_ws}`\n\n"
            f"Navigate tabs above with mouse or keys (`F2` Assistant, `F3` Workspaces, `F4` Integrations, `F5` Models, `F6` Plugins, `F7` Services, `F8` Settings).\n"
            f"Type your prompt below or use slash commands like `/help`, `/stats`, `/theme`, or `/clear`."
        )
        self._add_message(role="assistant", header_text=palette.ai_prefix, content=welcome_md)

    def set_theme(self, theme_key: str, persist: bool = True) -> None:
        """Apply theme class to root Screen, update tokens, and persist to config."""
        target_key = theme_key.strip().lower()
        spec = get_tui_theme(target_key)
        self.active_theme = spec.key

        try:
            screen = self.screen
            for old_theme in ("cyber_neon", "tokyo_night", "monokai", "matrix", "nordic_frost"):
                screen.remove_class(f"theme-{old_theme}")
            screen.add_class(f"theme-{spec.key}")
        except Exception:
            pass

        apply_active_theme(spec.key)

        try:
            header = self.query_one("#header-container", LocaLLMHeader)
            header.theme_badge = spec.badge
        except Exception:
            pass

        if persist:
            self.config.ui_theme = spec.key
            save_config(self.config)

    def on_theme_selected(self, event: ThemeSelected) -> None:
        self.set_theme(event.theme_key, persist=True)

    def on_model_changed(self, event: ModelChanged) -> None:
        self.config.default_model = event.model_name
        try:
            header = self.query_one("#header-container", LocaLLMHeader)
            header.update_model(event.model_name)
            telemetry = self.query_one("#telemetry-pane", TelemetryPane)
            telemetry.update_model(event.model_name)
        except Exception:
            pass

    def on_backend_changed(self, event: BackendChanged) -> None:
        from locallm.core.openai_client import get_inference_client
        self.client = get_inference_client(self.config)
        self.session.client = self.client
        try:
            header = self.query_one("#header-container", LocaLLMHeader)
            header.client = self.client
            header.update_status()
            telemetry = self.query_one("#telemetry-pane", TelemetryPane)
            telemetry.update_model(getattr(self.config, "default_model", "auto"), backend_info=event.backend_name.upper())
            models_view = self.query_one("#view-models", ModelsView)
            models_view.client = self.client
            models_view.refresh_models()
        except Exception:
            pass

    def on_workspace_changed(self, event: WorkspaceChanged) -> None:
        self.session.active_workspace = event.workspace_name
        self.session._init_system_prompt()
        try:
            header = self.query_one("#header-container", LocaLLMHeader)
            header.update_status()
            ws_pane = self.query_one("#workspace-pane", WorkspacePane)
            ws_pane.update_workspace(event.workspace_name)
            self.query_one("#view-workspaces", WorkspacesView).refresh_workspaces()
            self.query_one("#view-plugins", PluginsView).refresh_plugins()
        except Exception:
            pass

    def on_ui_mode_changed(self, event: UiModeChanged) -> None:
        self.config.ui_mode = event.mode
        save_config(self.config)

    def on_run_agent_task_requested(self, event: RunAgentTaskRequested) -> None:
        """Switch to Assistant tab and execute user agent task."""
        self.action_nav_tab("tab-assistant")
        palette = get_theme_palette(self.active_theme)
        self._add_message(role="user", header_text=palette.user_prefix, content=event.task_instruction)
        self._run_assistant_turn(event.task_instruction)

    def on_exit_requested(self, event: ExitRequested) -> None:
        self.action_quit_app()

    def action_nav_tab(self, tab_id: str) -> None:
        try:
            self.set_focus(None)
            tabs = self.query_one("#main-app-tabs", TabbedContent)
            tabs.active = tab_id
            self._refresh_tab_content(tab_id)
        except Exception:
            pass

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane_id = getattr(event.pane, "id", None)
        if not pane_id and hasattr(event, "tab") and event.tab:
            pane_id = event.tab.id.replace("--content-tab-", "")
        if pane_id:
            self._refresh_tab_content(pane_id)

    def _refresh_tab_content(self, pane_id: str) -> None:
        if pane_id == "tab-models":
            try:
                self.query_one("#view-models", ModelsView).refresh_models()
            except Exception:
                pass
        elif pane_id == "tab-workspaces":
            try:
                self.query_one("#view-workspaces", WorkspacesView).refresh_workspaces()
            except Exception:
                pass
        elif pane_id == "tab-services":
            try:
                self.query_one("#view-services", ServicesView).refresh_services()
            except Exception:
                pass
        elif pane_id == "tab-plugins":
            try:
                self.query_one("#view-plugins", PluginsView).refresh_plugins()
            except Exception:
                pass
        elif pane_id == "tab-integrations":
            try:
                self.query_one("#view-integrations", IntegrationsView).refresh_integrations()
            except Exception:
                pass
        elif pane_id == "tab-assistant":
            try:
                prompt = self.query_one("#prompt-container", PromptBox)
                prompt.focus_input()
            except Exception:
                pass

    def action_open_theme_picker(self) -> None:
        def _on_modal_close(selected_key: Optional[str]) -> None:
            if selected_key:
                self.set_theme(selected_key, persist=True)

        self.push_screen(ThemePickerModal(active_theme=self.active_theme), _on_modal_close)

    def action_clear_chat(self) -> None:
        self.session.clear()
        try:
            container = self.query_one("#chat-messages-container", Vertical)
            container.remove_children()
            self._show_welcome_message()
            telemetry = self.query_one("#telemetry-pane", TelemetryPane)
            telemetry.update_metrics(0, getattr(self.config, "context_window", 8192), 0.0)
        except Exception:
            pass

    def action_show_help(self) -> None:
        help_text = (
            "### ✦ Keyboard Shortcuts & Navigation ✦\n"
            "- **`F2-F8`** or **`Ctrl+1-7`**: Quick Tab Navigation:\n"
            "  - `F2` / `Ctrl+1`: 💬 Assistant\n"
            "  - `F3` / `Ctrl+2`: 📁 Workspaces\n"
            "  - `F4` / `Ctrl+3`: 🤖 Integrations\n"
            "  - `F5` / `Ctrl+4`: 🧠 Models\n"
            "  - `F6` / `Ctrl+5`: 🧩 Plugins\n"
            "  - `F7` / `Ctrl+6`: ⚡ Services\n"
            "  - `F8` / `Ctrl+7`: ⚙ Settings\n"
            "- **`Ctrl+T`**: Open Theme Picker dialog\n"
            "- **`Ctrl+L`**: Clear chat history\n"
            "- **`Ctrl+Q`**: Release VRAM and Quit to terminal\n"
            "- **`/stats`**: View token context and generation metrics\n"
            "- **`/theme <name>`**: Switch active theme (`cyber_neon`, `tokyo_night`, `monokai`, `matrix`, `nordic_frost`)\n"
            "- **`/clear`**: Free session memory\n"
            "- **`/help`**: Show this reference\n"
        )
        palette = get_theme_palette(self.active_theme)
        self._add_message(role="assistant", header_text=palette.ai_prefix, content=help_text)

    def action_quit_app(self) -> None:
        """Gracefully release model from VRAM and exit."""
        try:
            self.unloaded_count = self.client.unload_all_models(fallback_model=self.config.default_model)
        except Exception:
            self.unloaded_count = 0
        self.exit()

    def on_prompt_box_submitted(self, event: PromptBox.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        if query.startswith("/"):
            self._handle_slash_command(query)
            return

        if self.is_busy:
            return

        palette = get_theme_palette(self.active_theme)
        self._add_message(role="user", header_text=palette.user_prefix, content=query)
        self._run_assistant_turn(query)

    def _handle_slash_command(self, cmd_line: str) -> None:
        parts = cmd_line.strip().split()
        cmd = parts[0].lower()
        palette = get_theme_palette(self.active_theme)

        if cmd in ("/clear", "/reset"):
            self.action_clear_chat()
        elif cmd in ("/help", "?"):
            self.action_show_help()
        elif cmd in ("/stats", "/context", "/telemetry"):
            ctx_tokens = self.session.context_tokens
            limit = getattr(self.config, "context_window", 8192)
            pct = (ctx_tokens / limit * 100.0) if limit > 0 else 0.0
            msg = (
                f"### Telemetry Stats\n"
                f"- **Model:** `{self.config.default_model}`\n"
                f"- **Context:** `{ctx_tokens:,} / {limit:,} tokens` ({pct:.1f}%)\n"
                f"- **Workspace:** `{getattr(self.config, 'active_workspace', 'default')}`\n"
                f"- **Theme:** `{self.active_theme}`\n"
            )
            self._add_message("assistant", palette.ai_prefix, msg)
        elif cmd in ("/model", "/models"):
            features = self.client.get_model_features(self.config.default_model)
            msg = f"**Active Model:** `{self.config.default_model}` (Features: `{', '.join(features)}`)"
            self._add_message("assistant", palette.ai_prefix, msg)
        elif cmd == "/theme":
            if len(parts) > 1:
                target_theme = parts[1].lower()
                self.set_theme(target_theme, persist=True)
                self._add_message("assistant", palette.ai_prefix, f"Switched theme to **{target_theme}**")
            else:
                self.action_open_theme_picker()
        else:
            self._add_message("assistant", palette.ai_prefix, f"Unknown command: `{cmd}`. Type `/help` for guidance.")

    def _add_message(self, role: str, header_text: str, content: str = "") -> ChatMessageWidget:
        widget = ChatMessageWidget(role=role, header_text=header_text, initial_content=content)
        try:
            container = self.query_one("#chat-messages-container", Vertical)
            container.mount(widget)
            scroll = self.query_one("#chat-scroll", ChatScrollContainer)
            scroll.scroll_to_latest()
        except Exception:
            pass
        return widget

    @work(thread=True)
    def _run_assistant_turn(self, user_text: str) -> None:
        """Run generation loop and tool calls in a background thread."""
        self.is_busy = True
        palette = get_theme_palette(self.active_theme)

        assistant_widget = None
        def _mount_assistant():
            nonlocal assistant_widget
            assistant_widget = self._add_message("assistant", palette.ai_prefix, "")
        self.call_from_thread(_mount_assistant)

        def on_token(token: str) -> None:
            if assistant_widget:
                self.call_from_thread(assistant_widget.append_token, token)
                try:
                    scroll = self.query_one("#chat-scroll", ChatScrollContainer)
                    self.call_from_thread(scroll.scroll_to_latest)
                except Exception:
                    pass

        def on_tool_start(tool_name: str, arguments: dict) -> ToolCardWidget:
            card = ToolCardWidget(tool_name=tool_name, arguments=arguments)
            def _mount_card():
                container = self.query_one("#chat-messages-container", Vertical)
                container.mount(card)
                scroll = self.query_one("#chat-scroll", ChatScrollContainer)
                scroll.scroll_to_latest()
            self.call_from_thread(_mount_card)
            return card

        def on_tool_end(card: ToolCardWidget, observation: str, success: bool, duration: float) -> None:
            def _finish_card():
                card.complete(observation=observation, success=success, duration=duration)
                scroll = self.query_one("#chat-scroll", ChatScrollContainer)
                scroll.scroll_to_latest()
            self.call_from_thread(_finish_card)

        def on_complete(full_reply: str, total_tokens: int, speed: float) -> None:
            def _finish():
                limit = getattr(self.config, "context_window", 8192)
                try:
                    telemetry = self.query_one("#telemetry-pane", TelemetryPane)
                    telemetry.update_metrics(total_tokens, limit, speed)
                except Exception:
                    pass
                self.is_busy = False
            self.call_from_thread(_finish)

        def on_error(err_msg: str) -> None:
            def _finish_err():
                if assistant_widget:
                    assistant_widget.append_token(f"\n\n**Error:** {err_msg}")
                self.is_busy = False
            self.call_from_thread(_finish_err)

        self.session.run_turn(
            user_text=user_text,
            on_token=on_token,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
            on_complete=on_complete,
            on_error=on_error,
        )


def launch_tui_app(config: LocaLLMConfig, client: Any, initial_theme: Optional[str] = None) -> None:
    """Entry point to execute the locaLLM reactive TUI application."""
    app = LocaLLMApp(config=config, client=client, initial_theme=initial_theme)
    app.run()
    # Unload VRAM and print farewell upon exit
    unloaded = getattr(app, "unloaded_count", 0)
    render_application_farewell(unloaded_count=unloaded)
