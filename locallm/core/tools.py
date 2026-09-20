"""Built-in tools for local model function calling and automation."""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List
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


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Execute a requested tool and return a string observation."""
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
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"https://wttr.in/{loc}?format=3")
                if res.status_code == 200:
                    return res.text.strip()
                return f"Unable to fetch weather (status {res.status_code})"
        except Exception as exc:
            return f"Weather lookup error: {exc}"

    return f"Unknown tool: '{name}'"
