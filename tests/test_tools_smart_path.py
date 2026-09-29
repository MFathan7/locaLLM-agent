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

    def test_resolve_locallm_path_alias(self):
        resolved = resolve_smart_path(".locallm/workspaces/demo")
        expected = (Path.home() / ".locallm" / "workspaces" / "demo").resolve()
        self.assertEqual(resolved, expected)

    def test_workspace_skill_resolution_and_read_file(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            with patch("locallm.core.workspace.get_workspaces_dir", return_value=tmp_root):
                ws_dir = tmp_root / "test_ws"
                skill_dir = ws_dir / "skills" / "pentest" / "vuln-scanner"
                skill_dir.mkdir(parents=True)
                skill_file = skill_dir / "SKILL.md"
                skill_file.write_text("# Vuln Scanner\nAutonomous scanner steps.", encoding="utf-8")

                # 1. resolve_smart_path finds the nested skill in active workspace
                resolved = resolve_smart_path("vuln-scanner", workspace_name="test_ws")
                self.assertEqual(resolved, skill_file.resolve())

                # 2. execute_tool read_file automatically reads the resolved skill
                result = execute_tool("read_file", {"path": "vuln-scanner"}, workspace_name="test_ws")
                self.assertIn("Vuln Scanner", result)
                self.assertIn("Autonomous scanner steps", result)

                # 3. execute_tool read_skill loads the skill content
                skill_res = execute_tool("read_skill", {"skill_name": "vuln-scanner"}, workspace_name="test_ws")
                self.assertIn("Vuln Scanner", skill_res)


if __name__ == "__main__":
    unittest.main()
