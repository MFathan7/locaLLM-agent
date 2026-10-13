"""System, time, weather, and skill inspection tools for locaLLM."""

from datetime import datetime
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, Optional
import httpx
from locallm.core.tools.base import tool


def get_current_time_fn() -> str:
    """Return formatted current local date, time, and timezone."""
    now = datetime.now()
    tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    return now.strftime(f"%A, %Y-%m-%d %H:%M:%S {tz_name}")


def get_current_directory_fn(context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """Return absolute path of active workspace or current working directory."""
    ws_name = (context or {}).get("workspace_name")
    if ws_name:
        try:
            from locallm.core.workspace import get_workspace_dir
            ws_dir = get_workspace_dir(ws_name)
            if ws_dir.is_dir():
                return str(ws_dir.resolve())
        except Exception:
            pass
    return str(Path.cwd().resolve())


def execute_command_fn(
    command: Optional[str] = None,
    timeout: int = 15,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> str:
    """Run shell command safely in subprocess with output capture and timeout."""
    cmd_raw = command or kwargs.get("cmd") or kwargs.get("cli") or kwargs.get("script") or kwargs.get("args") or ""
    cmd = str(cmd_raw).strip()
    if not cmd:
        return "Error: Empty command."
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        # Determine working directory: prefer explicit cwd -> sandbox boundary -> active project CWD -> workspace fallback
        run_cwd = None
        specified_dir = kwargs.get("cwd") or kwargs.get("working_dir") or kwargs.get("directory")
        if specified_dir:
            cand = Path(os.path.expanduser(os.path.expandvars(str(specified_dir).strip())))
            if cand.is_dir():
                run_cwd = str(cand.resolve())

        if not run_cwd and context and context.get("boundary_dir"):
            cand = Path(str(context["boundary_dir"]))
            if cand.is_dir():
                run_cwd = str(cand.resolve())

        if not run_cwd:
            try:
                cand = Path.cwd().resolve()
                if cand.is_dir():
                    run_cwd = str(cand)
            except Exception:
                pass

        if not run_cwd:
            ws_name = (context or {}).get("workspace_name")
            if ws_name:
                try:
                    from locallm.core.workspace import get_workspace_dir
                    ws_dir = get_workspace_dir(ws_name)
                    if ws_dir.is_dir():
                        run_cwd = str(ws_dir.resolve())
                except Exception:
                    pass

        res = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=run_cwd,
            creationflags=flags,
        )
        output = res.stdout + ("\nError: " + res.stderr if res.stderr else "")
        return output.strip() or "(Executed with no output)"
    except subprocess.TimeoutExpired:
        return f"Command execution timed out after {timeout} seconds."
    except Exception as exc:
        return f"Command error: {exc}"


def get_weather_fn(location: str) -> str:
    """Check current weather condition and temperature for a city."""
    loc = location.strip()
    if not loc:
        return "Error: Location is required."
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.get(f"https://wttr.in/{loc}?format=%l:+%C,+%t")
            if res.status_code == 200:
                return res.text.replace("\u00b0", " deg ").strip()
            return f"Weather lookup failed (HTTP {res.status_code})."
    except Exception as exc:
        return f"Weather lookup error: {exc}"


def list_skills_fn(context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """List all available skills from workspace and project."""
    workspace_name = (context or {}).get("workspace_name", "default")
    try:
        from locallm.core.workspace import get_all_available_skills, get_workspace_dir

        ws_dir = get_workspace_dir(workspace_name)
        skills = get_all_available_skills(workspace_name)
        if not skills:
            return f"No custom agent skills found in active workspace '{workspace_name}' ({ws_dir / 'skills'}) or project."
        lines = [
            f"Active Workspace: '{workspace_name}' (Skills Directory: {ws_dir / 'skills'})",
            f"Available Agent Skills ({len(skills)} total):",
        ]
        for s in skills:
            lines.append(f"- {s['name']} [{s['source']}]: {s['description']}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Error listing skills: {exc}"


def read_skill_fn(skill_name: str, context: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """Read the complete instructions of a specific skill."""
    if not skill_name:
        return "Error: 'skill_name' parameter is required."
    workspace_name = (context or {}).get("workspace_name", "default")
    try:
        from locallm.core.workspace import get_skill_content

        content = get_skill_content(skill_name, workspace_name)
        if not content:
            return f"Error: Skill '{skill_name}' not found."
        return f"=== Skill Content for '{skill_name}' ===\n" + content[:6000]
    except Exception as exc:
        return f"Error reading skill: {exc}"


# Register tools
tool(
    name="get_current_time",
    description="Get current local date, time, day of week, and timezone",
    parameters={"type": "object", "properties": {}},
    is_mutating=False,
    categories={"assistant", "telegram", "whatsapp"},
)(get_current_time_fn)

tool(
    name="get_current_directory",
    description="Get the current working directory path",
    parameters={"type": "object", "properties": {}},
    is_mutating=False,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(get_current_directory_fn)

tool(
    name="execute_command",
    description="Run a shell command safely to inspect system state",
    parameters={
        "type": "object",
        "required": ["command"],
        "properties": {
            "command": {
                "type": "string",
                "description": "Command line string to execute",
            },
        },
    },
    is_mutating=True,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(execute_command_fn)

tool(
    name="get_weather",
    description="Get current weather condition and temperature for a city",
    parameters={
        "type": "object",
        "required": ["location"],
        "properties": {
            "location": {
                "type": "string",
                "description": "City or location name",
            },
        },
    },
    is_mutating=False,
    categories={"assistant", "telegram", "whatsapp"},
)(get_weather_fn)

tool(
    name="list_skills",
    description="List all available agent skills and specialized instruction workflows in the workspace and project.",
    parameters={"type": "object", "properties": {}},
    is_mutating=False,
    categories={"assistant"},
)(list_skills_fn)

tool(
    name="read_skill",
    description="Read the complete instructions, rules, or cheatsheet of a specific skill by name or path.",
    parameters={
        "type": "object",
        "required": ["skill_name"],
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The name, path, or identifier of the skill to read (e.g., 'vuln-sqli' or 'antislop')",
            },
        },
    },
    is_mutating=False,
    categories={"assistant"},
)(read_skill_fn)


def complete_task_fn(final_answer: str = "", **kwargs: Any) -> str:
    """Signal task completion and return the final answer summary."""
    ans = (final_answer or "").strip()
    return ans or "Task completed successfully."


tool(
    name="complete_task",
    description=(
        "Conclude and finish the current task execution cycle. "
        "Call this function ONLY when all user instructions have been completely satisfied, essential data is collected, "
        "or the final answer is ready. Calling this function immediately concludes the agent execution cycle."
    ),
    parameters={
        "type": "object",
        "required": ["final_answer"],
        "properties": {
            "final_answer": {
                "type": "string",
                "description": "Comprehensive final answer or summary of the completed task to deliver to the user.",
            },
        },
    },
    is_mutating=False,
    categories={"assistant", "telegram", "whatsapp"},
)(complete_task_fn)

