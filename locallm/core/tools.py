"""Built-in tools for local model function calling and automation."""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Set
import httpx


def resolve_smart_path(raw_path: str) -> Path:
    """Resolve a raw path string, supporting OS user directories and aliases.

    Maps aliases like 'downloads', 'desktop', 'documents', '~', '%USERPROFILE%'
    to their actual user system directories if not found locally.
    """
    if not raw_path or raw_path.strip() in (".", ""):
        return Path.cwd().resolve()

    clean = raw_path.strip().strip("'\"")
    expanded = os.path.expanduser(os.path.expandvars(clean))
    candidate = Path(expanded)

    # If explicit absolute path (e.g. C:\..., /opt/...), resolve directly anywhere on system
    if candidate.is_absolute():
        return candidate.resolve()

    if candidate.exists():
        return candidate.resolve()

    home = Path.home()
    aliases = {
        "downloads": home / "Downloads",
        "download": home / "Downloads",
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "document": home / "Documents",
        "pictures": home / "Pictures",
        "images": home / "Pictures",
        "videos": home / "Videos",
        "music": home / "Music",
        "home": home,
        "~": home,
    }

    norm = clean.replace("\\", "/").strip("/").lower()
    if norm in aliases:
        return aliases[norm].resolve()

    for alias_name, alias_dir in aliases.items():
        prefix = alias_name + "/"
        if norm.startswith(prefix):
            subpath = clean.replace("\\", "/")[len(prefix):].lstrip("/")
            resolved = alias_dir / subpath
            return resolved.resolve()

    return candidate.resolve()


ASSISTANT_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current local date, time, day of week, and timezone",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_directory",
            "description": "Get the current working directory path",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a specified path or alias (e.g. '.', 'downloads', 'desktop')",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path or alias to list (default is '.')",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read text content of a file from disk",
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_web",
            "description": "Fetch and read text content from a web page, GitHub repository, or URL",
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "HTTP or HTTPS URL to fetch (e.g. https://github.com/owner/repo or article link)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Run a shell command safely to inspect system state",
            "parameters": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command line string to execute",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather condition and temperature for a city",
            "parameters": {
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or location name",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite text content to a file anywhere on the system. Automatically creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write (absolute path or relative path, e.g. 'C:/Users/.../config.py', 'downloads/project/main.py', or 'README.md')",
                    },
                    "content": {
                        "type": "string",
                        "description": "The exact text content to write into the file",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory/folder anywhere on the system, including any intermediate parent directories.",
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to create (e.g. 'C:/Users/.../Bot Signal', 'downloads/new_project', or 'src/utils')",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all available agent skills and specialized instruction workflows in the workspace and project.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill",
            "description": "Read the complete instructions, rules, or cheatsheet of a specific skill by name.",
            "parameters": {
                "type": "object",
                "required": ["skill_name"],
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The exact name or identifier of the skill to read",
                    },
                },
            },
        },
    },
]

