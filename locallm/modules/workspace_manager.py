"""Interactive TUI module for workspace management (isolated knowledge & skills)."""

import os
from pathlib import Path
import subprocess
import tempfile
from typing import Optional

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
    extract_selected_skills,
    get_workspace_info,
    inspect_github_skills,
    list_workspaces,
    update_workspace_instructions,
)
from locallm.ui.theme import QUESTIONARY_STYLE, console


def run_workspace_menu(config: LocaLLMConfig) -> None:
    """Platform workspace management submenu loop."""
    while True:
        active = getattr(config, "active_workspace", "default")
        choice = questionary.select(
            "Workspace Manager:",
            choices=[
                f"Switch Active Workspace (Current: {active})",
                "Edit Custom Instructions (workspace.json)",
                "Add Knowledge Document (Paste / Type)",
                "Install Skill from GitHub / URL",
                "Add Skill Manually (Paste / Type)",
                "Create Workspace",
                "Delete Workspace",
                "View Workspace Details",
                "Back",
            ],
            style=QUESTIONARY_STYLE,
        ).ask()

        if choice is None or choice == "Back":
            break

        if choice.startswith("Switch Active Workspace"):
            _switch_workspace(config)
        elif choice == "Edit Custom Instructions (workspace.json)":
            _edit_instructions_wizard(config)
        elif choice == "Add Knowledge Document (Paste / Type)":
            _add_knowledge_wizard(config)
        elif choice == "Install Skill from GitHub / URL":
            _install_skill_wizard(config)
        elif choice == "Add Skill Manually (Paste / Type)":
            _add_skill_wizard(config)
        elif choice == "Create Workspace":
            _create_workspace_wizard(config)
        elif choice == "Delete Workspace":
            _delete_workspace_wizard(config)
        elif choice == "View Workspace Details":
            _display_workspaces_table(config)
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()


def _display_workspaces_table(config: LocaLLMConfig) -> None:
    """Render Rich table of installed workspaces."""
    active = getattr(config, "active_workspace", "default")
    workspaces = list_workspaces()

    table = Table(
        title="Installed Workspaces",
        border_style="cyan",
        header_style="bold cyan",
    )
    table.add_column("Status", style="bold", width=8)
    table.add_column("Workspace Name", style="bold white")
    table.add_column("Knowledge", justify="center")
    table.add_column("Skills", justify="center")
    table.add_column("Description")

    for ws in workspaces:
        name = ws["name"]
        is_active = "[bold green]ACTIVE[/]" if name == active else "[dim]INACTIVE[/]"
        desc = ws["description"] or "[dim]No description[/]"
        k_count = f"{ws['knowledge_count']} file(s)"
        s_count = f"{ws['skills_count']} file(s)"

        table.add_row(is_active, name, k_count, s_count, desc)

    console.print()
    console.print(table)
    console.print(
        f"[#aaaaaa]Workspaces root folder:[/] [bold cyan]{workspaces[0]['path'] if workspaces else '~/.locallm/workspaces'}[/]\n"
    )


def _switch_workspace(config: LocaLLMConfig) -> None:
    """Prompt user to change the active workspace."""
    workspaces = list_workspaces()
    active = getattr(config, "active_workspace", "default")

    choices = [ws["name"] for ws in workspaces] + ["Back"]
    chosen = questionary.select(
        f"Select active workspace (Current: {active}):",
        choices=choices,
        style=QUESTIONARY_STYLE,
    ).ask()

    if chosen and chosen != "Back" and chosen != active:
        config.active_workspace = chosen
        save_config(config)
        console.print(f"[success]Active workspace switched to:[/] [bold cyan]{chosen}[/]\n")


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
            console.print(f"[success]Active workspace is now:[/] [bold cyan]{name}[/]")
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
        console.print("[warning]No deletable custom workspaces found. ('default' and active workspace cannot be deleted).[/]\n")
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
    """Prompt user for multiline text without suggesting Alt+Enter, enabling Ctrl+D and Esc+Enter."""
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


