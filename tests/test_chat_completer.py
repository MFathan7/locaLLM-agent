"""Unit tests for prompt_toolkit ChatInputCompleter and AgentProgress."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from locallm.modules.assistant import _get_chat_bottom_toolbar
from locallm.ui.completer import ChatInputCompleter, SLASH_COMMANDS
from locallm.ui.spinner import AgentProgress, TaskTracker


class TestChatInputCompleter(unittest.TestCase):
    """Test suite for ChatInputCompleter slash commands and file autocompletion."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name)
        # Create sample files for autocompletion
        (self.workspace_path / "README.md").write_text("# Test Readme", encoding="utf-8")
        (self.workspace_path / "main.py").write_text("print('hello')", encoding="utf-8")
        src_dir = self.workspace_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("console.log('test')", encoding="utf-8")

        self.completer = ChatInputCompleter(workspace_dir=str(self.workspace_path))
        self.event = CompleteEvent()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_slash_command_all_suggestions(self):
        """Typing '/' should yield all registered slash commands."""
        doc = Document(text="/", cursor_position=1)
        completions = list(self.completer.get_completions(doc, self.event))
        command_texts = [c.text for c in completions]
        self.assertIn("/help", command_texts)
        self.assertIn("/top", command_texts)
        self.assertIn("/header", command_texts)
        self.assertIn("/model", command_texts)
        self.assertIn("/clear", command_texts)
        self.assertIn("/sessions", command_texts)
        self.assertEqual(len(completions), len(SLASH_COMMANDS))

    def test_slash_command_filtering(self):
        """Typing '/m' should filter only matching slash commands (e.g. /model)."""
        doc = Document(text="/m", cursor_position=2)
        completions = list(self.completer.get_completions(doc, self.event))
        command_texts = [c.text for c in completions]
        self.assertIn("/model", command_texts)
        self.assertNotIn("/help", command_texts)
        self.assertNotIn("/sessions", command_texts)

    def test_slash_command_meta_description(self):
        """Slash completions should contain non-empty display_meta descriptions."""
        doc = Document(text="/top", cursor_position=4)
        completions = list(self.completer.get_completions(doc, self.event))
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, "/top")
        self.assertTrue(len(completions[0].display_meta_text) > 0)

    def test_at_file_completion(self):
        """Typing '@' should autocomplete relative files from workspace."""
        doc = Document(text="@", cursor_position=1)
        completions = list(self.completer.get_completions(doc, self.event))
        completion_texts = [c.text for c in completions]
        self.assertTrue(any("README.md" in t for t in completion_texts))
        self.assertTrue(any("main.py" in t for t in completion_texts))

    def test_at_file_filtering(self):
        """Typing '@main' should filter to matching file names."""
        doc = Document(text="@main", cursor_position=5)
        completions = list(self.completer.get_completions(doc, self.event))
        completion_texts = [c.text for c in completions]
        self.assertIn("main.py", completion_texts)
        self.assertFalse(any("README.md" in t for t in completion_texts))

    def test_dot_slash_path_completion(self):
        """Typing './' should trigger path completion."""
        doc = Document(text="./", cursor_position=2)
        completions = list(self.completer.get_completions(doc, self.event))
        completion_texts = [c.text for c in completions]
        self.assertTrue(any("README.md" in t for t in completion_texts))

    def test_normal_text_no_completions(self):
        """Normal conversational text should not produce unprompted completions."""
        doc = Document(text="Can you explain quantum computing?", cursor_position=34)
        completions = list(self.completer.get_completions(doc, self.event))
        self.assertEqual(len(completions), 0)


class TestAgentProgress(unittest.TestCase):
    """Test suite for AgentProgress in-place status line manager."""

    def test_agent_progress_lifecycle(self):
        prog = AgentProgress(initial_text="locaLLM is thinking...")
        self.assertEqual(prog.current_text, "locaLLM is thinking...")

        with prog:
            prog.update("Searching web: python...")
            self.assertEqual(prog.current_text, "Searching web: python...")
            prog.add_completed_task("  [bold green]✔[/] Searched web: python (5 results)")
            self.assertEqual(len(prog.completed_tasks), 1)
            prog.pause()
            prog.resume()
            prog.update("Reading: main.py...")
            self.assertEqual(prog.current_text, "Reading: main.py...")
            prog.add_completed_task("  [bold green]✔[/] Read file: main.py (10 lines)")
            self.assertEqual(len(prog.completed_tasks), 2)
            group = prog._render()
            self.assertEqual(len(group.renderables), 3)


class TestTaskTracker(unittest.TestCase):
    """Test suite for TaskTracker completed tasks display and erasure manager."""

    def test_task_tracker_print_and_clear(self):
        from rich.console import Console
        import io
        buf = io.StringIO()
        mock_console = Console(file=buf, force_terminal=True, width=80)
        tracker = TaskTracker(mock_console)

        tracker.print_task("[bold green]✔[/] Searched Web: python")
        self.assertEqual(len(tracker.completed_tasks), 1)
        self.assertGreater(tracker.total_lines, 0)

        tracker.print_task("[bold green]✔[/] Fetched Web: https://python.org")
        self.assertEqual(len(tracker.completed_tasks), 2)
        self.assertEqual(tracker.total_lines, 2)

        tracker.clear()
        self.assertEqual(tracker.total_lines, 0)


class TestChatBottomToolbar(unittest.TestCase):
    """Test suite for dynamic chat bottom toolbar."""

    @patch("locallm.core.hardware.get_gpu_info")
    @patch("psutil.virtual_memory")
    def test_bottom_toolbar_rendering(self, mock_mem, mock_gpu):
        mock_gpu_inst = MagicMock()
        mock_gpu_inst.used_vram_mb = 4096
        mock_gpu_inst.total_vram_mb = 8192
        mock_gpu.return_value = mock_gpu_inst

        mock_vm = MagicMock()
        mock_vm.total = 16 * (1024**3)
        mock_vm.available = 8 * (1024**3)
        mock_mem.return_value = mock_vm

        toolbar_func = _get_chat_bottom_toolbar("my-workspace")
        result = toolbar_func()
        self.assertIn("VRAM: 4.0/8.0G", result)
        self.assertIn("RAM: 8.0/16.0G", result)
        self.assertIn("ws:my-workspace", result)


if __name__ == "__main__":
    unittest.main()