TELEGRAM_TOOLS: List[Dict[str, Any]] = list(ASSISTANT_TOOLS) + [
    {
        "type": "function",
        "function": {
            "name": "telegram_get_user_info",
            "description": "Get detailed Telegram metadata about the current user and active chat (name, username, user ID, language code, chat type).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_send_photo",
            "description": "Send an image or photo directly to the user in Telegram. Supports local file paths (e.g. 'desktop/image.png' or relative paths) and public web image URLs.",
            "parameters": {
                "type": "object",
                "required": ["photo_path_or_url"],
                "properties": {
                    "photo_path_or_url": {
                        "type": "string",
                        "description": "Local file path (e.g. 'desktop/chart.png') or public HTTP/HTTPS image URL",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional text caption accompanying the photo",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_send_document",
            "description": "Send any local file or document (e.g. PDF, Python script, Markdown report, zip, log file) directly to the user in Telegram.",
            "parameters": {
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Local file path (e.g. 'README.md', 'desktop/report.pdf')",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional caption describing the document",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_send_dice",
            "description": "Send an interactive animated Telegram game dice or emoji to the user. Emojis supported: '🎲', '🎯', '🏀', '⚽', '🎰', '🎳'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emoji": {
                        "type": "string",
                        "description": "Dice emoji: '🎲', '🎯', '🏀', '⚽', '🎰', '🎳' (default is '🎲')",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_send_sticker",
            "description": "Send a Telegram sticker using a valid Telegram sticker file_id.",
            "parameters": {
                "type": "object",
                "required": ["sticker"],
                "properties": {
                    "sticker": {
                        "type": "string",
                        "description": "Telegram sticker file_id",
                    },
                },
            },
        },
    },
]

WHATSAPP_TOOLS: List[Dict[str, Any]] = list(ASSISTANT_TOOLS) + [
    {
        "type": "function",
        "function": {
            "name": "whatsapp_get_contact_info",
            "description": "Get WhatsApp metadata about current user and active chat (phone number, pushName, JID).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_send_image",
            "description": "Send a photo or image directly to the user in WhatsApp. Supports local file paths and public image URLs.",
            "parameters": {
                "type": "object",
                "required": ["image_path_or_url"],
                "properties": {
                    "image_path_or_url": {
                        "type": "string",
                        "description": "Local file path (e.g. 'desktop/chart.png') or public HTTP/HTTPS image URL",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional text caption accompanying the image",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_send_document",
            "description": "Send any local file or document (PDF, script, Markdown, zip, report) directly to the user in WhatsApp.",
            "parameters": {
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to deliver (e.g. 'README.md', 'desktop/report.pdf')",
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional caption describing the document",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "whatsapp_send_sticker",
            "description": "Send a WhatsApp sticker generated from a local image file (PNG, JPG, WEBP).",
            "parameters": {
                "type": "object",
                "required": ["image_path"],
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Local image file path to convert and send as sticker (e.g. 'pictures/sticker.png')",
                    },
                },
            },
        },
    },
]


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    permission_policy: str = "always_allow",
    interactive: bool = True,
    session_state: Optional[Dict[str, Any]] = None,
    workspace_name: Optional[str] = "default",
) -> str:
    """Execute a requested tool with permission policy and return a string observation."""
    mutating_tools = {"write_file", "create_directory", "execute_command"}

    if name in mutating_tools:
        effective_policy = permission_policy.lower()
        if session_state and "permission_override" in session_state:
            effective_policy = session_state["permission_override"]

        if effective_policy == "deny":
            return f"[Permission Denied] Policy is set to 'deny'. Mutating action '{name}' was blocked."

        if effective_policy == "ask" and interactive:
            import questionary
            from locallm.ui.theme import QUESTIONARY_STYLE, console

            console.print(f"\n[bold yellow]✦ Permission Request:[/] Agent requests permission to execute [bold cyan]{name}[/]")
            if name == "write_file":
                console.print(f"  [#aaaaaa]Path:[/] [bold]{arguments.get('path', '')}[/]")
            elif name == "create_directory":
                console.print(f"  [#aaaaaa]Directory:[/] [bold]{arguments.get('path', '')}[/]")
            elif name == "execute_command":
                console.print(f"  [#aaaaaa]Command:[/] [bold]{arguments.get('command', '')}[/]")

            ans = questionary.select(
                f"Authorize agent to execute {name}?",
                choices=[
                    "Allow Once",
                    "Always Allow (this session)",
                    "Deny",
                ],
                style=QUESTIONARY_STYLE,
            ).ask()

            if ans == "Always Allow (this session)":
                if session_state is not None:
                    session_state["permission_override"] = "always_allow"
            elif ans != "Allow Once":
                return f"[Permission Denied] User rejected execution of '{name}'."

    if name == "get_current_time":
        now = datetime.now()
        tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
        return now.strftime(f"%A, %Y-%m-%d %H:%M:%S {tz_name}")

    elif name == "get_current_directory":
        return str(Path.cwd().resolve())

    elif name == "list_directory":
        raw_path = arguments.get("path", ".")
        target_path = resolve_smart_path(raw_path)
        if not target_path.exists():
            return f"Error: Directory '{target_path}' does not exist."
        if not target_path.is_dir():
            return f"Error: '{target_path}' is a file, not a directory. Use read_file to inspect it."
        try:
            dirs = []
            files = []
            for item in sorted(target_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                try:
                    if item.is_dir():
                        dirs.append(f"[DIR]  {item.name}")
                    else:
                        size_kb = item.stat().st_size / 1024
                        size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{item.stat().st_size} bytes"
                        files.append(f"[FILE] {item.name} ({size_str})")
                except Exception:
                    continue

            total_items = len(dirs) + len(files)
            header = f"Directory contents of '{target_path}' (Total: {len(dirs)} folders, {len(files)} files):\n"
            lines = dirs[:80] + files[:80]
            if not lines:
                body = "(Empty directory)"
            else:
                body = "\n".join(lines)
                if total_items > len(lines):
                    body += f"\n... ({total_items - len(lines)} additional items not shown)"
            return header + body
        except Exception as exc:
            return f"Error listing directory '{target_path}': {exc}"

    elif name == "read_file":
        path_str = arguments.get("path", "")
        file_path = resolve_smart_path(path_str)
        if not file_path.exists():
            return f"Error: File '{file_path}' not found."
        if file_path.is_dir():
            return f"Error: '{file_path}' is a directory, not a file. Use list_directory instead."
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            return text[:4000]
        except Exception as exc:
            return f"Error reading file '{file_path}': {exc}"

    elif name == "fetch_web":
        url = arguments.get("url", "").strip()
        if not url:
            return "Error: URL is required."
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
        }

        # Check for GitHub repository URL to attempt direct README retrieval
        gh_match = re.match(r"^https?://github\.com/([^/]+)/([^/#?]+)/?$", url)
        if gh_match:
            owner, repo = gh_match.group(1), gh_match.group(2)
            raw_readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
            try:
                with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
                    gh_res = client.get(raw_readme_url)
                    if gh_res.status_code == 200 and gh_res.text.strip():
                        return f"GitHub Repository: {owner}/{repo}\nREADME Content:\n" + gh_res.text[:3500]
            except Exception:
                pass

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
                res = client.get(url)
                if res.status_code != 200:
                    return f"HTTP {res.status_code}: Unable to access {url}"

                raw_html = res.text
                # Clean scripts, styles, and tags
                clean = re.sub(r"<script[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
                clean = re.sub(r"<style[\s\S]*?</style>", "", clean, flags=re.IGNORECASE)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = re.sub(r"\s+", " ", clean).strip()
                return clean[:3500] if clean else "(Empty or non-text content retrieved)"
        except Exception as exc:
            return f"Error fetching URL '{url}': {exc}"

    elif name == "execute_command":
        cmd = arguments.get("command", "").strip()
        if not cmd:
            return "Error: Empty command."
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, creationflags=flags)
            output = res.stdout + ("\nError: " + res.stderr if res.stderr else "")
            return output.strip() or "(Executed with no output)"
        except Exception as exc:
            return f"Command error: {exc}"

    elif name == "get_weather":
        loc = arguments.get("location", "").strip()
        if not loc:
            return "Error: Location is required."
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(f"https://wttr.in/{loc}?format=%l:+%C,+%t")
                if res.status_code == 200:
                    text = res.text.replace("\u00b0", " deg ").strip()
                    return text
        except Exception as exc:
            return f"Weather lookup error: {exc}"

    elif name == "write_file":
        path_str = arguments.get("path", "")
        content = arguments.get("content", "")
        if not path_str:
            return "Error: File path is required."
        file_path = resolve_smart_path(path_str)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8", errors="replace")
            return f"Successfully wrote {len(content)} characters to '{file_path}'."
        except Exception as exc:
            return f"Error writing file '{file_path}': {exc}"

    elif name == "create_directory":
        path_str = arguments.get("path", "")
        if not path_str:
            return "Error: Directory path is required."
        dir_path = resolve_smart_path(path_str)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return f"Successfully created directory '{dir_path}'."
        except Exception as exc:
            return f"Error creating directory '{dir_path}': {exc}"

    elif name == "list_skills":
        from locallm.core.workspace import get_all_available_skills
        skills = get_all_available_skills(workspace_name)
        if not skills:
            return "No custom agent skills found in active workspace or project."
        lines = [f"Available Agent Skills ({len(skills)} total):"]
        for s in skills:
            lines.append(f"- {s['name']} [{s['source']}]: {s['description']}")
        return "\n".join(lines)

    elif name == "read_skill":
        from locallm.core.workspace import get_skill_content
        skill_name = arguments.get("skill_name", "")
        if not skill_name:
            return "Error: 'skill_name' parameter is required."
        content = get_skill_content(skill_name, workspace_name)
        if not content:
            return f"Error: Skill '{skill_name}' not found."
        return f"=== Skill Content for '{skill_name}' ===\n" + content[:6000]

    return f"Unknown tool: '{name}'"


def describe_tool_action(name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
    """Generate clean, human-friendly action text for terminal spinners and notifications."""
    args = arguments or {}
    if name == "create_directory":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is creating folder '{name_str or path}'..." if (name_str or path) else "locaLLM is creating folder..."

    elif name == "write_file":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is writing file '{name_str or path}'..." if (name_str or path) else "locaLLM is writing file..."

    elif name == "list_directory":
        path = args.get("path", ".")
        name_str = Path(path).name if path not in (".", "") else "workspace"
        return f"locaLLM is inspecting folder '{name_str}'..."

    elif name == "read_file":
        path = args.get("path", "")
        name_str = Path(path).name if path else ""
        return f"locaLLM is reading '{name_str or path}'..." if (name_str or path) else "locaLLM is reading file..."

    elif name == "execute_command":
        cmd = args.get("command", "").strip()
        short_cmd = (cmd[:35] + "...") if len(cmd) > 35 else cmd
        return f"locaLLM is running command: {short_cmd}..." if short_cmd else "locaLLM is running system command..."

    elif name == "fetch_web":
        url = args.get("url", "").strip()
        clean_url = re.sub(r"^https?://(www\.)?", "", url)
        short_url = (clean_url[:35] + "...") if len(clean_url) > 35 else clean_url
        return f"locaLLM is fetching web content ({short_url})..." if short_url else "locaLLM is fetching web content..."

    elif name == "get_weather":
        loc = args.get("location", "")
        return f"locaLLM is checking weather for '{loc}'..." if loc else "locaLLM is checking weather..."

    elif name == "get_current_time":
        return "locaLLM is checking current time..."

    elif name == "get_current_directory":
        return "locaLLM is checking working directory..."

    elif name == "list_skills":
        return "locaLLM is discovering available skills..."

    elif name == "read_skill":
        sname = args.get("skill_name", "")
        return f"locaLLM is reading skill instructions for '{sname}'..." if sname else "locaLLM is reading skill..."

    return f"locaLLM is executing {name}..."


def format_live_tool_report(name: str, arguments: Optional[Dict[str, Any]], observation: str) -> str:
    """Format a persistent real-time completion report line for display in terminal/logs."""
    args = arguments or {}
    obs_lower = observation.lower()
    is_error = obs_lower.startswith("error") or "permission denied" in obs_lower or "failed" in obs_lower

    if is_error:
        clean_obs = observation.replace("[Permission Denied] ", "")
        return f"  [bold red]✖[/] [red]{name} failed:[/] [dim]{clean_obs}[/]"

    if name == "create_directory":
        path = args.get("path", "")
        return f"  [bold #00ff87]✔[/] [#00ff87]Created directory:[/] [bold cyan]{path}[/]"

    elif name == "write_file":
        path = args.get("path", "")
        content = args.get("content", "")
        return f"  [bold #00ff87]✔[/] [#00ff87]Written file:[/] [bold cyan]{path}[/] [dim]({len(content)} chars)[/]"

    elif name == "list_directory":
        path = args.get("path", ".")
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Inspected directory:[/] [bold cyan]{path}[/]"

    elif name == "read_file":
        path = args.get("path", "")
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Read file:[/] [bold cyan]{path}[/]"

    elif name == "execute_command":
        cmd = args.get("command", "").strip()
        short_cmd = (cmd[:40] + "...") if len(cmd) > 40 else cmd
        return f"  [bold #00ff87]✔[/] [#00ff87]Executed:[/] [bold cyan]{short_cmd}[/]"

    elif name == "fetch_web":
        url = args.get("url", "").strip()
        clean_url = re.sub(r"^https?://(www\.)?", "", url)
        short_url = (clean_url[:40] + "...") if len(clean_url) > 40 else clean_url
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Fetched web:[/] [dim cyan]{short_url}[/]"

    elif name == "get_weather":
        loc = args.get("location", "")
        return f"  [bold #00ff87]✔[/] [#00ff87]Weather ({loc}):[/] [dim white]{observation}[/]"

    elif name == "get_current_time":
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Checked time:[/] [dim white]{observation}[/]"

    elif name == "get_current_directory":
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Working directory:[/] [dim white]{observation}[/]"

    elif name == "list_skills":
        return "  [bold #00d7ff]✔[/] [#00d7ff]Discovered skills[/]"

    elif name == "read_skill":
        sname = args.get("skill_name", "")
        return f"  [bold #00d7ff]✔[/] [#00d7ff]Loaded skill:[/] [dim cyan]{sname}[/]"

    return f"  [bold #00ff87]✔[/] [#00ff87]Executed:[/] [bold cyan]{name}[/]"


def extract_fallback_tool_calls(
    content: str,
    valid_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract tool calls emitted as raw or markdown JSON in the content string.

    Handles single JSON objects, newline-delimited JSON objects, array of JSON objects,
    and markdown code-fenced json blocks when the backend engine leaves tool_calls empty.
    """
    if not content or "{" not in content:
        return []

    if valid_names is None:
        valid_names = {t.get("function", {}).get("name") for t in ASSISTANT_TOOLS}

    calls: List[Dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    length = len(content)

    while idx < length:
        idx = content.find("{", idx)
        if idx == -1:
            break
        try:
            obj, end_idx = decoder.raw_decode(content[idx:])
            idx += end_idx
            if isinstance(obj, dict):
                name = obj.get("name") or obj.get("tool")
                if not name and isinstance(obj.get("function"), dict):
                    name = obj.get("function", {}).get("name")
                elif not name and isinstance(obj.get("function"), str):
                    name = obj.get("function")

                args = obj.get("arguments") or obj.get("args") or obj.get("parameters")
                if args is None and isinstance(obj.get("function"), dict):
                    args = obj.get("function", {}).get("arguments") or obj.get("function", {}).get("parameters")
                if args is None:
                    args = {}

                if isinstance(name, str) and name in valid_names:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    calls.append({
                        "id": f"call_fallback_{len(calls)}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": args,
                        },
                    })
        except Exception:
            idx += 1

    return calls

