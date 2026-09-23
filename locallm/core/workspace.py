"""Workspace management engine for isolated knowledge, skills, and session contexts."""

from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import httpx


DEFAULT_WORKSPACE_AGENTS_MD = """# locaLLM Agent Persona & Directives

You are locaLLM, an autonomous, highly capable, and disciplined local AI assistant.

## Core Identity & Tone
- Approach every task with precision, clarity, and technical pragmatism.
- Provide direct, succinct, and high-signal responses.
- Ground all responses in concrete facts; avoid conversational fluff and unnecessary apologies.
- Never output canned AI disclaimers such as "As an AI..." or "I am only a language model".

## Autonomous Execution Authority
- You have direct execution authority on the host system via native function-calling tools.
- When asked to create, edit, inspect, or execute files, directories, scripts, or system tasks:
  - NEVER instruct the user to create files or run terminal commands manually when tools can perform the action.
  - Directly invoke the appropriate tools (`create_directory`, `write_file`, `execute_command`, `read_file`, `list_directory`, `resolve_path`).
  - Read-Only vs Mutating Discipline: If the user only asks to find, locate, search, check, or report file paths, existence, or metadata, NEVER invoke `write_file`, `create_directory`, or modifying commands. Use `resolve_path`, `list_directory`, or `read_file` exclusively.

## Proactive Knowledge Discovery & Web Research
- Whenever the user inquires about a specific entity, software, vendor, product, protocol, acronym, or concept (e.g. niche enterprise tools, newly released libraries, obscure technical terms) that you do not have 100% complete and verified knowledge of, or when asked about real-time events, current news, recent developments, or weather:
  - NEVER state that you don't know, have no information, or lack real-time access.
  - NEVER hallucinate or speculate without verification.
  - You MUST PROACTIVELY invoke `search_web` on your first turn to research verified information before answering.

## Tool Observation Synthesis
- Never cite internal function names (e.g. `get_current_time`, `search_web`) or raw schema parameters to the user.
- Seamlessly synthesize tool observations and local environment context into natural, authoritative answers.
"""


def get_workspaces_dir() -> Path:
    """Return base directory for all workspaces (~/.locallm/workspaces)."""
    base = Path.home() / ".locallm" / "workspaces"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_workspace_path(name: str) -> Path:
    """Return path to a specific workspace directory."""
    clean_name = name.strip()
    return get_workspaces_dir() / clean_name


def get_workspace_agents_path(name: str) -> Path:
    """Return path to the AGENTS.md or SOUL.md file for a workspace."""
    ws_path = get_workspace_path(name)
    soul_file = ws_path / "SOUL.md"
    if soul_file.is_file():
        return soul_file
    return ws_path / "AGENTS.md"


def ensure_default_workspace() -> Path:
    """Initialize the default workspace if it does not already exist."""
    default_dir = get_workspace_path("default")
    if not default_dir.exists():
        default_dir.mkdir(parents=True, exist_ok=True)
        (default_dir / "knowledge").mkdir(exist_ok=True)
        (default_dir / "skills").mkdir(exist_ok=True)
        (default_dir / "sessions").mkdir(exist_ok=True)

        meta = {
            "name": "default",
            "description": "Default general-purpose workspace",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "custom_instructions": "",
        }
        with open(default_dir / "workspace.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        readme_content = (
            "# Default Workspace Knowledge\n\n"
            "Drop `.md` or `.txt` reference files in this folder.\n"
            "They will automatically be loaded into the AI assistant and agent context "
            "whenever the `default` workspace is active.\n"
        )
        (default_dir / "knowledge" / "README.md").write_text(readme_content, encoding="utf-8")

    # Ensure default workspace AGENTS.md is scaffolded
    agents_file = default_dir / "AGENTS.md"
    soul_file = default_dir / "SOUL.md"
    if not agents_file.exists() and not soul_file.exists():
        agents_file.write_text(DEFAULT_WORKSPACE_AGENTS_MD, encoding="utf-8")

    return default_dir


