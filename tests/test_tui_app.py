"""Unit tests for locaLLM Textual TUI, theme styling, widgets, and app lifecycle."""

import unittest
from unittest.mock import MagicMock, patch
from locallm.config import LocaLLMConfig
from locallm.tui.app import LocaLLMApp
from locallm.tui.themes import (
    TUI_THEME_SPECS,
    build_app_tcss,
    get_tui_theme,
    list_tui_themes,
)
from locallm.tui.widgets import (
    ChatMessageWidget,
    ChatScrollContainer,
    LocaLLMHeader,
    PromptBox,
    TelemetryPane,
    ThemePickerModal,
    ThemeSwitcherWidget,
    ToolCardWidget,
    WorkspacePane,
)


class TestTuiThemeEngine(unittest.TestCase):
    """Test TCSS generator, palettes, and theme resolution."""

    def test_all_five_themes_defined(self):
        expected_keys = {"cyber_neon", "tokyo_night", "monokai", "matrix", "nordic_frost"}
        self.assertEqual(set(TUI_THEME_SPECS.keys()), expected_keys)
        for key in expected_keys:
            spec = TUI_THEME_SPECS[key]
            self.assertEqual(spec.key, key)
            self.assertTrue(spec.name)
            self.assertTrue(spec.primary.startswith("#"))
            self.assertTrue(spec.bg_screen.startswith("#"))
            self.assertTrue(spec.badge.startswith("⟦"))

    def test_get_tui_theme_valid_and_fallback(self):
        neon = get_tui_theme("cyber_neon")
        self.assertEqual(neon.key, "cyber_neon")

        matrix = get_tui_theme("  MATRIX  ")
        self.assertEqual(matrix.key, "matrix")

        fallback = get_tui_theme("invalid_theme_name")
        self.assertEqual(fallback.key, "cyber_neon")

    def test_list_tui_themes(self):
        themes = list_tui_themes()
        self.assertEqual(len(themes), 5)
        keys = [t[0] for t in themes]
        self.assertIn("cyber_neon", keys)
        self.assertIn("nordic_frost", keys)

    def test_build_app_tcss(self):
        tcss = build_app_tcss()
        self.assertIn("Screen", tcss)
        self.assertIn("#chat-scroll", tcss)
        for key in ("cyber_neon", "tokyo_night", "monokai", "matrix", "nordic_frost"):
            self.assertIn(f"Screen.theme-{key}", tcss)


class TestTuiWidgets(unittest.TestCase):
    """Test reactive widgets construction and state management."""

    def test_header_widget(self):
        header = LocaLLMHeader(model_name="qwen2.5-coder:7b", theme_badge="⟦⚡ CYBER⟧", is_online=True)
        self.assertEqual(header.model_name, "qwen2.5-coder:7b")
        self.assertEqual(header.backend_status, "ONLINE")
        self.assertIn("qwen2.5-coder:7b", header._render_title())
        self.assertIn("ONLINE", header._render_status())

    def test_tool_card_lifecycle(self):
        card = ToolCardWidget(tool_name="fetch_web", arguments={"url": "https://example.com"})
        self.assertEqual(card.status, "running")
        self.assertIn("fetch_web", card._render_header())

        card.complete(observation="HTTP 200 OK", success=True, duration=0.45)
        self.assertEqual(card.status, "completed")
        self.assertIn("✔ fetch_web (0.45s)", card._render_header())
        self.assertIn("HTTP 200 OK", card._render_details())

    def test_chat_message_widget(self):
        msg = ChatMessageWidget(role="user", header_text="▲ You", initial_content="Hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")

        msg.append_token(" world!")
        self.assertEqual(msg.content, "Hello world!")

    def test_telemetry_pane(self):
        telemetry = TelemetryPane(model_name="gemma4:12b", context_limit=8192)
        self.assertEqual(telemetry.model_name, "gemma4:12b")
        self.assertEqual(telemetry.context_limit, 8192)

        telemetry.update_metrics(context_tokens=2048, limit=8192, speed=42.5)
        self.assertEqual(telemetry.context_tokens, 2048)
        self.assertEqual(telemetry.speed_tok_s, 42.5)

    def test_workspace_pane(self):
        ws_pane = WorkspacePane(workspace_name="test_ws")
        self.assertEqual(ws_pane.workspace_name, "test_ws")

    def test_theme_switcher_widget(self):
        switcher = ThemeSwitcherWidget(active_theme="cyber_neon")
        self.assertEqual(switcher.active_theme, "cyber_neon")
        switcher.update_active_theme("matrix")
        self.assertEqual(switcher.active_theme, "matrix")


