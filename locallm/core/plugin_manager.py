"""Modular Plugin Architecture and Dynamic Tool Management for locaLLM."""

from dataclasses import dataclass, field
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class PluginInfo:
    """Metadata and tool definitions for an extensible locaLLM plugin."""

    name: str
    version: str
    description: str
    author: str
    enabled: bool
    dir_path: Path
    manifest_path: Path
    entrypoint_path: Optional[Path]
    tools: List[Dict[str, Any]] = field(default_factory=list)
    mutating_tools: Set[str] = field(default_factory=set)
    privileged_tools: Set[str] = field(default_factory=set)
    source: str = "global"  # "global", "workspace", "local"
    error: Optional[str] = None


def get_global_plugins_dir() -> Path:
    """Return base global plugins directory (~/.locallm/plugins)."""
    base = Path.home() / ".locallm" / "plugins"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_workspace_plugins_dir(workspace_name: Optional[str] = None) -> Optional[Path]:
    """Return workspace-specific plugins directory."""
    if not workspace_name:
        return None
    from locallm.core.workspace import get_workspace_path
    ws_dir = get_workspace_path(workspace_name) / "plugins"
    ws_dir.mkdir(parents=True, exist_ok=True)
    return ws_dir


def get_local_plugins_dir() -> Optional[Path]:
    """Return project-local plugins directory in current working directory."""
    cwd = Path.cwd()
    for cand in [cwd / "plugins", cwd / ".locallm" / "plugins"]:
        if cand.is_dir():
            return cand.resolve()
    return None


def _load_plugin_from_dir(plugin_dir: Path, source: str = "global") -> Optional[PluginInfo]:
    """Inspect and load a single plugin directory containing plugin.json."""
    manifest_path = plugin_dir / "plugin.json"
    if not manifest_path.is_file():
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return PluginInfo(
            name=plugin_dir.name,
            version="0.0.0",
            description="Failed to parse plugin.json",
            author="Unknown",
            enabled=False,
            dir_path=plugin_dir,
            manifest_path=manifest_path,
            entrypoint_path=None,
            source=source,
            error=str(exc),
        )

    name = str(data.get("name", plugin_dir.name)).strip()
    version = str(data.get("version", "1.0.0")).strip()
    description = str(data.get("description", "")).strip()
    author = str(data.get("author", "locaLLM User")).strip()
    enabled = bool(data.get("enabled", True))

    entrypoint_name = str(data.get("entrypoint", "main.py")).strip()
    entrypoint_path = plugin_dir / entrypoint_name
    if not entrypoint_path.is_file():
        entrypoint_path = None

    raw_tools = data.get("tools", [])
    standard_tools: List[Dict[str, Any]] = []
    mutating_tools: Set[str] = set()
    privileged_tools: Set[str] = set()

    for item in raw_tools:
        if not isinstance(item, dict):
            continue

        # Support OpenAI/Ollama function calling schema
        if item.get("type") == "function" and isinstance(item.get("function"), dict):
            tool_obj = item
            func_name = item["function"].get("name", "")
        elif "name" in item and "parameters" in item:
            func_name = item["name"]
            tool_obj = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": item.get("description", ""),
                    "parameters": item.get("parameters", {"type": "object", "properties": {}}),
                },
            }
        else:
            continue

        if func_name:
            standard_tools.append(tool_obj)
            is_mutating = bool(item.get("mutating", False) or item.get("function", {}).get("mutating", False))
            is_privileged = bool(item.get("privileged", False) or item.get("function", {}).get("privileged", False) or is_mutating)
            if is_mutating:
                mutating_tools.add(func_name)
            if is_privileged:
                privileged_tools.add(func_name)

    return PluginInfo(
        name=name,
        version=version,
        description=description,
        author=author,
        enabled=enabled,
        dir_path=plugin_dir,
        manifest_path=manifest_path,
        entrypoint_path=entrypoint_path,
        tools=standard_tools,
        mutating_tools=mutating_tools,
        privileged_tools=privileged_tools,
        source=source,
    )


