"""Interactive TUI module for workspace management (isolated knowledge & skills)."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from prompt_toolkit.key_binding import KeyBindings
import questionary
from rich.panel import Panel
from rich.table import Table
from locallm.config import LocaLLMConfig, save_config
from locallm.core.workspace import (
    add_workspace_document,
    add_workspace_skill,
    create_workspace,
    delete_workspace,
    delete_workspace_skill,
    ensure_default_workspace,
    extract_selected_skills,
    get_workspace_agents_path,
    get_workspace_info,
    get_workspace_path,
    inspect_github_skills,
    list_workspaces,
    update_workspace_instructions,
)
from locallm.ui.theme import QUESTIONARY_STYLE, console, get_theme_palette


def run_workspace_menu(config: LocaLLMConfig) -> None:
    """Platform workspace management interactive menu loop."""
    while True:
        console.clear()
        _render_workspace_overview(config)

        choice = questionary.select(
            "Workspace Options:",
            choices=[
                "Switch Workspace",
                "Knowledge Documents",
                "Skills",
                "Persona & Directives",
                "Create Workspace",
                "Delete Workspace",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Switch Workspace":
            _switch_workspace(config)
        elif choice == "Knowledge Documents":
            _manage_knowledge_menu(config)
        elif choice == "Skills":
            _manage_skills_menu(config)
        elif choice == "Persona & Directives":
            _manage_persona_menu(config)
        elif choice == "Create Workspace":
            _create_workspace_wizard(config)
        elif choice == "Delete Workspace":
            _delete_workspace_wizard(config)


def _render_workspace_overview(config: LocaLLMConfig) -> None:
    """Render a clean, high-contrast dashboard table and summary of all workspaces."""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    active = getattr(config, "active_workspace", "default")
    workspaces = list_workspaces()

    table = Table(
        title=f"⟦{palette.icon} WORKSPACES DASHBOARD⟧",
        border_style=palette.border_style,
        header_style=f"bold {palette.primary}",
        box=palette.box_style,
        expand=True,
    )
    table.add_column("Status", style="bold", width=12)
    table.add_column("Workspace Name", style=f"bold {palette.primary}", width=20)
    table.add_column("Knowledge", justify="center", width=14)
    table.add_column("Skills", justify="center", width=12)
    table.add_column("Description")

    for ws in workspaces:
        name = ws["name"]
        is_active = f"[bold {palette.success}]● ACTIVE[/]" if name == active else "[#aaaaaa]INACTIVE[/]"
        desc = ws["description"] or "[dim]General-purpose workspace[/]"
        k_count = f"{ws['knowledge_count']} doc(s)"
        s_count = f"{ws['skills_count']} skill(s)"
        table.add_row(is_active, name, k_count, s_count, desc)

    console.print(table)

    active_info = get_workspace_info(active)
    active_path = active_info.get("path", "") if active_info else str(get_workspace_path(active))
    agents_path = get_workspace_agents_path(active)
    has_agents = agents_path.is_file()
    agents_status = f"[bold {palette.success}]Configured ({agents_path.name})[/]" if has_agents else "[#aaaaaa]Default[/]"

    summary_text = (
        f"[bold white]Active Workspace:[/] [bold {palette.primary}]{active}[/]  •  "
        f"[bold white]Persona:[/] {agents_status}\n"
        f"[#aaaaaa]Folder:[/] [dim]{active_path}[/]"
    )
    console.print(Panel(summary_text, border_style=palette.border_style, box=palette.box_style))
    console.print()


def _switch_workspace(config: LocaLLMConfig) -> None:
    """Prompt user to change the active workspace."""
    workspaces = list_workspaces()
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    choices = [f"{ws['name']} (Active)" if ws["name"] == active else ws["name"] for ws in workspaces] + ["Back"]
    chosen = questionary.select(
        f"Select workspace to activate (Current: {active}):",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if chosen and chosen != "Back":
        clean_chosen = chosen.replace(" (Active)", "").strip()
        if clean_chosen != active:
            config.active_workspace = clean_chosen
            save_config(config)
            console.print(f"[success]Active workspace switched to:[/] [bold {palette.primary}]{clean_chosen}[/]\n")
            time.sleep(0.5)


def _manage_knowledge_menu(config: LocaLLMConfig) -> None:
    """Submenu for viewing, adding, and deleting knowledge documents in active workspace."""
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    while True:
        console.clear()
        ws_path = get_workspace_path(active)
        k_dir = ws_path / "knowledge"
        k_dir.mkdir(parents=True, exist_ok=True)
        docs = sorted([f for f in k_dir.glob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")], key=lambda x: x.name.lower())

        table = Table(
            title=f"⟦Knowledge Documents • Workspace: {active}⟧",
            border_style=palette.border_style,
            header_style=f"bold {palette.primary}",
            box=palette.box_style,
            expand=True,
        )
        table.add_column("#", justify="center", width=4)
        table.add_column("Document Filename", style=f"bold {palette.primary}", width=32)
        table.add_column("Size", justify="right", width=12)
        table.add_column("Path", style="dim")

        if docs:
            for idx, doc in enumerate(docs, 1):
                size_kb = doc.stat().st_size / 1024.0
                size_str = f"{size_kb:.1f} KB" if size_kb >= 1.0 else f"{doc.stat().st_size} B"
                table.add_row(str(idx), doc.name, size_str, str(doc))
        else:
            table.add_row("-", "[dim]No documents yet[/]", "-", f"[dim]Drop .md/.txt into {k_dir}[/]")

        console.print(table)
        console.print(f"[#aaaaaa]Reference documents are automatically injected into the AI context for workspace '{active}'.[/]\n")

        choices = [
            "Import from Local File",
            "Paste or Type in Terminal",
            "Open in External Editor",
        ]
        if docs:
            choices.append("Delete Document")
        choices.append("Back")

        choice = questionary.select(
            "Knowledge Options:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Import from Local File":
            _import_knowledge_file_wizard(active)
        elif choice == "Paste or Type in Terminal":
            _paste_knowledge_wizard(active)
        elif choice == "Open in External Editor":
            _editor_knowledge_wizard(active)
        elif choice == "Delete Document":
            _delete_knowledge_doc_wizard(active, docs)


def _manage_skills_menu(config: LocaLLMConfig) -> None:
    """Submenu for viewing, installing, and deleting skills in active workspace."""
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    while True:
        console.clear()
        ws_path = get_workspace_path(active)
        s_dir = ws_path / "skills"
        s_dir.mkdir(parents=True, exist_ok=True)
        items = sorted([f for f in s_dir.iterdir() if f.is_file() or f.is_dir()], key=lambda x: x.name.lower())

        table = Table(
            title=f"⟦Installed Skills • Workspace: {active}⟧",
            border_style=palette.border_style,
            header_style=f"bold {palette.primary}",
            box=palette.box_style,
            expand=True,
        )
        table.add_column("#", justify="center", width=4)
        table.add_column("Skill Name", style=f"bold {palette.primary}", width=28)
        table.add_column("Type", justify="center", width=12)
        table.add_column("Entrypoint / Path", style="dim")

        if items:
            for idx, item in enumerate(items, 1):
                item_type = "[bold cyan]Package[/]" if item.is_dir() else "[bold green]Markdown[/]"
                entry_str = f"{item.name}/SKILL.md" if item.is_dir() else item.name
                table.add_row(str(idx), item.name, item_type, entry_str)
        else:
            table.add_row("-", "[dim]No skills installed yet[/]", "-", "[dim]Install from GitHub or add manually[/]")

        console.print(table)
        console.print(f"[#aaaaaa]Agent skills provide specialized workflows and domain expertise to '{active}'.[/]\n")

        choices = [
            "Install Skill from GitHub / URL",
            "Add Skill Manually",
        ]
        if items:
            choices.append("Delete Skill(s)")
        choices.append("Back")

        choice = questionary.select(
            "Skills Options:",
            choices=choices,
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Install Skill from GitHub / URL":
            _install_skill_wizard(config)
        elif choice == "Add Skill Manually":
            _add_skill_wizard(config)
        elif choice in ("Delete Skill", "Delete Skill(s)"):
            _delete_skill_wizard(active, items)


def _manage_persona_menu(config: LocaLLMConfig) -> None:
    """Submenu for viewing and editing persona directives (AGENTS.md) and custom instructions."""
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    while True:
        console.clear()
        agents_path = get_workspace_agents_path(active)
        info = get_workspace_info(active)
        instructions = info.get("custom_instructions", "") if info else ""

        agents_preview = "[dim]No AGENTS.md file found (using built-in default)[/]"
        if agents_path.is_file():
            try:
                raw_text = agents_path.read_text(encoding="utf-8", errors="replace").strip()
                agents_preview = (raw_text[:600] + "\n... [Full file available in editor]") if len(raw_text) > 600 else raw_text
            except Exception:
                agents_preview = "[danger]Failed to read AGENTS.md[/]"

        inst_preview = instructions if instructions else "[dim]No custom instructions configured[/]"

        console.print(Panel(
            agents_preview,
            title=f"[bold {palette.primary}]⟦Persona & Directives: {agents_path.name}⟧[/]",
            border_style=palette.border_style,
            box=palette.box_style,
        ))
        console.print(Panel(
            inst_preview,
            title=f"[bold {palette.accent}]⟦Custom Workspace Instructions (workspace.json)⟧[/]",
            border_style=palette.border_style,
            box=palette.box_style,
        ))
        console.print()

        choice = questionary.select(
            "Persona & Directives Options:",
            choices=[
                "Edit Persona (AGENTS.md)",
                "Edit Custom Instructions",
                "Reset Persona to Default",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice == "Edit Persona (AGENTS.md)":
            _edit_agents_wizard(config)
        elif choice == "Edit Custom Instructions":
            _edit_instructions_wizard(config)
        elif choice == "Reset Persona to Default":
            _reset_agents_persona(active, agents_path)


def _reset_agents_persona(active: str, agents_path: Path) -> None:
    """Reset the active workspace persona to the canonical default template."""
    confirm = questionary.confirm(
        f"Reset {agents_path.name} in workspace '{active}' to default persona?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()
    if confirm:
        from locallm.core.workspace import DEFAULT_WORKSPACE_AGENTS_MD
        try:
            agents_path.write_text(DEFAULT_WORKSPACE_AGENTS_MD, encoding="utf-8")
            console.print(f"[success]{agents_path.name} reset to default template successfully.[/]\n")
        except Exception as exc:
            console.print(f"[danger]Failed to reset persona: {exc}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _import_knowledge_file_wizard(active: str) -> None:
    """Import an existing file into the active workspace knowledge folder."""
    file_path_str = questionary.text(
        "Enter local file path to import (e.g. ./README.md or /path/to/doc.md):",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not file_path_str or not file_path_str.strip():
        return

    local_path = Path(file_path_str.strip().strip('"').strip("'"))
    if not local_path.exists() or not local_path.is_file():
        console.print(f"[danger]File '{local_path}' does not exist or is not a file.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    try:
        content = local_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        console.print(f"[danger]Failed to read file: {exc}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    doc_name = local_path.name
    custom_name = questionary.text(
        f"Save in workspace as filename (default: {doc_name}):",
        default=doc_name,
        style=QUESTIONARY_STYLE,
    ).ask()
    if custom_name and custom_name.strip():
        doc_name = custom_name.strip()

    ok, msg = add_workspace_document(active, doc_name, content)
    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _paste_knowledge_wizard(active: str) -> None:
    """Paste or type text into a new knowledge document."""
    doc_name = questionary.text(
        "Enter document title or filename (e.g. architecture_guide, api_spec):",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not doc_name or not doc_name.strip():
        return

    doc_name = doc_name.strip()
    console.print("[#aaaaaa]Paste or type document content below. Press Esc then Enter, or Ctrl+D to submit:[/]")
    content = _prompt_multiline_text("Document Content:")

    if not content or not content.strip():
        console.print("[warning]Empty document content. Aborted.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    ok, msg = add_workspace_document(active, doc_name, content)
    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _editor_knowledge_wizard(active: str) -> None:
    """Create and edit a knowledge document using an external text editor."""
    doc_name = questionary.text(
        "Enter document title or filename (e.g. system_runbook):",
        style=QUESTIONARY_STYLE,
    ).ask()
    if not doc_name or not doc_name.strip():
        return

    doc_name = doc_name.strip()
    content = _edit_in_external_editor()
    if content is None or not content.strip():
        console.print("[warning]No content saved. Aborted.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    ok, msg = add_workspace_document(active, doc_name, content)
    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")
    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _delete_knowledge_doc_wizard(active: str, docs: List[Path]) -> None:
    """Prompt user to select and delete a knowledge document from disk."""
    if not docs:
        console.print("[warning]No documents available to delete.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    choices = [doc.name for doc in docs] + ["Cancel"]
    chosen = questionary.select(
        "Select document to delete permanently:",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    confirm = questionary.confirm(
        f"Permanently delete document '{chosen}' from workspace '{active}'?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if confirm:
        ws_path = get_workspace_path(active)
        target = ws_path / "knowledge" / chosen
        try:
            target.unlink()
            console.print(f"[success]Document '{chosen}' deleted successfully.[/]\n")
        except Exception as exc:
            console.print(f"[danger]Failed to delete document: {exc}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _delete_skill_wizard(active: str, items: List[Path]) -> None:
    """Prompt user to multi-select and delete installed skills from disk."""
    if not items:
        console.print("[warning]No skills available to delete.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    console.print(f"\n[#aaaaaa]Select skill(s) to permanently delete from '[bold cyan]{active}[/]' (Space to toggle, Enter to confirm):[/]\n")

    skill_choices = [item.name for item in items]
    chosen = questionary.checkbox(
        "Select skills to delete permanently:",
        choices=skill_choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen:
        console.print("[#aaaaaa]No skills selected. Deletion cancelled.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    if len(chosen) == 1:
        confirm_prompt = f"Permanently delete skill '{chosen[0]}' from workspace '{active}'?"
    else:
        confirm_prompt = f"Permanently delete {len(chosen)} skills ({', '.join(chosen)}) from workspace '{active}'?"

    confirm = questionary.confirm(
        confirm_prompt,
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if confirm:
        deleted_count = 0
        error_msgs = []
        for skill_name in chosen:
            ok, msg = delete_workspace_skill(active, skill_name)
            if ok:
                deleted_count += 1
            else:
                error_msgs.append(msg)

        if deleted_count > 0:
            console.print(f"[success]Successfully deleted {deleted_count} skill(s) from workspace '{active}'.[/]\n")
        if error_msgs:
            for em in error_msgs:
                console.print(f"[danger]{em}[/]")
            console.print()
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _create_workspace_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to create a new workspace."""
    name = questionary.text(
        "Enter new workspace name (letters, numbers, hyphens):",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not name or not name.strip():
        return

    name = name.strip()
    desc = questionary.text(
        "Enter workspace description (optional):",
        style=QUESTIONARY_STYLE,
    ).ask() or ""

    custom_prompt = questionary.text(
        "Enter custom workspace instructions (optional):",
        style=QUESTIONARY_STYLE,
    ).ask() or ""

    ok, msg = create_workspace(name, description=desc, custom_instructions=custom_prompt)
    if ok:
        console.print(f"[success]{msg}[/]")
        switch_now = questionary.confirm(
            f"Switch to '{name}' as active workspace now?",
            default=True,
            style=QUESTIONARY_STYLE,
        ).ask()
        if switch_now:
            config.active_workspace = name
            save_config(config)
            palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
            console.print(f"[success]Active workspace is now:[/] [bold {palette.primary}]{name}[/]")
        console.print()
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
    else:
        console.print(f"[danger]{msg}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _delete_workspace_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to select and delete an inactive custom workspace."""
    workspaces = list_workspaces()
    active = getattr(config, "active_workspace", "default")

    # Filter out default and currently active workspace
    deletable = [ws["name"] for ws in workspaces if ws["name"] != "default" and ws["name"] != active]

    if not deletable:
        console.print("[warning]No deletable custom workspaces found. ('default' and the active workspace cannot be deleted).[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    chosen = questionary.select(
        "Choose workspace to delete:",
        choices=deletable + ["Cancel"],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not chosen or chosen == "Cancel":
        return

    confirm = questionary.confirm(
        f"Are you sure you want to permanently delete workspace '{chosen}' and all its knowledge files?",
        default=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    if confirm:
        ok, msg = delete_workspace(chosen, active)
        if ok:
            console.print(f"[success]{msg}[/]\n")
        else:
            console.print(f"[danger]{msg}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _prompt_multiline_text(message: str, default: str = "") -> Optional[str]:
    """Prompt user for multiline text, enabling Ctrl+D and Esc+Enter."""
    kb = KeyBindings()

    @kb.add("c-d")
    def _accept_ctrl_d(event):
        event.current_buffer.validate_and_handle()

    try:
        return questionary.text(
            message,
            default=default,
            multiline=True,
            instruction="(Press 'Esc then Enter' or 'Ctrl+D' to save/submit)\n>",
            key_bindings=kb,
            style=QUESTIONARY_STYLE,
        ).ask()
    except Exception:
        return questionary.text(
            message,
            default=default,
            multiline=True,
            instruction="(Press 'Esc then Enter' to save/submit)\n>",
            style=QUESTIONARY_STYLE,
        ).ask()


def _edit_in_external_editor(initial_content: str = "", filename_hint: str = "temp.md", suffix: str = ".md") -> Optional[str]:
    """Open initial_content in an external text editor and return saved content."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=suffix, delete=False) as tf:
        tf.write(initial_content)
        temp_path = tf.name

    editor = os.environ.get("EDITOR")
    if not editor:
        editor = "notepad.exe" if os.name == "nt" else "nano"

    try:
        console.print(f"[#aaaaaa]Opening external editor ({editor}). Save and close the editor when done...[/]")
        subprocess.run([editor, temp_path], check=True)
        with open(temp_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content
    except Exception as exc:
        console.print(f"[danger]Failed to open external editor: {exc}[/]")
        return None
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def _edit_agents_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to view and edit active workspace AGENTS.md / persona."""
    active = getattr(config, "active_workspace", "default")
    agents_path = get_workspace_agents_path(active)
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    current_text = ""
    if agents_path.is_file():
        try:
            current_text = agents_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            current_text = ""

    console.print(f"\n[bold {palette.primary}]Editing Persona for Active Workspace:[/] [bold {palette.success}]{active}[/]")
    console.print(f"[#aaaaaa]Target file:[/] [dim]{agents_path}[/]\n")

    method = questionary.select(
        "Select editing action:",
        choices=[
            "Open in External Editor",
            "Paste or Type in Terminal",
            "Reset to Default Persona",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not method or method == "Cancel":
        return

    new_text: Optional[str] = None
    if method == "Reset to Default Persona":
        from locallm.core.workspace import DEFAULT_WORKSPACE_AGENTS_MD
        new_text = DEFAULT_WORKSPACE_AGENTS_MD
    elif method == "Open in External Editor":
        new_text = _edit_in_external_editor(initial_content=current_text, filename_hint=agents_path.name)
    elif method == "Paste or Type in Terminal":
        console.print("[#aaaaaa]Type or paste markdown below. Press Esc then Enter, or Ctrl+D to submit:[/]")
        new_text = _prompt_multiline_text("Persona Markdown:", default=current_text)

    if new_text is not None:
        try:
            agents_path.write_text(new_text, encoding="utf-8")
            console.print(f"[success]Saved {len(new_text)} characters to {agents_path.name} successfully.[/]\n")
        except Exception as exc:
            console.print(f"[danger]Failed to save {agents_path.name}: {exc}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _edit_instructions_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to view and edit custom workspace instructions."""
    active = getattr(config, "active_workspace", "default")
    info = get_workspace_info(active)
    current_inst = info.get("custom_instructions", "") if info else ""
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))

    console.print(f"\n[bold {palette.primary}]Custom Instructions for Active Workspace:[/] [bold {palette.success}]{active}[/]")

    method = questionary.select(
        "Select editing method:",
        choices=[
            "Paste or Type in Terminal",
            "Open in External Editor",
            "Clear Instructions",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not method or method == "Cancel":
        return

    new_inst: Optional[str] = None
    if method == "Clear Instructions":
        new_inst = ""
    elif method == "Open in External Editor":
        new_inst = _edit_in_external_editor(initial_content=current_inst)
    elif method == "Paste or Type in Terminal":
        console.print("[#aaaaaa]Type or paste instructions below. Press Esc then Enter, or Ctrl+D to submit:[/]")
        new_inst = _prompt_multiline_text("Instructions:", default=current_inst)

    if new_inst is not None:
        ok, msg = update_workspace_instructions(active, new_inst)
        if ok:
            console.print(f"[success]{msg}[/]\n")
        else:
            console.print(f"[danger]{msg}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _add_skill_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to add a manual skill file to skills/ directory."""
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    console.print(f"\n[bold {palette.primary}]Add Skill Manually to Workspace:[/] [bold {palette.success}]{active}[/]")

    method = questionary.select(
        "Select skill input method:",
        choices=[
            "Paste or Type in Terminal",
            "Import from Local File (e.g. ./SKILL.md)",
            "Open in External Editor",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not method or method == "Cancel":
        return

    skill_name = ""
    content: Optional[str] = None

    if method == "Import from Local File (e.g. ./SKILL.md)":
        file_path_str = questionary.text(
            "Enter local file path to import:",
            style=QUESTIONARY_STYLE,
        ).ask()
        if not file_path_str or not file_path_str.strip():
            return
        local_path = Path(file_path_str.strip().strip('"').strip("'"))
        if not local_path.exists() or not local_path.is_file():
            console.print(f"[danger]File '{local_path}' does not exist or is not a file.[/]\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
            return
        try:
            content = local_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            console.print(f"[danger]Failed to read file: {exc}[/]\n")
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
            return
        skill_name = local_path.stem
        custom_name = questionary.text(
            f"Save skill name in workspace (default: {skill_name}):",
            default=skill_name,
            style=QUESTIONARY_STYLE,
        ).ask()
        if custom_name and custom_name.strip():
            skill_name = custom_name.strip()

    elif method == "Open in External Editor":
        skill_name = questionary.text(
            "Enter skill name (e.g. code_reviewer, security_auditor):",
            style=QUESTIONARY_STYLE,
        ).ask()
        if not skill_name or not skill_name.strip():
            return
        skill_name = skill_name.strip()
        content = _edit_in_external_editor()
        if content is None:
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
            return

    elif method == "Paste or Type in Terminal":
        skill_name = questionary.text(
            "Enter skill name (e.g. code_reviewer, security_auditor):",
            style=QUESTIONARY_STYLE,
        ).ask()
        if not skill_name or not skill_name.strip():
            return
        skill_name = skill_name.strip()
        console.print("[#aaaaaa]Paste or type skill instructions below. Press Esc then Enter, or Ctrl+D to submit:[/]")
        content = _prompt_multiline_text("Skill Instructions:")

    if not content or not content.strip():
        console.print("[warning]Empty skill content. Aborted.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    ok, msg = add_workspace_skill(active, skill_name, content)
    if ok:
        console.print(f"[success]{msg}[/]\n")
    else:
        console.print(f"[danger]{msg}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _install_skill_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to inspect and selectively install skills from GitHub repository or URL."""
    active = getattr(config, "active_workspace", "default")
    palette = get_theme_palette(getattr(config, "ui_theme", "cyber_neon"))
    console.print(f"\n[bold {palette.primary}]Install Agent Skill from GitHub / URL into Workspace:[/] [bold {palette.success}]{active}[/]")
    console.print("[#aaaaaa]Accepts: owner/repo, owner/repo/subpath, full GitHub URLs, or direct .zip links[/]\n")

    source = questionary.text(
        "Enter GitHub repo or URL:",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not source or not source.strip():
        return

    clean_source = source.strip()
    console.print(f"[bold {palette.accent}]Fetching and inspecting source:[/] [#bbbbbb]{clean_source}[/]")

    ok, msg, available, zip_bytes, target_subpath = inspect_github_skills(clean_source)
    if not ok:
        console.print(f"[danger]{msg}[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    if not available:
        console.print("[warning]No installable skills were discovered in this source.[/]\n")
        questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
        return

    if len(available) == 1:
        skill_name = available[0]
        console.print(f"\n[bold {palette.primary}]Found 1 skill:[/] [bold {palette.success}]{skill_name}[/]")
        confirm = questionary.confirm(
            f"Install skill '{skill_name}' into workspace '{active}'?",
            default=True,
            style=QUESTIONARY_STYLE,
        ).ask()

        if confirm:
            ext_ok, ext_msg = extract_selected_skills(
                active, zip_bytes, [skill_name], target_subpath=target_subpath
            )
            if ext_ok:
                console.print(f"[success]{ext_msg}[/]\n")
            else:
                console.print(f"[danger]{ext_msg}[/]\n")
        else:
            console.print("[#aaaaaa]Installation cancelled.[/]\n")

    else:
        console.print(f"\n[bold {palette.primary}]Discovered {len(available)} available skills in repository.[/]")
        console.print("[#aaaaaa]Select which skill(s) to install (Space to toggle, Enter to confirm):[/]\n")

        chosen = questionary.checkbox(
            "Select skills to extract:",
            choices=available,
            style=QUESTIONARY_STYLE,
        ).ask()

        if not chosen:
            console.print("[#aaaaaa]No skills selected. Installation cancelled.[/]\n")
        else:
            ext_ok, ext_msg = extract_selected_skills(
                active, zip_bytes, chosen, target_subpath=target_subpath
            )
            if ext_ok:
                console.print(f"[success]{ext_msg}[/]\n")
            else:
                console.print(f"[danger]{ext_msg}[/]\n")

    questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