class TestTuiApp(unittest.TestCase):
    """Test LocaLLMApp construction, theme switching, and slash commands."""

    def setUp(self):
        self.config = LocaLLMConfig(
            default_model="test-model",
            ui_theme="tokyo_night",
            active_workspace="default",
        )
        self.mock_client = MagicMock()
        self.mock_client.is_connected.return_value = True
        self.mock_client.get_model_features.return_value = ["Tools"]

    def test_app_initialization(self):
        app = LocaLLMApp(config=self.config, client=self.mock_client)
        self.assertEqual(app.active_theme, "tokyo_night")
        self.assertIsNotNone(app.session)

    @patch("locallm.tui.app.save_config")
    def test_app_set_theme(self, mock_save):
        app = LocaLLMApp(config=self.config, client=self.mock_client, initial_theme="cyber_neon")
        self.assertEqual(app.active_theme, "cyber_neon")

        # Mock screen for headless testing
        app._screen = MagicMock()

        app.set_theme("matrix", persist=True)
        self.assertEqual(app.active_theme, "matrix")
        self.assertEqual(self.config.ui_theme, "matrix")
        mock_save.assert_called_once_with(self.config)

    @patch("locallm.tui.app.save_config")
    def test_app_slash_commands(self, mock_save):
        app = LocaLLMApp(config=self.config, client=self.mock_client)
        app._screen = MagicMock()
        app._add_message = MagicMock()

        # /theme command
        app._handle_slash_command("/theme monokai")
        self.assertEqual(app.active_theme, "monokai")

        # /stats command
        app._handle_slash_command("/stats")
        app._add_message.assert_called()

        # /model command
        app._handle_slash_command("/model")
        app._add_message.assert_called()

    def test_app_quit_action_unloads_vram(self):
        app = LocaLLMApp(config=self.config, client=self.mock_client)
        app.exit = MagicMock()
        app.action_quit_app()
        self.mock_client.unload_all_models.assert_called_with(fallback_model=self.config.default_model)
        app.exit.assert_called_once()

    def test_app_headless_mounting(self):
        import asyncio
        app = LocaLLMApp(config=self.config, client=self.mock_client)

        async def _run():
            async with app.run_test():
                self.assertIsNotNone(app.query_one("#header-container"))
                self.assertIsNotNone(app.query_one("#chat-scroll"))
                self.assertIsNotNone(app.query_one("#prompt-container"))
                self.assertIsNotNone(app.query_one("#workspace-pane"))
                self.assertIsNotNone(app.query_one("#main-app-tabs"))
                self.assertIsNotNone(app.query_one("#tab-assistant"))
                self.assertIsNotNone(app.query_one("#tab-workspaces"))
                self.assertIsNotNone(app.query_one("#tab-integrations"))
                self.assertIsNotNone(app.query_one("#tab-models"))
                self.assertIsNotNone(app.query_one("#tab-plugins"))
                self.assertIsNotNone(app.query_one("#tab-services"))
                self.assertIsNotNone(app.query_one("#tab-settings"))

                # Test tab navigation and view refreshing
                app.action_nav_tab("tab-models")
                m_view = app.query_one("#view-models")
                self.assertIsNotNone(m_view)

                app.action_nav_tab("tab-workspaces")
                w_view = app.query_one("#view-workspaces")
                self.assertIsNotNone(w_view)

                app.action_nav_tab("tab-plugins")
                p_view = app.query_one("#view-plugins")
                self.assertIsNotNone(p_view)

        asyncio.run(_run())

    def test_config_ui_mode_field(self):
        cfg = LocaLLMConfig()
        self.assertEqual(cfg.ui_mode, "classic")
        cfg_modern = LocaLLMConfig(ui_mode="modern")
        self.assertEqual(cfg_modern.ui_mode, "modern")


if __name__ == "__main__":
    unittest.main()
