"""Filesystem manipulation, path resolution, and sandboxed boundary checking."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from locallm.core.tools.base import tool


def resolve_smart_path(raw_path: str, boundary_dir: Optional[Path] = None) -> Path:
    """Resolve a raw path string, supporting OS user directories and aliases.

    Maps aliases like 'downloads', 'desktop', 'documents', '~', '%USERPROFILE%'
    to their actual user system directories if not found locally.

    If boundary_dir is provided, enforces that the resolved path does not escape
    the boundary directory (path traversal protection for messaging/bridges).
    """
    if not raw_path or raw_path.strip() in (".", ""):
        candidate = Path.cwd().resolve()
    else:
        clean = raw_path.strip().strip("'\"")
        expanded = os.path.expanduser(os.path.expandvars(clean))
        cand_path = Path(expanded)

        if cand_path.is_absolute() or cand_path.exists():
            candidate = cand_path.resolve()
        else:
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
                candidate = aliases[norm].resolve()
            else:
                matched_alias = False
                for alias_name, alias_dir in aliases.items():
                    prefix = alias_name + "/"
                    if norm.startswith(prefix):
                        subpath = clean.replace("\\", "/")[len(prefix):].lstrip("/")
                        candidate = (alias_dir / subpath).resolve()
                        matched_alias = True
                        break
                if not matched_alias:
                    candidate = cand_path.resolve()

    if boundary_dir is not None:
        boundary_resolved = boundary_dir.resolve()
        try:
            candidate.relative_to(boundary_resolved)
        except ValueError:
            raise PermissionError(
                f"Access denied: path '{raw_path}' escapes allowed boundary directory '{boundary_resolved}'."
            )

    return candidate


def read_file_fn(
    path: str,
    offset: int = 0,
    max_chars: int = 4000,
    boundary_dir: Optional[Path] = None,
) -> str:
    """Read file content with optional pagination offset and max_chars limit."""
    try:
        file_path = resolve_smart_path(path, boundary_dir=boundary_dir)
    except PermissionError as exc:
        return f"Error: {exc}"

    if not file_path.exists():
        return f"Error: File '{file_path}' not found."
    if file_path.is_dir():
        return f"Error: '{file_path}' is a directory, not a file. Use list_directory instead."

    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        total_len = len(text)

        safe_offset = max(0, int(offset))
        safe_max = max(1, int(max_chars)) if max_chars else 4000

        if safe_offset >= total_len and total_len > 0:
            return f"Error: Offset {safe_offset} is beyond the total file length ({total_len} characters)."

        chunk = text[safe_offset : safe_offset + safe_max]
        next_offset = safe_offset + len(chunk)

        if total_len > next_offset:
            notice = (
                f"[Showing characters {safe_offset} to {next_offset} of {total_len}. "
                f"To read the next chunk, call read_file with offset={next_offset}]\n\n"
            )
            return notice + chunk
        elif safe_offset > 0:
            notice = f"[Showing characters {safe_offset} to {next_offset} of {total_len} (End of file)]\n\n"
            return notice + chunk
        return chunk
    except Exception as exc:
        return f"Error reading file '{file_path}': {exc}"


def write_file_fn(
    path: str,
    content: str,
    boundary_dir: Optional[Path] = None,
) -> str:
    """Write text content to disk, automatically creating parent directories."""
    if not path:
        return "Error: File path is required."
    try:
        file_path = resolve_smart_path(path, boundary_dir=boundary_dir)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8", errors="replace")
        return f"Successfully wrote {len(content)} characters to '{file_path}'."
    except PermissionError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error writing file '{path}': {exc}"


def list_directory_fn(
    path: str = ".",
    boundary_dir: Optional[Path] = None,
) -> str:
    """List directory contents prioritizing folders before files."""
    try:
        target_path = resolve_smart_path(path, boundary_dir=boundary_dir)
    except PermissionError as exc:
        return f"Error: {exc}"

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


def create_directory_fn(
    path: str,
    boundary_dir: Optional[Path] = None,
) -> str:
    """Create directory anywhere on system including parent paths."""
    if not path:
        return "Error: Directory path is required."
    try:
        dir_path = resolve_smart_path(path, boundary_dir=boundary_dir)
        dir_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory '{dir_path}'."
    except PermissionError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error creating directory '{path}': {exc}"


# Register tools
tool(
    name="list_directory",
    description="List files and folders in a specified path or alias (e.g. '.', 'downloads', 'desktop')",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path or alias to list (default is '.')",
            },
        },
    },
    is_mutating=False,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(list_directory_fn)

tool(
    name="read_file",
    description="Read text content of a file from disk with optional pagination offset and length limit.",
    parameters={
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read",
            },
            "offset": {
                "type": "integer",
                "description": "Character offset to start reading from (default 0)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return in this chunk (default 4000)",
            },
        },
    },
    is_mutating=False,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(read_file_fn)

tool(
    name="write_file",
    description="Write or overwrite text content to a file anywhere on the system. Automatically creates parent directories if needed.",
    parameters={
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
    is_mutating=True,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(write_file_fn)

tool(
    name="create_directory",
    description="Create a new directory/folder anywhere on the system, including any intermediate parent directories.",
    parameters={
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to create (e.g. 'C:/Users/.../Bot Signal', 'downloads/new_project', or 'src/utils')",
            },
        },
    },
    is_mutating=True,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(create_directory_fn)


def resolve_path_fn(
    path: str,
    boundary_dir: Optional[Path] = None,
) -> str:
    """Find and inspect the absolute filesystem path, existence, and metadata of a file or directory."""
    if not path:
        return "Error: Path is required."
    try:
        file_path = resolve_smart_path(path, boundary_dir=boundary_dir)
    except PermissionError as exc:
        return f"Error: {exc}"

    if file_path.exists():
        is_dir = file_path.is_dir()
        item_type = "Directory" if is_dir else "File"
        abs_path = str(file_path.resolve())
        parent_dir = str(file_path.parent.resolve())

        if is_dir:
            return (
                f"Path: {abs_path}\n"
                f"Exists: True\n"
                f"Type: Directory\n"
                f"Absolute Path: {abs_path}\n"
                f"Parent Directory: {parent_dir}"
            )
        else:
            try:
                stat = file_path.stat()
                size_kb = stat.st_size / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{stat.st_size} bytes"
            except Exception:
                size_str = "Unknown"
            return (
                f"Path: {abs_path}\n"
                f"Exists: True\n"
                f"Type: File\n"
                f"Size: {size_str}\n"
                f"Absolute Path: {abs_path}\n"
                f"Parent Directory: {parent_dir}"
            )

    # Not found at exact location: attempt helpful nearby search in working directory
    name = file_path.name
    try:
        cwd = Path.cwd().resolve()
        matches = [str(p.resolve()) for p in cwd.glob(f"**/{name}") if p.is_file() or p.is_dir()]
        if matches:
            found_list = "\n".join(f"- {m}" for m in matches[:5])
            return (
                f"Path '{file_path}' does not exist at the exact specified location (Exists: False).\n"
                f"However, item with name '{name}' was located in working directory at:\n{found_list}"
            )
    except Exception:
        pass

    return f"Path '{file_path}' does not exist (Exists: False). Absolute candidate: {file_path.resolve()}"


tool(
    name="resolve_path",
    description="Find and resolve the absolute filesystem path, existence, and metadata of a file or directory without modifying or opening its content.",
    parameters={
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute path, filename, or alias to locate (e.g. './reports/uv_latest.md', 'downloads/data.json', 'README.md')",
            },
        },
    },
    is_mutating=False,
    is_privileged=True,
    categories={"assistant", "telegram", "whatsapp"},
)(resolve_path_fn)
