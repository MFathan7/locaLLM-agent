"""Unit tests for the TUI theme engine, palettes, VRAM gauge, and theme switcher."""

import unittest
from unittest.mock import MagicMock, patch
from locallm.config import LocaLLMConfig
from locallm.modules.settings import _switch_ui_theme
from locallm.ui.banner import format_vram_bar
from locallm.ui.theme import (
    THEME_DEFINITIONS,
    apply_active_theme,
    get_theme_palette,
    list_available_themes,
)


class TestThemeEngine(unittest.TestCase):
    """Test theme registry, color tokens, and VRAM visual gauge."""

    def test_theme_definitions_present(self):
        expected_keys = ["cyber_neon", "tokyo_night", "monokai", "matrix", "nordic_frost"]
        for key in expected_keys:
            self.assertIn(key, THEME_DEFINITIONS)
            palette = THEME_DEFINITIONS[key]
            self.assertEqual(palette.key, key)
            self.assertTrue(palette.primary.startswith("#"))
            self.assertTrue(palette.accent.startswith("#"))
            self.assertTrue(len(palette.border_style) > 0)
            self.assertTrue(len(palette.icon) > 0)
            self.assertIsNotNone(palette.box_style)
            self.assertTrue(len(palette.prompt_symbol) > 0)
            self.assertTrue(len(palette.user_prefix) > 0)
            self.assertTrue(len(palette.ai_prefix) > 0)
            self.assertTrue(len(palette.badge) > 0)

    def test_render_chat_welcome_card(self):
        from locallm.ui.chat_view import render_chat_welcome_card
        cfg = LocaLLMConfig()
        # Should execute cleanly without error
        render_chat_welcome_card(cfg, model_name="gemma4:12b", features=["Tools", "Vision"])


    def test_get_theme_palette_valid_and_fallback(self):
        # Valid key
        pal = get_theme_palette("tokyo_night")
        self.assertEqual(pal.name, "Tokyo Night")

        # Case insensitive & whitespace
        pal2 = get_theme_palette("  CYBER_NEON  ")
        self.assertEqual(pal2.name, "Cyber Neon")

        # Fallback to default
        pal_fallback = get_theme_palette("nonexistent_theme")
        self.assertEqual(pal_fallback.key, "cyber_neon")

    def test_list_available_themes(self):
        themes = list_available_themes()
        self.assertEqual(len(themes), 5)
        keys = [t[0] for t in themes]
        self.assertIn("cyber_neon", keys)
        self.assertIn("matrix", keys)

    def test_format_vram_bar(self):
        # Zero / invalid total
        self.assertEqual(format_vram_bar(0.0, 0.0), "[dim]N/A[/]")

        # Normal low usage (< 70%) -> green
        bar_low = format_vram_bar(2.0, 10.0, width=10)
        self.assertIn("bold green", bar_low)
        self.assertIn("2.0/10.0 GB (20%)", bar_low)
        self.assertIn("██░░░░░░░░", bar_low)

        # Medium usage (70% - 90%) -> yellow
        bar_med = format_vram_bar(8.0, 10.0, width=10)
        self.assertIn("bold yellow", bar_med)
        self.assertIn("8.0/10.0 GB (80%)", bar_med)

        # High usage (>= 90%) -> red
        bar_high = format_vram_bar(9.5, 10.0, width=10)
        self.assertIn("bold red", bar_high)
        self.assertIn("9.5/10.0 GB (95%)", bar_high)

    def test_apply_active_theme(self):
        apply_active_theme("matrix")
        pal = get_theme_palette()
        self.assertEqual(pal.key, "matrix")

        # Revert back to cyber_neon
        apply_active_theme("cyber_neon")
        pal_reverted = get_theme_palette()
        self.assertEqual(pal_reverted.key, "cyber_neon")

    def test_config_ui_theme_field(self):
        cfg = LocaLLMConfig()
        self.assertEqual(cfg.ui_theme, "cyber_neon")

        cfg_custom = LocaLLMConfig(ui_theme="monokai")
        self.assertEqual(cfg_custom.ui_theme, "monokai")

    @patch("questionary.select")
    @patch("locallm.modules.settings.save_config")
    def test_switch_ui_theme_menu(self, mock_save, mock_select):
        cfg = LocaLLMConfig(ui_theme="cyber_neon")

        # Simulate user choosing Nordic Frost
        mock_select.return_value.ask.return_value = "Nordic Frost (Clean Scandinavian aesthetic with arctic cyan and polar blue)"
        _switch_ui_theme(cfg)

        self.assertEqual(cfg.ui_theme, "nordic_frost")
        mock_save.assert_called_once_with(cfg)

        # Cleanup back to default
        apply_active_theme("cyber_neon")


if __name__ == "__main__":
    unittest.main()
