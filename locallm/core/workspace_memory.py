"""Workspace-scoped persistent memory manager for locaLLM."""

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional

from locallm.core.workspace import get_workspace_path

logger = logging.getLogger(__name__)

MAX_WORKSPACE_FACTS = 30


class WorkspaceMemoryManager:
    """Manages persistent domain-specific facts and episodic context scoped strictly to a single workspace."""

    def __init__(self, workspace_name: str) -> None:
        self.workspace_name = (workspace_name or "default").strip()
        self.workspace_path = get_workspace_path(self.workspace_name)
        self.memory_file = self.workspace_path / "memory.json"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure workspace directory exists and memory file is initialized if missing."""
        try:
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            if not self.memory_file.exists():
                self.save({"facts": {}})
        except Exception as exc:
            logger.warning(
                "Failed to initialize workspace memory storage for '%s': %s",
                self.workspace_name,
                exc,
            )

    def is_auto_memory_enabled(self) -> bool:
        """Check if auto-memory extraction is enabled in workspace.json (defaults to True)."""
        ws_json = self.workspace_path / "workspace.json"
        if not ws_json.is_file():
            return True
        try:
            with open(ws_json, "r", encoding="utf-8", errors="replace") as f:
                meta = json.load(f)
            return bool(meta.get("auto_memory", True))
        except Exception:
            return True

    def set_auto_memory_enabled(self, enabled: bool) -> bool:
        """Update auto_memory toggle in workspace.json."""
        ws_json = self.workspace_path / "workspace.json"
        meta: Dict[str, Any] = {}
        if ws_json.is_file():
            try:
                with open(ws_json, "r", encoding="utf-8", errors="replace") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        meta["auto_memory"] = bool(enabled)
        try:
            with open(ws_json, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            return True
        except Exception as exc:
            logger.warning("Failed to update auto_memory for workspace '%s': %s", self.workspace_name, exc)
            return False

    def load(self) -> Dict[str, Any]:
        """Safely load workspace memory JSON with fallback on corruption or errors."""
        if not self.memory_file.is_file():
            return {"facts": {}}

        try:
            with open(self.memory_file, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return {"facts": {}}

            facts = data.get("facts")
            if not isinstance(facts, dict):
                facts = {}

            # Sanitize facts ensuring string keys and values
            cleaned_facts: Dict[str, str] = {}
            for k, v in facts.items():
                if k and v is not None:
                    k_str = str(k).strip()
                    v_str = str(v).strip()
                    if k_str and v_str:
                        cleaned_facts[k_str] = v_str

            return {"facts": cleaned_facts}
        except Exception as exc:
            logger.warning(
                "Failed to read workspace memory from %s (%s). Falling back to empty memory.",
                self.memory_file,
                exc,
            )
            return {"facts": {}}

    def save(self, data: Dict[str, Any]) -> bool:
        """Atomically write workspace memory state to disk."""
        try:
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            facts = data.get("facts", {}) if isinstance(data, dict) else {}

            # Enforce max facts quota (keep most recent)
            if len(facts) > MAX_WORKSPACE_FACTS:
                trimmed_keys = list(facts.keys())[-MAX_WORKSPACE_FACTS:]
                facts = {k: facts[k] for k in trimmed_keys}

            normalized = {"facts": facts}

            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.workspace_path,
                delete=False,
                prefix="memory_",
                suffix=".tmp",
            )
            temp_path = Path(temp_file.name)
            try:
                json.dump(normalized, temp_file, indent=2, ensure_ascii=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_file.close()

                temp_path.replace(self.memory_file)
                return True
            except Exception:
                temp_file.close()
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
                raise
        except Exception as exc:
            logger.error(
                "Failed to atomic-save workspace memory to %s: %s",
                self.memory_file,
                exc,
            )
            return False

    def set_fact(self, key: str, value: Any) -> bool:
        """Store a factual statement under key in workspace memory."""
        clean_key = str(key or "").strip()
        clean_val = str(value or "").strip()
        if not clean_key or not clean_val:
            return False

        data = self.load()
        data["facts"][clean_key] = clean_val
        return self.save(data)

    def delete_fact(self, key: str) -> bool:
        """Remove a fact by key from workspace memory."""
        clean_key = str(key or "").strip()
        if not clean_key:
            return False

        data = self.load()
        if clean_key in data["facts"]:
            del data["facts"][clean_key]
            return self.save(data)
        return False

    def clear_memory(self) -> bool:
        """Clear all stored facts in this workspace."""
        return self.save({"facts": {}})

    def list_facts(self) -> Dict[str, str]:
        """Return dictionary of all facts stored in this workspace."""
        return dict(self.load().get("facts", {}))

    def build_workspace_memory_context(self) -> str:
        """Format workspace memory facts for supplementary context injection.

        Format:
        [Workspace Knowledge & Long-Term Memory]
        - key: value

        Returns empty string if auto-memory is disabled or no facts are recorded.
        """
        if not self.is_auto_memory_enabled():
            return ""

        facts = self.list_facts()
        if not facts:
            return ""

        lines = ["[Workspace Knowledge & Long-Term Memory]"]
        for k, v in sorted(facts.items()):
            lines.append(f"- {k}: {v}")

        return "\n".join(lines)
