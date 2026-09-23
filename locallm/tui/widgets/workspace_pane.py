"""Active workspace browser and knowledge inspector widget for locaLLM TUI."""

from pathlib import Path
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static
from locallm.core.workspace import get_workspace_info, get_workspace_path


class WorkspacePane(Widget):
    """Sidebar widget presenting the active workspace files, knowledge documents, and skills."""

    DEFAULT_CSS = """
    WorkspacePane {
        height: auto;
        padding: 0 1;
    }
    """

    workspace_name: reactive[str] = reactive("default")

    def __init__(self, workspace_name: str = "default", **kwargs) -> None:
        super().__init__(**kwargs)
        self.workspace_name = workspace_name

    def compose(self) -> ComposeResult:
        with Vertical(classes="stat-box"):
            yield Label("ACTIVE WORKSPACE", classes="stat-title")
            yield Label(f"• Name: {self.workspace_name}", id="ws-name-lbl", classes="stat-row")
            yield Label("• Path: Loading...", id="ws-path-lbl", classes="stat-row")
            yield Label("• Assets: Loading...", id="ws-assets-lbl", classes="stat-row")

        with Vertical(classes="stat-box"):
            yield Label("WORKSPACE DIRECTORY TREE", classes="stat-title")
            yield Static("Scanning workspace...", id="ws-file-list")

    def on_mount(self) -> None:
        self.refresh_workspace()

    def update_workspace(self, name: str) -> None:
        """Switch workspace and refresh metadata."""
        self.workspace_name = name
        self.refresh_workspace()

    def refresh_workspace(self) -> None:
        """Inspect workspace folder on disk and update UI listings."""
        try:
            info = get_workspace_info(self.workspace_name)
            ws_path = get_workspace_path(self.workspace_name)

            self.query_one("#ws-name-lbl", Label).update(f"• Name: {self.workspace_name}")
            self.query_one("#ws-path-lbl", Label).update(f"• Path: {ws_path}")

            k_count = len(info.get("knowledge_files", [])) if info and "knowledge_files" in info else (info.get("knowledge_count", 0) if info else 0)
            s_count = len(info.get("skill_files", [])) if info and "skill_files" in info else (info.get("skills_count", 0) if info else 0)
            self.query_one("#ws-assets-lbl", Label).update(f"• Knowledge Docs: {k_count}  • Skills: {s_count}")

            # Scan directory entries
            lines = []
            if ws_path.exists():
                for p in sorted(ws_path.rglob("*")):
                    if p.is_file() and not any(part.startswith(".") for part in p.parts):
                        rel = p.relative_to(ws_path)
                        size_kb = max(1, p.stat().st_size // 1024)
                        lines.append(f"📄 {rel} ({size_kb} KB)")
                        if len(lines) >= 12:
                            lines.append(f"... and more items")
                            break

            if not lines:
                tree_text = "[dim]Workspace is empty. Add skills or knowledge docs.[/]"
            else:
                tree_text = "\n".join(lines)

            self.query_one("#ws-file-list", Static).update(tree_text)
        except Exception:
            pass