def _edit_in_external_editor(initial_content: str = "", suffix: str = ".md") -> Optional[str]:
    """Open initial_content in an external text editor (Notepad on Windows) and return saved content."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=suffix, delete=False) as tf:
        tf.write(initial_content)
        temp_path = tf.name

    editor = os.environ.get("EDITOR")
    if not editor:
        editor = "notepad.exe" if os.name == "nt" else "nano"

    try:
        console.print(f"[#aaaaaa]Opening external editor ({editor}). Save (Ctrl+S) and close the editor window when done...[/]")
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


def _edit_instructions_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to view and edit custom workspace instructions."""
    active = getattr(config, "active_workspace", "default")
    info = get_workspace_info(active)
    current_inst = info.get("custom_instructions", "") if info else ""

    console.print(f"\n[bold cyan]Custom Instructions for Active Workspace:[/] [bold green]{active}[/]")
    if current_inst:
        console.print(Panel(current_inst, border_style="cyan", title="Current Instructions"))
    else:
        console.print("[#aaaaaa]No custom instructions configured yet.[/]\n")

    method = questionary.select(
        "Select editing method:",
        choices=[
            "Paste or Type in Terminal",
            "Open in Notepad / External Editor",
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
    elif method == "Open in Notepad / External Editor":
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


def _add_knowledge_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to add a markdown or text document to knowledge/ directory."""
    active = getattr(config, "active_workspace", "default")
    console.print(f"\n[bold cyan]Add Knowledge Document to Workspace:[/] [bold green]{active}[/]")

    method = questionary.select(
        "Select document input method:",
        choices=[
            "Paste or Type in Terminal",
            "Import from Local File (e.g. ./README.md)",
            "Open in Notepad / External Editor",
            "Cancel",
        ],
        style=QUESTIONARY_STYLE,
    ).ask()

    if not method or method == "Cancel":
        return

    doc_name = ""
    content: Optional[str] = None

    if method == "Import from Local File (e.g. ./README.md)":
        file_path_str = questionary.text(
            "Enter local file path to import (e.g. ./README.md or C:\\docs\\api.md):",
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

    elif method == "Open in Notepad / External Editor":
        doc_name = questionary.text(
            "Enter document title or filename (e.g. company_faq, product_spec):",
            style=QUESTIONARY_STYLE,
        ).ask()
        if not doc_name or not doc_name.strip():
            return
        doc_name = doc_name.strip()
        content = _edit_in_external_editor()
        if content is None:
            questionary.text("Press Enter to return...", style=QUESTIONARY_STYLE).ask()
            return

    elif method == "Paste or Type in Terminal":
        doc_name = questionary.text(
            "Enter document title or filename (e.g. company_faq, product_spec):",
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


def _add_skill_wizard(config: LocaLLMConfig) -> None:
    """Prompt user to add a manual skill file to skills/ directory."""
    active = getattr(config, "active_workspace", "default")
    console.print(f"\n[bold cyan]Add Skill Manually to Workspace:[/] [bold green]{active}[/]")

    method = questionary.select(
        "Select skill input method:",
        choices=[
            "Paste or Type in Terminal",
            "Import from Local File (e.g. ./SKILL.md)",
            "Open in Notepad / External Editor",
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

    elif method == "Open in Notepad / External Editor":
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
    console.print(f"\n[bold cyan]Install Agent Skill from GitHub / URL into Workspace:[/] [bold green]{active}[/]")
    console.print("[#aaaaaa]Accepts: owner/repo, owner/repo/subpath, full GitHub URLs, or direct .zip links[/]\n")

    source = questionary.text(
        "Enter GitHub repo or URL:",
        style=QUESTIONARY_STYLE,
    ).ask()

    if not source or not source.strip():
        return

    clean_source = source.strip()
    console.print(f"[bold cyan]Fetching and inspecting source:[/] [#bbbbbb]{clean_source}[/]")

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
        console.print(f"\n[bold cyan]Found 1 skill:[/] [bold green]{skill_name}[/]")
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
        # Multi-skill repository (e.g. anti-slop)
        console.print(f"\n[bold cyan]Discovered {len(available)} available skills in repository.[/]")
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