def list_plugins(workspace_name: Optional[str] = None) -> List[PluginInfo]:
    """Discover all plugins across global, workspace, and local project directories."""
    plugins: List[PluginInfo] = []
    seen_names: Set[str] = set()

    # 1. Project-Local directory (highest precedence)
    local_dir = get_local_plugins_dir()
    if local_dir and local_dir.is_dir():
        for item in sorted(local_dir.iterdir()):
            if item.is_dir() and (item / "plugin.json").is_file():
                p = _load_plugin_from_dir(item, source="local")
                if p and p.name.lower() not in seen_names:
                    plugins.append(p)
                    seen_names.add(p.name.lower())

    # 2. Workspace-specific directory
    if workspace_name:
        ws_dir = get_workspace_plugins_dir(workspace_name)
        if ws_dir and ws_dir.is_dir():
            for item in sorted(ws_dir.iterdir()):
                if item.is_dir() and (item / "plugin.json").is_file():
                    p = _load_plugin_from_dir(item, source=f"ws:{workspace_name}")
                    if p and p.name.lower() not in seen_names:
                        plugins.append(p)
                        seen_names.add(p.name.lower())

    # 3. Global directory (~/.locallm/plugins)
    global_dir = get_global_plugins_dir()
    if global_dir.is_dir():
        for item in sorted(global_dir.iterdir()):
            if item.is_dir() and (item / "plugin.json").is_file():
                p = _load_plugin_from_dir(item, source="global")
                if p and p.name.lower() not in seen_names:
                    plugins.append(p)
                    seen_names.add(p.name.lower())

    return plugins


def get_plugin(name: str, workspace_name: Optional[str] = None) -> Optional[PluginInfo]:
    """Find a specific plugin by name (case-insensitive)."""
    target = name.strip().lower()
    for p in list_plugins(workspace_name):
        if p.name.strip().lower() == target:
            return p
    return None


