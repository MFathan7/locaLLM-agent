"""Intelligent, ultra-lightweight prompt_toolkit completers for locaLLM interactive chat."""

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

SLASH_COMMANDS: Dict[str, str] = {
    "/help": "Show command guide and keyboard shortcuts",
    "/top": "Launch live real-time VRAM & hardware telemetry HUD",
    "/header": "Refresh and display chat header & hardware telemetry",
    "/model": "Inspect active model, switch model, or toggle router",
    "/sessions": "List, resume, or manage workspace chat sessions",
    "/new": "Archive current chat and start a fresh session",
    "/clear": "Wipe current conversation history & reset memory",
    "/delete": "Delete active or saved chat session files",
    "/stats": "View session context tokens, speed & hardware stats",
    "/system": "View or dynamically edit the active system prompt",
    "/back": "Return to the main menu without terminating",
    "/exit": "Unload GPU VRAM and terminate session",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
}


def _get_project_files(workspace_dir: Optional[str] = None, max_files: int = 200) -> List[str]:
    """Retrieve relative file paths from workspace directory, ignoring heavy directories."""
    cwd = Path(workspace_dir).resolve() if workspace_dir else Path.cwd()
    collected: List[str] = []
    try:
        for root, dirs, files in os.walk(cwd):
            # Prune ignored directories in-place for fast traversal
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            rel_root = Path(root).relative_to(cwd)
            for f in files:
                if f.startswith("."):
                    continue
                rel_path = str(rel_root / f).replace("\\", "/")
                if rel_path.startswith("./"):
                    rel_path = rel_path[2:]
                collected.append(rel_path)
                if len(collected) >= max_files:
                    return collected
    except Exception:
        pass
    return collected


class ChatInputCompleter(Completer):
    """Unified completer handling slash commands and smart path suggestions."""

    def __init__(
        self,
        commands: Optional[Dict[str, str]] = None,
        workspace_dir: Optional[str] = None,
    ) -> None:
        self.commands = commands or SLASH_COMMANDS
        self.workspace_dir = workspace_dir
        self._cached_files: Optional[List[str]] = None

    def refresh_file_cache(self) -> None:
        """Force refresh of project files cache."""
        self._cached_files = None

    def _get_files(self) -> List[str]:
        if self._cached_files is None:
            self._cached_files = _get_project_files(workspace_dir=self.workspace_dir)
        return self._cached_files

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        # 1. Slash commands at the start of input or start of line
        stripped_line = text.lstrip()
        if stripped_line.startswith("/") and " " not in stripped_line:
            query = stripped_line.lower()
            for cmd, desc in self.commands.items():
                if cmd.lower().startswith(query) or query in cmd.lower():
                    # Calculate replacement start
                    start_pos = -len(query)
                    yield Completion(
                        text=cmd,
                        start_position=start_pos,
                        display=cmd,
                        display_meta=desc,
                    )
            return

        # 2. File mentions via '@' symbol (e.g. '@README' or '@locallm/')
        if "@" in word:
            at_idx = word.rfind("@")
            file_query = word[at_idx + 1 :].lower()
            start_pos = -len(file_query)
            files = self._get_files()
            count = 0
            for f in files:
                if file_query in f.lower():
                    yield Completion(
                        text=f,
                        start_position=start_pos,
                        display=f,
                        display_meta="File",
                    )
                    count += 1
                    if count >= 15:
                        break
            return

        # 3. Path completion via './' prefix
        if word.startswith("./"):
            path_query = word[2:].lower()
            start_pos = -len(path_query)
            files = self._get_files()
            count = 0
            for f in files:
                if path_query in f.lower():
                    yield Completion(
                        text=f,
                        start_position=start_pos,
                        display=f,
                        display_meta="Path",
                    )
                    count += 1
                    if count >= 15:
                        break
            return