def list_workspaces() -> List[Dict[str, Any]]:
    """List all available workspaces with metadata and file counts."""
    ensure_default_workspace()
    base = get_workspaces_dir()
    results: List[Dict[str, Any]] = []

    for entry in sorted(base.iterdir(), key=lambda p: (p.name != "default", p.name.lower())):
        if not entry.is_dir():
            continue

        meta_file = entry / "workspace.json"
        meta: Dict[str, Any] = {}
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        knowledge_dir = entry / "knowledge"
        knowledge_count = len([f for f in knowledge_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")]) if knowledge_dir.exists() else 0

        skills_dir = entry / "skills"
        skills_count = len([f for f in skills_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")]) if skills_dir.exists() else 0

        results.append({
            "name": entry.name,
            "description": meta.get("description", ""),
            "custom_instructions": meta.get("custom_instructions", ""),
            "created_at": meta.get("created_at", ""),
            "knowledge_count": knowledge_count,
            "skills_count": skills_count,
            "path": str(entry.resolve()),
        })

    return results


def get_workspace_info(name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a single workspace by name."""
    ws_path = get_workspace_path(name)
    if not ws_path.exists() or not ws_path.is_dir():
        return None

    meta_file = ws_path / "workspace.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    knowledge_dir = ws_path / "knowledge"
    k_files = [str(f.relative_to(knowledge_dir)).replace("\\", "/") for f in knowledge_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")] if knowledge_dir.exists() else []

    skills_dir = ws_path / "skills"
    s_files = [str(f.relative_to(skills_dir)).replace("\\", "/") for f in skills_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")] if skills_dir.exists() else []

    return {
        "name": ws_path.name,
        "description": meta.get("description", ""),
        "custom_instructions": meta.get("custom_instructions", ""),
        "created_at": meta.get("created_at", ""),
        "knowledge_files": k_files,
        "skill_files": s_files,
        "path": str(ws_path.resolve()),
    }


def create_workspace(
    name: str,
    description: str = "",
    custom_instructions: str = "",
) -> Tuple[bool, str]:
    """Create a new isolated workspace with scaffolded directories."""
    clean_name = name.strip().lower()
    if not clean_name:
        return False, "Workspace name cannot be empty."

    # Validate name format: alphanumeric, hyphens, and underscores only
    if not re.match(r"^[a-zA-Z0-9_\-]+$", clean_name):
        return False, "Workspace name must contain only letters, numbers, hyphens, or underscores."

    ws_path = get_workspace_path(clean_name)
    if ws_path.exists():
        return False, f"Workspace '{clean_name}' already exists."

    try:
        ws_path.mkdir(parents=True, exist_ok=True)
        (ws_path / "knowledge").mkdir(exist_ok=True)
        (ws_path / "skills").mkdir(exist_ok=True)
        (ws_path / "sessions").mkdir(exist_ok=True)

        meta = {
            "name": clean_name,
            "description": description.strip(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "custom_instructions": custom_instructions.strip(),
        }
        with open(ws_path / "workspace.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Automatically scaffold workspace AGENTS.md
        agents_file = ws_path / "AGENTS.md"
        if not agents_file.exists():
            if custom_instructions.strip():
                initial_agents = f"{DEFAULT_WORKSPACE_AGENTS_MD}\n\n## Custom Workspace Directives\n{custom_instructions.strip()}\n"
            else:
                initial_agents = DEFAULT_WORKSPACE_AGENTS_MD
            agents_file.write_text(initial_agents, encoding="utf-8")

        return True, f"Workspace '{clean_name}' created successfully."
    except Exception as exc:
        return False, f"Failed to create workspace: {exc}"


def delete_workspace(name: str, active_workspace: str) -> Tuple[bool, str]:
    """Delete a workspace directory, preventing deletion of default or active workspace."""
    clean_name = name.strip().lower()
    if clean_name == "default":
        return False, "The 'default' workspace cannot be deleted."

    if clean_name == active_workspace.strip().lower():
        return False, f"Cannot delete '{clean_name}' because it is currently active. Switch to another workspace first."

    ws_path = get_workspace_path(clean_name)
    if not ws_path.exists() or not ws_path.is_dir():
        return False, f"Workspace '{clean_name}' does not exist."

    try:
        shutil.rmtree(ws_path)
        return True, f"Workspace '{clean_name}' deleted successfully."
    except Exception as exc:
        return False, f"Failed to delete workspace '{clean_name}': {exc}"


def load_workspace_context(name: str) -> str:
    """Load knowledge, skills, persona directives, and custom instructions for the workspace.

    Resolves AGENTS.md persona hierarchy with strict precedence:
    Active Workspace > Project CWD > Global (~/.locallm) > Default Template
    """
    clean_name = name.strip() if name else "default"
    ws_path = get_workspace_path(clean_name)

    # Fallback to default if specified workspace is absent
    if not ws_path.exists() or not ws_path.is_dir():
        ws_path = ensure_default_workspace()
        clean_name = "default"

    # Ensure physical AGENTS.md file exists on disk in workspace
    ws_agents_file = ws_path / "AGENTS.md"
    ws_soul_file = ws_path / "SOUL.md"
    if not ws_agents_file.exists() and not ws_soul_file.exists():
        try:
            ws_agents_file.write_text(DEFAULT_WORKSPACE_AGENTS_MD, encoding="utf-8")
        except Exception:
            pass

    sections: List[str] = []

    # 1. Resolve Persona & Cognitive Directives (AGENTS.md / SOUL.md)
    persona_text = ""
    persona_source = ""

    for cand_name in ["AGENTS.md", "SOUL.md", "agent.md"]:
        ws_cand = ws_path / cand_name
        if ws_cand.is_file():
            try:
                persona_text = ws_cand.read_text(encoding="utf-8", errors="replace").strip()
                if persona_text:
                    persona_source = f"Workspace: {clean_name}"
                    break
            except Exception:
                pass

    if not persona_text:
        global_dir = Path.home() / ".locallm"
        for cand_name in ["AGENTS.md", "SOUL.md"]:
            glob_cand = global_dir / cand_name
            if glob_cand.is_file():
                try:
                    persona_text = glob_cand.read_text(encoding="utf-8", errors="replace").strip()
                    if persona_text:
                        persona_source = "Global (~/.locallm)"
                        break
                except Exception:
                    pass

    if not persona_text:
        persona_text = DEFAULT_WORKSPACE_AGENTS_MD
        persona_source = "Default Directives"

    if persona_text:
        sections.append(f"[Persona & Cognitive Directives ({persona_source})]\n{persona_text}")

    # 2. Custom instructions from workspace.json (if distinct from AGENTS.md)
    meta_file = ws_path / "workspace.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                custom_inst = meta.get("custom_instructions", "").strip()
                if custom_inst and custom_inst not in persona_text:
                    sections.append(f"[Workspace Instructions]\n{custom_inst}")
        except Exception:
            pass

    # 3. Knowledge documents (.md, .txt) - Progressive disclosure (compact snippets)
    knowledge_dir = ws_path / "knowledge"
    if knowledge_dir.exists() and knowledge_dir.is_dir():
        k_entries: List[str] = []
        k_files = [f for f in knowledge_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")]
        for file in sorted(k_files, key=lambda p: str(p.relative_to(knowledge_dir)).lower()):
            try:
                content = file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    rel_name = str(file.relative_to(knowledge_dir)).replace("\\", "/")
                    snippet = content if len(content) <= 400 else (content[:400] + f"\n... [Use read_file('{rel_name}') for full document]")
                    k_entries.append(f"--- Document: {rel_name} ---\n{snippet}")
            except Exception:
                continue
        if k_entries:
            combined_k = "\n\n".join(k_entries)
            sections.append(f"[Workspace Knowledge Base]\n{combined_k[:3000]}")

    # 4. Agent Skills (.md, .txt) - Progressive disclosure (compact snippets)
    skills_dir = ws_path / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        s_entries: List[str] = []
        s_files = [f for f in skills_dir.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")]
        for file in sorted(s_files, key=lambda p: str(p.relative_to(skills_dir)).lower()):
            try:
                content = file.read_text(encoding="utf-8", errors="replace").strip()
                if content:
                    rel_name = str(file.relative_to(skills_dir)).replace("\\", "/")
                    snippet = content if len(content) <= 400 else (content[:400] + f"\n... [Use read_file('{rel_name}') for full skill instructions]")
                    s_entries.append(f"--- Skill: {rel_name} ---\n{snippet}")
            except Exception:
                continue
        if s_entries:
            combined_s = "\n\n".join(s_entries)
            sections.append(f"[Workspace Skills]\n{combined_s[:3000]}")

    # 5. Project Rules & Context from Current Working Directory (CWD)
    cwd = Path.cwd()
    project_rules_files = ["AGENTS.md", "CLAUDE.md", "agent.md", "rules.md"]
    for rf_name in project_rules_files:
            rule_file = cwd / rf_name
            if rule_file.is_file():
                try:
                    rule_text = rule_file.read_text(encoding="utf-8", errors="replace").strip()
                    if rule_text:
                        rule_snippet = rule_text if len(rule_text) <= 2000 else (rule_text[:2000] + f"\n... [Full project rules in {rf_name}]")
                        sections.append(f"[Project Architecture & Rules ({rf_name})]\n{rule_snippet}")
                        break
                except Exception:
                    pass

    # 5. Local Project Skills from CWD (.locallm/skills, .agents/skills, skills/)
    for local_skill_path in [cwd / ".locallm" / "skills", cwd / ".agents" / "skills", cwd / "skills"]:
        if local_skill_path.is_dir() and local_skill_path.resolve() != ws_path.resolve():
            local_s_files = [f for f in local_skill_path.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt")]
            if local_s_files:
                local_s_entries: List[str] = []
                for file in sorted(local_s_files, key=lambda p: str(p.relative_to(local_skill_path)).lower())[:10]:
                    try:
                        content = file.read_text(encoding="utf-8", errors="replace").strip()
                        if content:
                            rel_name = str(file.relative_to(local_skill_path)).replace("\\", "/")
                            snippet = content if len(content) <= 300 else (content[:300] + f"\n... [Use read_file('{rel_name}') for full instructions]")
                            local_s_entries.append(f"--- Local Skill: {rel_name} ---\n{snippet}")
                    except Exception:
                        continue
                if local_s_entries:
                    sections.append(f"[Local Project Skills]\n" + "\n\n".join(local_s_entries)[:2500])
                    break

    if not sections:
        return ""

    body = "\n\n".join(sections)
    return f"Active Workspace: '{clean_name}'\n{body}"


def get_all_available_skills(workspace_name: Optional[str] = "default") -> List[Dict[str, str]]:
    """Return list of all available skills across active workspace and current working directory."""
    skills: List[Dict[str, str]] = []
    seen_names = set()

    clean_name = workspace_name.strip() if workspace_name else "default"
    ws_skills_dir = get_workspace_path(clean_name) / "skills"
    if ws_skills_dir.is_dir():
        for file in sorted(ws_skills_dir.rglob("*")):
            if file.is_file() and file.suffix.lower() in (".md", ".txt"):
                skill_id = file.stem if file.name.lower() in ("skill.md", "readme.md") else file.name
                if file.parent != ws_skills_dir and file.name.lower() in ("skill.md", "readme.md"):
                    skill_id = file.parent.name
                if skill_id.lower() not in seen_names:
                    seen_names.add(skill_id.lower())
                    try:
                        first_lines = file.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                        desc = next((l.strip("#- ") for l in first_lines if l.strip() and not l.startswith("---")), "Workspace skill")
                    except Exception:
                        desc = "Workspace skill"
                    skills.append({
                        "name": skill_id,
                        "source": f"workspace:{clean_name}",
                        "path": str(file.resolve()),
                        "description": desc[:160],
                    })

    cwd = Path.cwd()
    for local_skill_path in [cwd / ".locallm" / "skills", cwd / ".agents" / "skills", cwd / "skills"]:
        if local_skill_path.is_dir():
            for file in sorted(local_skill_path.rglob("*")):
                if file.is_file() and file.suffix.lower() in (".md", ".txt"):
                    skill_id = file.stem if file.name.lower() in ("skill.md", "readme.md") else file.name
                    if file.parent != local_skill_path and file.name.lower() in ("skill.md", "readme.md"):
                        skill_id = file.parent.name
                    if skill_id.lower() not in seen_names:
                        seen_names.add(skill_id.lower())
                        try:
                            first_lines = file.read_text(encoding="utf-8", errors="replace").strip().splitlines()
                            desc = next((l.strip("#- ") for l in first_lines if l.strip() and not l.startswith("---")), "Project skill")
                        except Exception:
                            desc = "Project skill"
                        skills.append({
                            "name": skill_id,
                            "source": "local_project",
                            "path": str(file.resolve()),
                            "description": desc[:160],
                        })
    return skills


def get_skill_content(skill_name: str, workspace_name: Optional[str] = "default") -> Optional[str]:
    """Retrieve full text content for a skill by name from active workspace or project."""
    clean_target = skill_name.strip().lower()
    for s in get_all_available_skills(workspace_name):
        if s["name"].lower() == clean_target or clean_target in s["name"].lower():
            try:
                return Path(s["path"]).read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None
    return None


def sanitize_workspace_content(text: str) -> str:
    """Sanitize text input to repair UTF-16 surrogate pairs and strip lone surrogates.

    Terminal pastes on Windows often split emojis or symbols into UTF-16 surrogate code points.
    This function recombines valid surrogate pairs into proper Unicode characters and safely
    handles lone surrogates so saving to UTF-8 never throws UnicodeEncodeError.
    """
    if not text:
        return ""
    try:
        # Reconstruct valid surrogate pairs (e.g. \ud83d\ude00 -> 😀)
        text = text.encode("utf-16", "surrogatepass").decode("utf-16", "replace")
    except Exception:
        pass

    try:
        # Strip or replace any remaining unpaired lone surrogates
        text = text.encode("utf-8", "replace").decode("utf-8", "replace")
    except Exception:
        pass

    return text


def update_workspace_instructions(name: str, new_instructions: str) -> Tuple[bool, str]:
    """Update custom_instructions in workspace.json for the specified workspace."""
    clean_name = name.strip().lower()
    ws_path = get_workspace_path(clean_name)
    if not ws_path.exists() or not ws_path.is_dir():
        return False, f"Workspace '{clean_name}' does not exist."

    meta_file = ws_path / "workspace.json"
    meta: Dict[str, Any] = {}
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    meta["custom_instructions"] = sanitize_workspace_content(new_instructions).strip()
    try:
        with open(meta_file, "w", encoding="utf-8", errors="replace") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        return True, f"Custom instructions updated for workspace '{clean_name}'."
    except Exception as exc:
        return False, f"Failed to save custom instructions: {exc}"


def add_workspace_document(workspace_name: str, doc_name: str, content: str) -> Tuple[bool, str]:
    """Save a text or markdown knowledge document into the specified workspace's knowledge/ directory."""
    clean_ws = workspace_name.strip().lower()
    ws_path = get_workspace_path(clean_ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return False, f"Workspace '{clean_ws}' does not exist."

    clean_doc = doc_name.strip()
    if not clean_doc:
        return False, "Document name cannot be empty."

    # Remove dangerous traversal characters
    safe_name = os.path.basename(clean_doc.replace("\\", "/"))
    # Normalize extension: default to .md if no .md or .txt extension
    if not (safe_name.lower().endswith(".md") or safe_name.lower().endswith(".txt")):
        safe_name = f"{safe_name}.md"

    knowledge_dir = ws_path / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    target_file = knowledge_dir / safe_name

    try:
        clean_content = sanitize_workspace_content(content.strip())
        target_file.write_text(clean_content, encoding="utf-8", errors="replace")
        return True, f"Knowledge document '{safe_name}' saved to workspace '{clean_ws}'."
    except Exception as exc:
        return False, f"Failed to write document '{safe_name}': {exc}"


def add_workspace_skill(workspace_name: str, skill_name: str, content: str) -> Tuple[bool, str]:
    """Save a text or markdown skill file into the specified workspace's skills/ directory."""
    clean_ws = workspace_name.strip().lower()
    ws_path = get_workspace_path(clean_ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return False, f"Workspace '{clean_ws}' does not exist."

    clean_skill = skill_name.strip()
    if not clean_skill:
        return False, "Skill name cannot be empty."

    safe_name = os.path.basename(clean_skill.replace("\\", "/"))
    skills_base = ws_path / "skills"
    skills_base.mkdir(parents=True, exist_ok=True)

    if not (safe_name.lower().endswith(".md") or safe_name.lower().endswith(".txt")):
        skill_dir = skills_base / safe_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        target_file = skill_dir / "SKILL.md"
        display_name = f"{safe_name}/SKILL.md"
    else:
        target_file = skills_base / safe_name
        display_name = safe_name

    try:
        clean_content = sanitize_workspace_content(content.strip())
        target_file.write_text(clean_content, encoding="utf-8", errors="replace")
        return True, f"Skill '{display_name}' saved to workspace '{clean_ws}'."
    except Exception as exc:
        return False, f"Failed to write skill '{safe_name}': {exc}"


def parse_github_source(source: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parse owner, repo, branch, and subpath from a GitHub URL or shorthand.

    Returns:
        (owner, repo, branch, subpath)
    """
    clean = source.strip()

    # Pattern 1: https://github.com/owner/repo/tree/branch/subpath or https://github.com/owner/repo
    m = re.match(
        r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+)/(.*))?/?$",
        clean,
        re.IGNORECASE,
    )
    if m:
        owner = m.group(1)
        repo = m.group(2)
        branch = m.group(3)
        subpath = m.group(4).strip("/") if m.group(4) else None
        return owner, repo, branch, subpath

    # Pattern 2: owner/repo/tree/branch/subpath
    m2 = re.match(
        r"^([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+)/(.*))?/?$",
        clean,
    )
    if m2 and not clean.startswith("http://") and not clean.startswith("https://"):
        owner = m2.group(1)
        repo = m2.group(2)
        branch = m2.group(3)
        subpath = m2.group(4).strip("/") if m2.group(4) else None
        return owner, repo, branch, subpath

    # Pattern 3: owner/repo/subpath shorthand (e.g. anti-slop/anti-slop/skills/antislop-code)
    parts = clean.split("/")
    if len(parts) >= 3 and not clean.startswith("http://") and not clean.startswith("https://"):
        owner = parts[0]
        repo = parts[1]
        subpath = "/".join(parts[2:]).strip("/")
        return owner, repo, None, subpath

    # Pattern 4: owner/repo shorthand
    if len(parts) == 2 and not clean.startswith("http://") and not clean.startswith("https://"):
        return parts[0], parts[1].replace(".git", ""), None, None

    return None, None, None, None


def inspect_github_skills(source: str) -> Tuple[bool, str, List[str], bytes, Optional[str]]:
    """Inspect a GitHub repository or URL and discover available agent skills.

    Returns:
        (success, message, available_skills, zip_bytes, target_subpath)
    """
    clean_source = source.strip()
    if not clean_source:
        return False, "Source URL or repository cannot be empty.", [], b"", None

    # Check if direct raw markdown/txt URL
    if clean_source.lower().endswith(".md") or clean_source.lower().endswith(".txt") or "raw.githubusercontent.com" in clean_source.lower():
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(clean_source)
                if resp.status_code != 200:
                    return False, f"Failed to download raw skill file (HTTP {resp.status_code}).", [], b"", None

                raw_filename = clean_source.split("/")[-1].split("?")[0]
                if not raw_filename:
                    raw_filename = "SKILL.md"
                skill_name = raw_filename.rsplit(".", 1)[0]

                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    zf.writestr(f"{skill_name}/{raw_filename}", resp.content)
                return True, f"Found 1 file skill '{skill_name}'.", [skill_name], buf.getvalue(), None
        except Exception as exc:
            return False, f"Network error downloading skill: {exc}", [], b"", None

    # Check if direct ZIP URL
    if clean_source.lower().endswith(".zip") and (clean_source.startswith("http://") or clean_source.startswith("https://")):
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                resp = client.get(clean_source)
                if resp.status_code != 200:
                    return False, f"Failed to download zip archive (HTTP {resp.status_code}).", [], b"", None
                zip_bytes = resp.content
                target_subpath = None
                repo = "custom-skills"
        except Exception as exc:
            return False, f"Network error downloading zip: {exc}", [], b"", None
    else:
        owner, repo, branch, target_subpath = parse_github_source(clean_source)
        if not owner or not repo:
            return False, f"Invalid GitHub repository source format: '{clean_source}'. Expected 'owner/repo' or GitHub URL.", [], b"", None

        branches_to_try = [branch] if branch else ["main", "master"]
        zip_bytes = b""
        last_error = ""

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            for b in branches_to_try:
                zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{b}.zip"
                try:
                    resp = client.get(zip_url)
                    if resp.status_code == 200:
                        zip_bytes = resp.content
                        break
                    else:
                        last_error = f"HTTP {resp.status_code} for branch '{b}'"
                except Exception as exc:
                    last_error = str(exc)

        if not zip_bytes:
            return False, f"Failed to download repository '{owner}/{repo}': {last_error}", [], b"", None

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        names = zf.namelist()
    except Exception as exc:
        return False, f"Failed to read downloaded zip archive: {exc}", [], b"", None

    if not names:
        return False, "Downloaded repository archive is empty.", [], b"", None

    first_part = names[0].split("/")[0]
    prefix = ""
    if all(n.startswith(first_part + "/") or n == first_part for n in names if n):
        prefix = first_part + "/"

    # If target_subpath was specified (e.g. skills/antislop-code)
    if target_subpath:
        norm_sub = target_subpath.strip("/")
        sub_files = [
            n[len(prefix):] for n in names
            if n[len(prefix):].startswith(norm_sub + "/") or n[len(prefix):] == norm_sub
        ]
        if not sub_files:
            return False, f"Target subpath '{target_subpath}' not found in repository.", [], b"", None
        skill_name = norm_sub.split("/")[-1]
        return True, f"Found target skill '{skill_name}' at '{target_subpath}'.", [skill_name], zip_bytes, norm_sub

    discovered_skills: set = set()

    for n in names:
        rel = n[len(prefix):]
        if not rel or rel.endswith("/"):
            continue

        parts = rel.split("/")
        if any(
            p.startswith(".")
            or p.startswith("_")
            or p.lower() in ("tests", "test", "node_modules", "dist", "build", "assets", "images", "img")
            for p in parts
        ):
            continue

        # Look for skills/<skill_name>/... pattern
        if len(parts) >= 2 and parts[0].lower() == "skills":
            discovered_skills.add(parts[1])
        # Look for <dir>/SKILL.md pattern
        elif len(parts) >= 2 and parts[-1].upper() in ("SKILL.MD", "README.MD") and parts[0].lower() not in ("docs", ".github"):
            discovered_skills.add(parts[0])

    if discovered_skills:
        sorted_skills = sorted(list(discovered_skills))
        return True, f"Discovered {len(sorted_skills)} skill(s).", sorted_skills, zip_bytes, None

    # Fallback: treat entire repo as a single skill named after the repo
    repo_skill_name = repo if 'repo' in locals() and repo else "custom-skill"
    return True, f"Found 1 repository skill '{repo_skill_name}'.", [repo_skill_name], zip_bytes, None


def extract_selected_skills(
    workspace_name: str,
    zip_bytes: bytes,
    selected_skills: List[str],
    target_subpath: Optional[str] = None,
) -> Tuple[bool, str]:
    """Selectively extract only chosen skills from zip data into workspace's skills/ folder.

    Strictly filters out repository bloat (.git, .github, tests, images, non-md/txt files).
    """
    clean_ws = workspace_name.strip().lower()
    ws_path = get_workspace_path(clean_ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return False, f"Workspace '{clean_ws}' does not exist."

    if not selected_skills:
        return False, "No skills selected for extraction."

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        names = zf.namelist()
    except Exception as exc:
        return False, f"Invalid zip archive: {exc}"

    first_part = names[0].split("/")[0] if names else ""
    prefix = ""
    if names and all(n.startswith(first_part + "/") or n == first_part for n in names if n):
        prefix = first_part + "/"

    skills_base = ws_path / "skills"
    skills_base.mkdir(parents=True, exist_ok=True)

    extracted_count = 0
    selected_set = set(selected_skills)

    for member in names:
        if member.endswith("/"):
            continue

        rel = member[len(prefix):]
        parts = rel.split("/")

        # Strict bloat filter: allow only .md and .txt files
        if not (rel.lower().endswith(".md") or rel.lower().endswith(".txt")):
            continue

        # Skip files larger than 500KB
        try:
            if zf.getinfo(member).file_size > 500 * 1024:
                continue
        except Exception:
            pass

        # Exclude hidden, test, build, and media directories
        if any(
            p.startswith(".")
            or p.startswith("_")
            or p.lower() in ("tests", "test", "node_modules", "dist", "build", "assets", "images", "img")
            for p in parts
        ):
            continue

        dest_rel: Optional[Path] = None

        # Case A: target_subpath was specified (e.g. skills/antislop-code)
        if target_subpath:
            norm_sub = target_subpath.strip("/")
            if rel.startswith(norm_sub + "/"):
                leaf = norm_sub.split("/")[-1]
                sub_rel = rel[len(norm_sub):].lstrip("/")
                dest_rel = Path(leaf) / sub_rel
            elif rel == norm_sub:
                leaf = norm_sub.split("/")[-1]
                dest_rel = Path(leaf) / "SKILL.md"

        # Case B: Repo has skills/<skill_name>/...
        elif len(parts) >= 2 and parts[0].lower() == "skills":
            skill_name = parts[1]
            if skill_name in selected_set:
                sub_rel = "/".join(parts[2:]) if len(parts) > 2 else Path(parts[-1]).name
                dest_rel = Path(skill_name) / sub_rel

        # Case C: Repo has <skill_name>/... (e.g. antislop/SKILL.md)
        elif len(parts) >= 2 and parts[0] in selected_set:
            skill_name = parts[0]
            sub_rel = "/".join(parts[1:])
            dest_rel = Path(skill_name) / sub_rel

        # Case D: Single skill fallback
        elif len(selected_set) == 1:
            single_skill = list(selected_set)[0]
            dest_rel = Path(single_skill) / rel

        if dest_rel:
            dest_file = skills_base / dest_rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = zf.read(member).decode("utf-8", errors="replace")
                dest_file.write_text(content, encoding="utf-8", errors="replace")
                extracted_count += 1
            except Exception:
                continue

    if extracted_count == 0:
        return False, "No matching .md or .txt skill files found to extract for the selected skill(s)."

    return True, f"Successfully extracted {extracted_count} file(s) for {len(selected_skills)} skill(s) into workspace '{clean_ws}'."


def install_skill_from_source(
    workspace_name: str,
    source: str,
    selected_skills: Optional[List[str]] = None,
) -> Tuple[bool, str, List[str]]:
    """Download, inspect, and install skills from a GitHub repository or URL.

    If selected_skills is provided, only those are installed.
    If multiple skills are found and selected_skills is None/empty:
        Returns (False, informative message with skill list, available_skills)
        to prevent dumping entire multi-skill repositories without user consent.
    If only 1 skill is found, it installs it automatically.
    """
    ok, msg, available, zip_bytes, target_subpath = inspect_github_skills(source)
    if not ok:
        return False, msg, []

    if not available:
        return False, "No installable skills were detected in the source repository.", []

    to_install: List[str] = []
    if selected_skills:
        to_install = [s for s in selected_skills if s in available]
        if not to_install:
            return False, f"None of the requested skills {selected_skills} were found. Available: {available}", available
    else:
        if len(available) == 1:
            to_install = available
        else:
            return False, (
                f"Repository contains {len(available)} skills: {', '.join(available)}. "
                "Specify which skill(s) to install using --skill <name>."
            ), available

    ext_ok, ext_msg = extract_selected_skills(
        workspace_name,
        zip_bytes,
        to_install,
        target_subpath=target_subpath,
    )
    return ext_ok, ext_msg, to_install


def get_workspace_sessions_dir(workspace_name: str) -> Path:
    """Return sessions directory for a workspace and ensure it exists."""
    sessions_dir = get_workspace_path(workspace_name) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def save_workspace_session(
    workspace_name: str,
    session_id: str,
    memory: Any,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Persist conversation session state to workspace sessions directory."""
    clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", session_id.strip())
    if not clean_id.endswith(".json"):
        dest = get_workspace_sessions_dir(workspace_name) / f"{clean_id}.json"
    else:
        dest = get_workspace_sessions_dir(workspace_name) / clean_id

    meta: Dict[str, Any] = {
        "session_id": clean_id.replace(".json", ""),
        "workspace": workspace_name.strip(),
        "updated_at": datetime.now().isoformat(),
        "message_count": len(getattr(memory, "history", [])),
    }
    if metadata:
        meta.update(metadata)

    if hasattr(memory, "save_to_json"):
        memory.save_to_json(dest, metadata=meta)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": meta,
            "system_prompt": getattr(memory, "system_prompt", None),
            "history": getattr(memory, "history", []),
        }
        with open(dest, "w", encoding="utf-8", errors="replace") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    return dest


def load_workspace_session(workspace_name: str, session_id: str) -> Optional[Any]:
    """Load conversation session from workspace sessions directory."""
    from locallm.core.memory import ConversationMemory

    clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", session_id.strip().replace(".json", ""))
    target = get_workspace_sessions_dir(workspace_name) / f"{clean_id}.json"
    if not target.is_file():
        return None

    memory = ConversationMemory()
    memory.load_from_json(target)
    return memory


def list_workspace_sessions(workspace_name: str) -> List[Dict[str, Any]]:
    """List all saved sessions in a workspace, sorted by updated timestamp descending."""
    sessions_dir = get_workspace_sessions_dir(workspace_name)
    results: List[Dict[str, Any]] = []

    for file_path in sessions_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            meta = data.get("metadata", {}) if isinstance(data, dict) else {}
            history = data.get("history", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            last_snippet = ""
            if history:
                last_msg = history[-1]
                content = last_msg.get("content", "")
                last_snippet = (content[:80] + "...") if len(content) > 80 else content

            session_id = meta.get("session_id", file_path.stem)
            updated_at = meta.get("updated_at", datetime.fromtimestamp(file_path.stat().st_mtime).isoformat())

            results.append({
                "session_id": session_id,
                "file_path": str(file_path),
                "type": meta.get("type", "chat"),
                "model": meta.get("model", "-"),
                "message_count": len(history),
                "last_snippet": last_snippet,
                "updated_at": updated_at,
            })
        except Exception:
            continue

    results.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
    return results


def delete_workspace_session(workspace_name: str, session_id: str) -> bool:
    """Delete a specific session file from a workspace."""
    clean_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", session_id.strip().replace(".json", ""))
    target = get_workspace_sessions_dir(workspace_name) / f"{clean_id}.json"
    if target.is_file():
        try:
            target.unlink()
            return True
        except Exception:
            return False
    return False


def clear_all_workspace_sessions(workspace_name: str) -> int:
    """Delete all saved session files from a workspace. Returns count of deleted files."""
    sessions_dir = get_workspace_sessions_dir(workspace_name)
    count = 0
    for file_path in sessions_dir.glob("*.json"):
        try:
            file_path.unlink()
            count += 1
        except Exception:
            continue
    return count


