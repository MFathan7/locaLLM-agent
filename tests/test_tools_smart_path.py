"""Unit tests for smart path resolution and web fetching tools."""

from pathlib import Path
import unittest
from locallm.core.tools import execute_tool, resolve_smart_path
from locallm.ui.chat_view import render_response_stats


class TestSmartPathAndTools(unittest.TestCase):
    """Test smart path mappings and new tool behaviors."""

    def test_resolve_cwd(self):
        resolved = resolve_smart_path(".")
        self.assertEqual(resolved, Path.cwd().resolve())

    def test_resolve_downloads_alias(self):
        resolved = resolve_smart_path("downloads")
        expected = (Path.home() / "Downloads").resolve()
        self.assertEqual(resolved, expected)

    def test_resolve_desktop_alias(self):
        resolved = resolve_smart_path("desktop")
        expected = (Path.home() / "Desktop").resolve()
        self.assertEqual(resolved, expected)

    def test_resolve_subpath_alias(self):
        resolved = resolve_smart_path("downloads/sample.pdf")
        expected = (Path.home() / "Downloads" / "sample.pdf").resolve()
        self.assertEqual(resolved, expected)

    def test_list_directory_downloads(self):
        # Should resolve cleanly without "Error: Path 'downloads' does not exist"
        result = execute_tool("list_directory", {"path": "downloads"})
        self.assertTrue(
            result.startswith("Directory contents of") or "Empty directory" in result,
            f"Unexpected output: {result[:100]}",
        )

    def test_fetch_web_invalid_url(self):
        result = execute_tool("fetch_web", {"url": "https://invalid.domain.that.does.not.exist.xyz"})
        self.assertTrue("Error" in result or "Unable" in result)

    def test_render_response_stats(self):
        stats = {
            "prompt_eval_count": 120,
            "eval_count": 45,
            "eval_duration": 1_000_000_000,  # 1 second
        }
        # Should run without error
        render_response_stats(stats)


if __name__ == "__main__":
    unittest.main()