def get_active_plugin_tools(workspace_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return combined list of tool schemas provided by all currently enabled plugins."""
    active_tools: List[Dict[str, Any]] = []
    registered_names: Set[str] = set()

    for p in list_plugins(workspace_name):
        if not p.enabled or p.error:
            continue
        for tool_schema in p.tools:
            fname = tool_schema.get("function", {}).get("name")
            if fname and fname not in registered_names:
                active_tools.append(tool_schema)
                registered_names.add(fname)

    return active_tools


def get_plugin_mutating_tools(workspace_name: Optional[str] = None) -> Set[str]:
    """Return set of all mutating tool names contributed by active plugins."""
    mutating: Set[str] = set()
    for p in list_plugins(workspace_name):
        if p.enabled and not p.error:
            mutating.update(p.mutating_tools)
    return mutating


def get_plugin_privileged_tools(workspace_name: Optional[str] = None) -> Set[str]:
    """Return set of all privileged tool names contributed by active plugins."""
    privileged: Set[str] = set()
    for p in list_plugins(workspace_name):
        if p.enabled and not p.error:
            privileged.update(p.privileged_tools)
    return privileged


def execute_plugin_tool(
    name: str,
    arguments: Dict[str, Any],
    workspace_name: Optional[str] = None,
) -> Tuple[bool, str]:
    """Execute a tool call using installed and enabled plugins.

    Returns:
        (handled: bool, observation: str)
    """
    for p in list_plugins(workspace_name):
        if not p.enabled or p.error or not p.entrypoint_path:
            continue

        tool_names = [t.get("function", {}).get("name") for t in p.tools]
        if name not in tool_names:
            continue

        # Load plugin module dynamically
        try:
            module_name = f"locallm_plugin_{re.sub(r'[^a-zA-Z0-9_]', '_', p.name)}"
            spec = importlib.util.spec_from_file_location(module_name, p.entrypoint_path)
            if not spec or not spec.loader:
                return True, f"Error: Unable to load plugin entrypoint for '{p.name}'."

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Option A: Function matching the tool name directly (e.g. def query_sqlite(...):)
            if hasattr(module, name) and callable(getattr(module, name)):
                func = getattr(module, name)
                try:
                    res = func(**arguments)
                    return True, str(res)
                except TypeError:
                    # Fallback to passing arguments dict if kwargs failed
                    res = func(arguments)
                    return True, str(res)

            # Option B: Generic tool dispatcher: def execute_tool(tool_name, arguments):
            if hasattr(module, "execute_tool") and callable(getattr(module, "execute_tool")):
                res = module.execute_tool(name, arguments)
                return True, str(res)

            return True, f"Error: Plugin '{p.name}' declared tool '{name}' but found no callable function '{name}' in '{p.entrypoint_path.name}'."

        except Exception as exc:
            return True, f"Error executing plugin tool '{name}' from '{p.name}': {exc}"

    return False, ""


def enable_plugin(name: str, workspace_name: Optional[str] = None) -> Tuple[bool, str]:
    """Enable a plugin by updating its manifest file."""
    p = get_plugin(name, workspace_name)
    if not p:
        return False, f"Plugin '{name}' not found."

    try:
        with open(p.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["enabled"] = True
        with open(p.manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True, f"Plugin '{p.name}' enabled successfully."
    except Exception as exc:
        return False, f"Failed to enable plugin '{p.name}': {exc}"


def disable_plugin(name: str, workspace_name: Optional[str] = None) -> Tuple[bool, str]:
    """Disable a plugin by updating its manifest file."""
    p = get_plugin(name, workspace_name)
    if not p:
        return False, f"Plugin '{name}' not found."

    try:
        with open(p.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["enabled"] = False
        with open(p.manifest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True, f"Plugin '{p.name}' disabled."
    except Exception as exc:
        return False, f"Failed to disable plugin '{p.name}': {exc}"


def create_plugin_scaffold(
    name: str,
    target_dir: Optional[Path] = None,
    description: str = "",
) -> Tuple[bool, str, Optional[Path]]:
    """Create a new starter plugin scaffold with plugin.json and main.py."""
    clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip().lower())
    if not clean_name:
        return False, "Plugin name cannot be empty.", None

    base_dir = target_dir or get_global_plugins_dir()
    plugin_dir = base_dir / clean_name
    if plugin_dir.exists():
        return False, f"Plugin directory '{clean_name}' already exists in '{base_dir}'.", None

    try:
        plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": clean_name,
            "version": "1.0.0",
            "description": description.strip() or f"Custom {clean_name} plugin for locaLLM",
            "author": "locaLLM User",
            "enabled": True,
            "entrypoint": "main.py",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": f"{clean_name}_example_action",
                        "description": f"Example action provided by {clean_name} plugin",
                        "parameters": {
                            "type": "object",
                            "required": ["input_text"],
                            "properties": {
                                "input_text": {
                                    "type": "string",
                                    "description": "Sample input parameter to process",
                                },
                            },
                        },
                    },
                    "mutating": False,
                }
            ],
        }

        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        entrypoint_content = f'''"""Entrypoint for {clean_name} plugin."""

def {clean_name}_example_action(input_text: str) -> str:
    """Process an action and return observation to locaLLM."""
    return f"[{clean_name}] Processed input: '{{input_text}}' successfully."
'''
        with open(plugin_dir / "main.py", "w", encoding="utf-8") as f:
            f.write(entrypoint_content)

        return True, f"Plugin scaffold '{clean_name}' created at: {plugin_dir}", plugin_dir
    except Exception as exc:
        return False, f"Failed to create plugin scaffold: {exc}", None


def delete_plugin(name: str, workspace_name: Optional[str] = None) -> Tuple[bool, str]:
    """Permanently delete an installed plugin directory."""
    clean_name = name.strip()
    if not clean_name:
        return False, "Plugin name cannot be empty."

    p = get_plugin(clean_name, workspace_name)
    if not p:
        return False, f"Plugin '{clean_name}' not found."

    plugin_dir = p.dir_path
    if not plugin_dir.exists() or not plugin_dir.is_dir():
        return False, f"Plugin directory '{plugin_dir}' does not exist or is not a directory."

    try:
        shutil.rmtree(plugin_dir)
        return True, f"Plugin '{p.name}' ({p.source}) permanently deleted."
    except Exception as exc:
        return False, f"Failed to delete plugin '{p.name}': {exc}"

