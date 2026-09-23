"""Interactive Workspaces Manager view for locaLLM TUI with real-time assets inspection."""

from pathlib import Path
from typing import Any, Dict, List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from locallm.config import LocaLLMConfig, save_config
from locallm.core.workspace import (
    create_workspace,
    delete_workspace,
    get_workspace_path,
    list_workspaces,
)


class WorkspaceChanged(Message):
    """Event posted when active workspace is changed."""

    def __init__(self, workspace_name: str) -> None:
        super().__init__()
        self.workspace_name = workspace_name


class WorkspacesView(Widget):
    """View managing isolated workspaces, personas, knowledge docs, and custom skills."""

    DEFAULT_CSS = """
    WorkspacesView {
        height: 100%;
        padding: 1 2;
    }

    #workspaces-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .ws-card {
        margin-bottom: 1;
        padding: 1;
        border: round #555555;
        height: auto;
    }

    .ws-card-active {
        border: round $primary;
    }

    .ws-actions-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .ws-actions-row Button {
        margin-right: 1;
    }

    #input-new-ws {
        width: 1fr;
        margin-right: 1;
    }

    #btn-create-ws {
        width: auto;
    }
    """

    def __init__(self, config: LocaLLMConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.workspaces: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="workspaces-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ ACTIVE WORKSPACE ✦", classes="stat-title")
                active_ws = getattr(self.config, "active_workspace", "default")
                yield Label(f"Current Workspace: [bold cyan]{active_ws}[/]", id="lbl-active-ws-title")
                yield Label(f"Path: [dim]{get_workspace_path(active_ws)}[/]", id="lbl-active-ws-path")
                with Horizontal(classes="ws-actions-row"):
                    yield Button("Refresh Workspaces", id="btn-refresh-ws", variant="default")

            with Vertical(classes="stat-box"):
                yield Label("CREATE NEW ISOLATED WORKSPACE", classes="stat-title")
                yield Label("Creates an isolated environment with zero-bleed memory and custom AGENTS.md persona:", classes="stat-row")
                with Horizontal(classes="ws-actions-row"):
                    yield Input(placeholder="e.g. frontend-team, data-science, sec-audit", id="input-new-ws")
                    yield Button("Create Workspace", id="btn-create-ws", variant="success")
                yield Label("", id="lbl-create-ws-status")

            with Vertical(classes="stat-box", id="all-workspaces-wrapper"):
                yield Label("ALL WORKSPACES", classes="stat-title")
                yield Vertical(id="workspaces-cards-box")

            with Vertical(classes="stat-box", id="active-ws-assets-wrapper"):
                yield Label("ACTIVE WORKSPACE KNOWLEDGE & SKILLS", classes="stat-title")
                yield Static("Inspecting workspace assets...", id="active-ws-assets-static")

    def on_mount(self) -> None:
        self.refresh_workspaces()

    def refresh_workspaces(self) -> None:
        """Scan ~/.locallm/workspaces, render workspace cards and active assets."""
        try:
            active_ws = getattr(self.config, "active_workspace", "default")
            try:
                self.query_one("#lbl-active-ws-title", Label).update(
                    f"Current Workspace: [bold cyan]{active_ws}[/]"
                )
                self.query_one("#lbl-active-ws-path", Label).update(
                    f"Path: [dim]{get_workspace_path(active_ws)}[/]"
                )
            except Exception:
                pass

            cards_box = self.query_one("#workspaces-cards-box", Vertical)
            cards_box.remove_children()

            self.workspaces = list_workspaces()

            if not self.workspaces:
                cards_box.mount(Label("[yellow]No workspaces found. Default workspace will be initialized.[/]"))
            else:
                for idx, w in enumerate(self.workspaces):
                    name = w["name"]
                    k_count = w.get("knowledge_count", 0)
                    s_count = w.get("skills_count", 0)
                    desc = w.get("description") or "Isolated workspace"
                    ws_dir = w.get("path", str(get_workspace_path(name)))

                    is_curr = (name.lower() == active_ws.lower())
                    card_classes = "ws-card ws-card-active" if is_curr else "ws-card"

                    actions = []
                    if is_curr:
                        actions.append(Button("Active Workspace", disabled=True, variant="default"))
                    else:
                        actions.append(Button("Switch Workspace", id=f"btn-ws-act---{idx}", variant="primary"))

                    if name != "default":
                        actions.append(Button("Delete", id=f"btn-ws-del---{idx}", variant="error"))

                    active_marker = "  [bold cyan]★ ACTIVE[/]" if is_curr else ""
                    card = Vertical(
                        Label(f"[bold cyan]{name}[/]{active_marker} - [dim]{desc}[/]", classes="stat-title"),
                        Label(f"• Path: [dim]{ws_dir}[/]\n• Knowledge Documents: [bold white]{k_count}[/]  • Custom Skills: [bold white]{s_count}[/]", classes="stat-row"),
                        Horizontal(*actions, classes="ws-actions-row"),
                        classes=card_classes,
                    )
                    cards_box.mount(card)

            # Update Active Workspace Assets breakdown
            ws_path = get_workspace_path(active_ws)
            asset_lines = []

            k_dir = ws_path / "knowledge"
            k_files = [f for f in k_dir.glob("*") if f.is_file()] if k_dir.exists() else []
            asset_lines.append(f"[bold cyan]Knowledge Documents ({len(k_files)}):[/]")
            if not k_files:
                asset_lines.append("  [dim](No documents in ./knowledge/ folder)[/]")
            else:
                for f in sorted(k_files, key=lambda p: p.name):
                    size_kb = max(1, f.stat().st_size // 1024)
                    asset_lines.append(f"  • [bold white]{f.name}[/] ({size_kb} KB)")

            s_dir = ws_path / "skills"
            s_dirs = [d for d in s_dir.iterdir() if d.is_dir() or d.name.endswith(".md")] if s_dir.exists() else []
            asset_lines.append(f"\n[bold cyan]Custom Skills ({len(s_dirs)}):[/]")
            if not s_dirs:
                asset_lines.append("  [dim](No skills in ./skills/ folder)[/]")
            else:
                for s in sorted(s_dirs, key=lambda p: p.name):
                    asset_lines.append(f"  • [bold green]{s.name}[/]")

            try:
                self.query_one("#active-ws-assets-static", Static).update("\n".join(asset_lines))
            except Exception:
                pass

        except Exception as ex:
            try:
                cards_box = self.query_one("#workspaces-cards-box", Vertical)
                cards_box.remove_children()
                cards_box.mount(Label(f"[bold red]Error loading workspaces: {ex}[/]"))
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-refresh-ws":
            self.refresh_workspaces()
        elif btn_id == "btn-create-ws":
            self._handle_create_ws()
        elif btn_id.startswith("btn-ws-act---"):
            idx_str = btn_id.replace("btn-ws-act---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.workspaces):
                    target = self.workspaces[idx]["name"]
                    self.config.active_workspace = target
                    save_config(self.config)
                    self.post_message(WorkspaceChanged(target))
                    self.refresh_workspaces()
            except Exception:
                pass
        elif btn_id.startswith("btn-ws-del---"):
            idx_str = btn_id.replace("btn-ws-del---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.workspaces):
                    target = self.workspaces[idx]["name"]
                    if target != "default":
                        delete_workspace(target)
                        if self.config.active_workspace == target:
                            self.config.active_workspace = "default"
                            save_config(self.config)
                            self.post_message(WorkspaceChanged("default"))
                        self.refresh_workspaces()
            except Exception:
                pass

    def _handle_create_ws(self) -> None:
        inp = self.query_one("#input-new-ws", Input)
        name = inp.value.strip()
        if not name:
            self.query_one("#lbl-create-ws-status", Label).update("[red]Workspace name cannot be empty.[/]")
            return

        try:
            create_workspace(name)
            inp.value = ""
            self.query_one("#lbl-create-ws-status", Label).update(f"[green]✔ Workspace '{name}' created successfully![/]")
            self.config.active_workspace = name
            save_config(self.config)
            self.post_message(WorkspaceChanged(name))
            self.refresh_workspaces()
        except Exception as ex:
            self.query_one("#lbl-create-ws-status", Label).update(f"[red]✖ Failed to create workspace: {ex}[/]")
